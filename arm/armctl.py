#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Episode 1 六轴机械臂控制工具 / Контроллер манипулятора Episode 1
================================================================

硬件（已按你的配置固化）:
  * 电机: HANPOSE 17HS3401S-HG25, NEMA17, 25:1 行星减速
  * 驱动: ZDT X42S_V1.0 板, 版本 V1.0.2 (版本帧显示 Y42), 不刷固件
  * 总线: UTC-T01 USB-CAN (SLCAN), 500 kbit/s, 扩展帧
  * 仅 CAN_H / CAN_L, 不接 GND; 12-32 V, 严禁 48 V

关键设计:
  * 所有运动指令都走 Emm42 兼容的“脉冲数”接口, 软件按 25:1 换算输出轴角度。
  * 每个关节有软件软限位; 未标定 min/max 的关节拒绝执行 move。
  * 默认等待到位; Ctrl+C 只 stop, 不 disable (防止重力关节掉落)。

用法:
  python armctl.py ports
  python armctl.py scan --channel COM6
  python armctl.py info --channel COM6 --id 1
  python armctl.py zero --channel COM6 --yes
  python armctl.py move --channel COM6 --id 1 --deg 10 --rpm 2
  python armctl.py move-all --channel COM6 --deg "10,-5,0,0,0,0" --rpm 1

在 macOS 上把 --channel 换成 /dev/cu.usbmodemXXXX 或 /dev/cu.wchusbserialXXXX。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# ============================================================================
# 常量
# ============================================================================

FULL_STEPS = 200                 # 1.8° 步进电机整步数
DEFAULT_GEAR_RATIO = 25.0        # HG25 行星减速
DEFAULT_MICROSTEP = 16
VOLTAGE_MIN_MV = 11500           # 11.5 V, 低于此值不运动
VOLTAGE_MAX_MV = 32500           # 32.5 V, 高于此值立即拒绝
DEFAULT_TIMEOUT = 0.60           # SLCAN/USB 往返超时

EXIT_SAFETY = 3
EXIT_COMM = 4


class ArmError(RuntimeError):
    """可读的工程错误。"""


class SafetyError(ArmError):
    """安全检查未通过, 禁止运动。"""


# ============================================================================
# 配置
# ============================================================================

@dataclass
class Joint:
    index: int                   # 关节序号 1..6, 也是 move-all 的顺序
    can_id: int                  # 驱动器 ID_Addr
    name: str
    invert: bool = False         # true: 正角度对应 CCW
    min_deg: Optional[float] = None
    max_deg: Optional[float] = None
    max_output_rpm: float = 6.0
    gear_ratio: float = 25.0

    @property
    def limits_ready(self) -> bool:
        return self.min_deg is not None and self.max_deg is not None

    def check_target(self, target_deg: float) -> None:
        if not self.limits_ready:
            raise SafetyError(
                f"关节 {self.index} ({self.name}) 尚未标定机械极限 "
                f"min_deg/max_deg; 先完成 docs/CALIBRATION.md 再运行。"
            )
        assert self.min_deg is not None and self.max_deg is not None
        if target_deg < self.min_deg - 1e-9 or target_deg > self.max_deg + 1e-9:
            raise SafetyError(
                f"目标 {target_deg:.3f}° 超出关节 {self.index} 软限位 "
                f"[{self.min_deg:.3f}, {self.max_deg:.3f}]°"
            )


@dataclass
class ArmConfig:
    gear_ratio: float
    microstep: Optional[int]
    max_output_rpm: float
    default_output_rpm: float
    max_step_deg: float
    firmware: str
    joints: List[Joint]
    path: Path

    def by_can_id(self, can_id: int) -> Joint:
        for j in self.joints:
            if j.can_id == can_id:
                return j
        raise ArmError(
            f"CAN ID {can_id} 不在 {self.path} 中; 先把它加入 joints 列表。"
        )

    def by_index(self, index: int) -> Joint:
        for j in self.joints:
            if j.index == index:
                return j
        raise ArmError(f"配置中没有关节 {index}")

    def joint_ids(self) -> List[int]:
        return [j.can_id for j in self.joints]

    def validate(self) -> None:
        if self.gear_ratio <= 0:
            raise ArmError("gear_ratio 必须 > 0")
        if self.max_output_rpm <= 0:
            raise ArmError("max_output_rpm 必须 > 0")
        if self.max_step_deg <= 0:
            raise ArmError("max_step_deg 必须 > 0")
        if self.microstep is not None and not (1 <= self.microstep <= 256):
            raise ArmError("microstep 必须在 1..256")
        if self.firmware not in ("emm", "x", "auto"):
            raise ArmError("firmware 必须是 emm / x / auto")
        ids, idxs = set(), set()
        for j in self.joints:
            if j.can_id in ids:
                raise ArmError(f"CAN ID 重复: {j.can_id}")
            if j.index in idxs:
                raise ArmError(f"关节序号重复: {j.index}")
            ids.add(j.can_id)
            idxs.add(j.index)
            if (j.min_deg is None) != (j.max_deg is None):
                raise ArmError(f"关节 {j.index}: min_deg/max_deg 必须同时填写或同时为 null")
            if j.min_deg is not None and j.max_deg is not None and j.min_deg >= j.max_deg:
                raise ArmError(f"关节 {j.index}: min_deg 必须小于 max_deg")
            if j.max_output_rpm <= 0:
                raise ArmError(f"关节 {j.index}: max_output_rpm 必须 > 0")
            if j.gear_ratio <= 0:
                raise ArmError(f"关节 {j.index}: gear_ratio 必须 > 0")


def load_config(path: Path) -> ArmConfig:
    if not path.is_file():
        raise ArmError(f"配置文件不存在: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    arm = raw.get("arm", {})
    joints_raw = raw.get("joints", [])
    if not isinstance(joints_raw, list) or not joints_raw:
        raise ArmError("配置里 joints 必须是非空数组")
    joints = [
        Joint(
            index=int(item["joint"]),
            can_id=int(item["id"]),
            name=str(item.get("name", f"J{item['joint']}")),
            invert=bool(item.get("invert", False)),
            min_deg=None if item.get("min_deg") is None else float(item["min_deg"]),
            max_deg=None if item.get("max_deg") is None else float(item["max_deg"]),
            max_output_rpm=float(item.get("max_output_rpm", arm.get("max_output_rpm", 6.0))),
            gear_ratio=float(item.get("gear_ratio", arm.get("gear_ratio", 25.0))),
        )
        for item in joints_raw
    ]
    cfg = ArmConfig(
        gear_ratio=float(arm.get("gear_ratio", DEFAULT_GEAR_RATIO)),
        microstep=None if arm.get("microstep") is None else int(arm["microstep"]),
        max_output_rpm=float(arm.get("max_output_rpm", 6.0)),
        default_output_rpm=float(arm.get("default_output_rpm", 2.0)),
        max_step_deg=float(arm.get("max_step_deg", 90.0)),
        firmware=str(arm.get("firmware", "emm")).lower(),
        joints=joints,
        path=path,
    )
    cfg.validate()
    return cfg


# ============================================================================
# 软件角度状态
# ============================================================================

@dataclass
class ArmState:
    valid: bool
    angles: Dict[str, float]
    updated: str
    zeroed: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def empty(cls, cfg: ArmConfig) -> "ArmState":
        return cls(
            valid=False,
            angles={str(j.index): 0.0 for j in cfg.joints},
            updated="",
            zeroed={str(j.index): False for j in cfg.joints},
        )

    @classmethod
    def load(cls, path: Path, cfg: ArmConfig) -> "ArmState":
        if not path.is_file():
            return cls.empty(cfg)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            angles = {str(j.index): float(raw["angles"].get(str(j.index), 0.0))
                      for j in cfg.joints}
            zeroed_raw = raw.get("zeroed")
            if zeroed_raw is None:
                # 兼容旧状态文件: valid=True 视为六个关节都 zero 过
                zeroed = {str(j.index): bool(raw.get("valid", False))
                          for j in cfg.joints}
            else:
                zeroed = {str(j.index): bool(zeroed_raw.get(str(j.index), False))
                          for j in cfg.joints}
            return cls(
                valid=bool(raw.get("valid", False)),
                angles=angles,
                updated=str(raw.get("updated", "")),
                zeroed=zeroed,
            )
        except Exception:
            return cls.empty(cfg)

    def angle(self, joint_index: int) -> float:
        return float(self.angles.get(str(joint_index), 0.0))

    def set_angle(self, joint_index: int, value: float) -> None:
        self.angles[str(joint_index)] = float(value)

    def save(self, path: Path) -> None:
        self.updated = datetime.now().isoformat(timespec="seconds")
        payload = {
            "version": 1,
            "valid": self.valid,
            "angles": self.angles,
            "zeroed": self.zeroed,
            "updated": self.updated,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)


# ============================================================================
# CAN 传输
# ============================================================================

def make_transport(args):
    """创建 python-can 传输, 供 x42s_stepper 使用。"""
    try:
        import can
        import threading
        from x42s_stepper.transport.can import CanTransport
    except ImportError as exc:
        raise ArmError(
            "缺少依赖。请运行: pip install 'x42s-stepper[can]==0.2.0' pyserial"
        ) from exc

    class _Transport(CanTransport):
        def __init__(self):
            self.channel = args.channel
            self.bitrate = args.bitrate
            self.default_timeout = args.timeout
            self._lock = threading.RLock()
            kwargs = dict(
                interface=args.iface,
                channel=args.channel,
                receive_own_messages=False,
                fd=False,
            )
            # slcan 需要 python-can 帮我们发 "Sx" 设速率; socketcan 由 ip link 设。
            if args.iface in ("slcan", "pcan", "kvaser", "gs_usb"):
                kwargs["bitrate"] = args.bitrate
            try:
                self._bus = can.Bus(**kwargs)
            except Exception as exc:
                raise ArmError(
                    f"打开 CAN 失败: interface={args.iface} channel={args.channel} "
                    f"bitrate={args.bitrate}\n{exc}\n"
                    "Windows 示例: --iface slcan --channel COM6\n"
                    "macOS 示例:   --iface slcan --channel /dev/cu.usbmodemXXXX\n"
                    "Linux 示例:   --iface socketcan --channel can0"
                ) from exc

    return _Transport()


# ============================================================================
# 控制器
# ============================================================================

class ArmController:
    def __init__(self, cfg: ArmConfig, args):
        self.cfg = cfg
        self.args = args
        self.transport = None
        self.motors: Dict[int, object] = {}
        self.state_path = Path(args.state) if args.state else cfg.path.parent / ".arm_state.json"
        self.state = ArmState.load(self.state_path, cfg)
        self._microstep = int(args.microstep) if args.microstep else cfg.microstep
        self._touched: set = set()
        self._X42SDevice = None
        self._FirmwareType = None

    # ---------- 基础 ----------

    def _ensure_sdk(self) -> None:
        if self._X42SDevice is not None:
            return
        try:
            from x42s_stepper import X42SDevice, FirmwareType
        except ImportError as exc:
            raise ArmError(
                "缺少依赖。请运行: pip install 'x42s-stepper[can]==0.2.0' pyserial"
            ) from exc
        self._X42SDevice = X42SDevice
        self._FirmwareType = FirmwareType

    def _ensure_transport(self):
        if self.transport is None:
            self.transport = make_transport(self.args)
        return self.transport

    def close(self) -> None:
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                pass

    def motor(self, can_id: int):
        self._ensure_sdk()
        if can_id not in self.motors:
            if self.cfg.firmware == "auto":
                fw = None
            elif self.cfg.firmware == "x":
                fw = self._FirmwareType.X_FIRMWARE
            else:
                fw = self._FirmwareType.EMM_FIRMWARE
            self.motors[can_id] = self._X42SDevice(
                self._ensure_transport(),
                address=can_id,
                firmware_type=fw,
                auto_test=False,
                microstep=self._microstep or DEFAULT_MICROSTEP,
            )
        return self.motors[can_id]

    def _ms(self, can_id: int) -> int:
        """读取实际细分; 256 在 Emm 配置里用 0 表示。"""
        if self._microstep:
            return self._microstep
        cfg = self.motor(can_id).get_config()
        if cfg is None:
            raise ArmError(f"ID {can_id} 读配置无应答, 无法确定细分")
        ms = int(getattr(cfg, "microstep", 0))
        ms = 256 if ms == 0 else ms
        if not (1 <= ms <= 256):
            raise ArmError(f"驱动器返回非法细分值: {ms}")
        self._microstep = ms
        print(f"[信息] 从驱动器读到细分 = {ms}")
        return ms

    def _voltage_ok(self, can_ids: Sequence[int], skip: bool) -> None:
        if skip:
            print("[警告] 已跳过母线电压检查 (--skip-voltage-check)")
            return
        seen = set()
        for cid in can_ids:
            if cid in seen:
                continue
            seen.add(cid)
            raw = self.motor(cid).get_bus_voltage()
            if raw is None:
                raise ArmError(
                    f"驱动器 {cid} 母线电压读取无应答; 禁止运动。"
                    "检查 CAN 接线/ID/波特率/终端电阻。"
                )
            mv = int(raw)
            if mv < VOLTAGE_MIN_MV or mv > VOLTAGE_MAX_MV:
                raise SafetyError(
                    f"驱动器 {cid} 母线电压 {mv/1000:.2f} V 超出允许范围 "
                    f"[{VOLTAGE_MIN_MV/1000:.1f}, {VOLTAGE_MAX_MV/1000:.1f}] V。"
                    "禁止上电运动; 用万用表确认电源电压与极性。"
                )
            print(f"[安全] 驱动器 {cid} 母线电压 {mv/1000:.2f} V")

    def _check_rpm(self, joint: Joint, rpm: float) -> float:
        limit = min(self.cfg.max_output_rpm, joint.max_output_rpm)
        if rpm <= 0:
            raise SafetyError("--rpm 必须是正数 (输出轴 RPM)")
        if rpm > limit + 1e-9:
            raise SafetyError(
                f"关节 {joint.index} 输出轴速度 {rpm:.2f} RPM 超过限制 {limit:.2f} RPM"
            )
        return rpm

    def _pulses(self, deg: float, microstep: int, gear_ratio: float) -> int:
        per_turn = FULL_STEPS * microstep * gear_ratio
        return int(round(abs(deg) * per_turn / 360.0))

    def _direction(self, joint: Joint, positive: bool):
        from x42s_stepper import Direction
        cw = positive if not joint.invert else (not positive)
        return Direction.CW if cw else Direction.CCW

    def _state_ready(self, joints: Sequence[Joint]) -> None:
        missing = [j.index for j in joints
                   if not self.state.zeroed.get(str(j.index), False)]
        if missing:
            raise SafetyError(
                f"关节 {missing} 还没有 zero 过, 或 jog 后位置未知。\n"
                "把该关节放到安全姿态后运行: python armctl.py zero --id N --yes\n"
                "注意: zero 只是把【当前姿态】定义为 0°, 不会驱动电机。"
            )

    def _invalidate_joint(self, joint: Joint, reason: str) -> None:
        self.state.zeroed[str(joint.index)] = False
        self.state.valid = all(self.state.zeroed.get(str(j.index), False)
                               for j in self.cfg.joints)
        self.state.save(self.state_path)
        print(f"[警告] J{joint.index} 标记为 NOT-ZEROED: {reason}", file=sys.stderr)

    # ---------- 扫描 / 信息 ----------

    def scan(self, start: int, end: int) -> int:
        print(f"扫描 CAN ID {start}..{end} (只读版本, 不使能, 不运动) ...")
        found = []
        for addr in range(start, end + 1):
            try:
                m = self.motor(addr)
                v = m.ping()
                if v is None:
                    raise ArmError("无应答 (ping 返回 None)")
                fw = getattr(v, "firmware_version_str", "?")
                hw = getattr(v, "hw_type_str", "?")
                print(f"  ID {addr:>3}: OK  固件 {fw}  硬件 {hw}")
                found.append(addr)
            except Exception as exc:
                msg = str(exc).splitlines()[0][:90]
                print(f"  ID {addr:>3}: --  {msg}")
        print(f"发现 {len(found)} 个: {found}")
        if found:
            print("下一步: python armctl.py info --channel ... --id %d" % found[0])
        return 0

    def info(self, can_id: int) -> int:
        m = self.motor(can_id)
        v = m.get_version()
        if v is None:
            raise ArmError(f"ID {can_id} 无应答 (读版本返回 None)")
        print(f"== CAN ID {can_id} ==")
        print(f"  固件版本        {getattr(v, 'firmware_version_str', '?')}")
        print(f"  硬件版本        {getattr(v, 'hw_type_str', '?')}")
        series = getattr(v, "hw_series", 0)
        if series != 0:
            print(f"  [警告] 硬件系列码={series} (不是 X 系列的 0)。"
                  "交接写的是 X42S，请核对驱动器板型；"
                  "Y42 与 X42S 的配置/命令载荷不完全相同。")
        try:
            cfg = m.get_config()
        except Exception as exc:
            cfg = None
            print(f"  [警告] 读驱动配置失败: {exc}")
        if cfg is not None:
            ms_show = getattr(cfg, "microstep", "?")
            if ms_show == 0:
                ms_show = 256
            fields = [
                ("驱动器内 ID", getattr(cfg, "motor_id", "?")),
                ("细分", ms_show),
                ("通讯端口模式", getattr(getattr(cfg, "serial_port_mode", None), "name", "?")),
                ("CAN 速率", getattr(getattr(cfg, "can_rate", None), "name", "?")),
                ("max_voltage", (f"{cfg.max_voltage_mv/1000:.1f} V"
                                if hasattr(cfg, "max_voltage_mv") else "?")),
                ("控制命令应答", getattr(getattr(cfg, "response_mode", None), "name", "?")),
                ("堵转保护", getattr(getattr(cfg, "stall_protect", None), "name", "?")),
            ]
            for k, val in fields:
                print(f"  {k:<15} {val}")
            mode = getattr(getattr(cfg, "serial_port_mode", None), "name", "")
            if mode and mode != "CAN":
                print("  [警告] P_Serial 不是 CAN1_MAP。CAN 命令本不应响应; 请核对驱动菜单。")

        try:
            raw = m.get_bus_voltage()
            if raw is None:
                raise ArmError("无应答")
            mv = int(raw)
            print(f"  母线电压        {mv/1000:.2f} V")
            if mv < VOLTAGE_MIN_MV or mv > VOLTAGE_MAX_MV:
                print("  [危险] 电压超出 12-32 V 范围, 禁止运动!")
        except Exception as exc:
            print(f"  母线电压        读取失败: {exc}")
        try:
            print(f"  温度            {m.get_temperature()} °C")
            print(f"  相电流          {m.get_phase_current()} mA")
            print(f"  实时转速        {m.get_realtime_speed():.2f} RPM (电机轴)")
            try:
                print(f"  位置误差        {m.get_position_error():.3f}° (电机轴)")
            except Exception:
                pass
            motor_pos = m.get_realtime_position()
            print(f"  实时位置        {motor_pos:.2f}° (电机轴, 多圈累计)")
            try:
                jpos = self.cfg.by_can_id(can_id)
                out_pos = motor_pos / jpos.gear_ratio
            except ArmError:
                out_pos = motor_pos / self.cfg.gear_ratio
            print(f"  输出轴位置      {out_pos:.2f}° (多圈累计)")
            print(f"  编码器角度      {m.get_encoder_degrees():.2f}°")
        except Exception as exc:
            print(f"  状态读取失败: {exc}")
        try:
            st = m.get_motor_status()
            print(f"  使能={st.enabled} 到位={st.position_reached} "
                  f"堵转={st.stall_detected} 保护={st.stall_protected}")
        except Exception as exc:
            print(f"  状态标志读取失败: {exc}")

        try:
            j = self.cfg.by_can_id(can_id)
            print(f"  配置关节        J{j.index} {j.name}  invert={j.invert}")
            print(f"  软限位          {j.min_deg} .. {j.max_deg} °")
            print(f"  软件当前角度    {self.state.angle(j.index):.3f}°  "
                  f"(state valid={self.state.valid})")
        except ArmError:
            print("  [提示] 该 ID 尚未写入 config/joints.json")
        return 0

    # ---------- 使能 / 停止 ----------

    def enable(self, can_id: int) -> int:
        j = self.cfg.by_can_id(can_id)
        self._voltage_ok([can_id], bool(getattr(self.args, "skip_voltage_check", False)))
        m = self.motor(can_id)
        if not m.enable():
            raise ArmError(f"ID {can_id} 使能失败")
        self._touched.add(can_id)
        print(f"ID {can_id} (J{j.index}) 已使能, 锁轴。")
        return 0

    def disable(self, can_id: int) -> int:
        j = self.cfg.by_can_id(can_id)
        m = self.motor(can_id)
        if not m.disable():
            raise ArmError(f"ID {can_id} 失能失败")
        self._touched.discard(can_id)
        print(f"ID {can_id} (J{j.index}) 已失能。")
        print("[警告] 失能后关节可能因重力掉落; 请先托住机械臂。")
        return 0

    def stop_all(self, quiet: bool = False) -> None:
        for cid in sorted(self._touched):
            try:
                self.motor(cid).stop()
                if not quiet:
                    print(f"ID {cid} 已停止 (保持使能)")
            except Exception as exc:
                print(f"[错误] ID {cid} 停止失败: {exc}")

    def clear_protection(self, can_id: int) -> int:
        j = self.cfg.by_can_id(can_id)
        m = self.motor(can_id)
        m.stop()
        time.sleep(0.1)
        if not m.clear_protection():
            raise ArmError(f"ID {can_id} 解除保护失败")
        time.sleep(0.1)
        st = m.get_motor_status()
        print(f"ID {can_id} (J{j.index}) 保护已清除: "
              f"堵转={st.stall_detected} 保护={st.stall_protected} 到位={st.position_reached}")
        return 0

    # ---------- 零位 / 状态 ----------

    def zero(self, confirmed: bool, can_id: Optional[int] = None,
             at_deg: float = 0.0) -> int:
        if not confirmed:
            raise SafetyError("zero 会改变软限位的参考点; 确认后加 --yes")
        if abs(at_deg) > 1e-9 and can_id is None:
            raise SafetyError("--at-deg 非 0 时必须同时给 --id, 防止把全部关节设错")
        if can_id is not None:
            j = self.cfg.by_can_id(can_id)
            self.state.set_angle(j.index, at_deg)
            self.state.zeroed[str(j.index)] = True
            self.state.save(self.state_path)
            print(f"已把 J{j.index} (ID {can_id}) 的【当前姿态】定义为 {at_deg:.3f}°。")
            print("其他关节的软件角度/zero 状态保持不变。")
        else:
            for j in self.cfg.joints:
                self.state.set_angle(j.index, 0.0)
                self.state.zeroed[str(j.index)] = True
            self.state.save(self.state_path)
            print("已把【当前姿态】定义为所有关节 0.000°。")
        self.state.valid = all(self.state.zeroed.get(str(j.index), False)
                               for j in self.cfg.joints)
        self.state.save(self.state_path)
        print(f"状态文件: {self.state_path}")
        print("驱动器内部的单圈零点没有改动; 本工具只用相对脉冲运动。")
        return 0

    def show_state(self) -> int:
        print(f"state file: {self.state_path}")
        print(f"valid={self.state.valid}  updated={self.state.updated or '-'}")
        for j in self.cfg.joints:
            lim = (f"[{j.min_deg:.2f}, {j.max_deg:.2f}]"
                   if j.limits_ready else "[未标定]")
            z = "zeroed" if self.state.zeroed.get(str(j.index), False) else "NOT-ZEROED"
            print(f"  J{j.index} id={j.can_id:<3} {j.name:<12} "
                  f"angle={self.state.angle(j.index):9.3f}°  limits={lim}  {z}")
        return 0

    # ---------- 运动 ----------

    def _move_one(self, joint: Joint, delta_deg: float, rpm: float,
                  accel: int, wait: bool, sync: bool = False,
                  allow_large: bool = False, check_state: bool = True,
                  wait_timeout: float = 60.0, check_limits: bool = True) -> float:
        if not 0 <= int(accel) <= 255:
            raise SafetyError("--accel 必须在 0..255 (Emm 档位)")
        if check_state:
            self._state_ready([joint])
        if abs(delta_deg) > self.cfg.max_step_deg and not allow_large:
            raise SafetyError(
                f"单次运动 {delta_deg:.2f}° 超过 max_step_deg="
                f"{self.cfg.max_step_deg:.1f}°; 确认安全后加 --allow-large"
            )
        current = self.state.angle(joint.index)
        target = current + delta_deg
        if check_limits:
            joint.check_target(target)
        rpm = self._check_rpm(joint, rpm)
        ms = self._ms(joint.can_id)
        pulses = self._pulses(delta_deg, ms, joint.gear_ratio)
        if pulses <= 0:
            raise ArmError("角度太小, 换算后脉冲数为 0")

        m = self.motor(joint.can_id)
        if not m.enable():
            raise ArmError(f"ID {joint.can_id} 使能失败")
        self._touched.add(joint.can_id)

        motor_rpm = int(round(rpm * joint.gear_ratio))
        if motor_rpm < 1:
            raise SafetyError(
                f"输出轴 {rpm:.3f} RPM × 减速比 {joint.gear_ratio:g} "
                f"四舍五入后电机转速为 0；请把 --rpm 提高到至少 "
                f"{1.0 / joint.gear_ratio:.3f}"
            )
        direction = self._direction(joint, delta_deg >= 0)
        from x42s_stepper import MotionMode
        ok = m.move_position(
            pulses=pulses,
            speed_rpm=motor_rpm,
            direction=direction,
            acceleration=int(accel),
            motion_mode=MotionMode.RELATIVE_CURRENT,
            sync=sync,
        )
        if not ok:
            raise ArmError(f"ID {joint.can_id} 位置命令被拒绝")
        if not sync and wait:
            self._wait_done(joint, m, timeout=wait_timeout)
            self.state.set_angle(joint.index, target)
            self.state.save(self.state_path)
        elif not sync:
            self.state.set_angle(joint.index, target)
            self.state.save(self.state_path)
            print(f"[警告] 未等待到位, 软件角度已按指令假设为 {target:.3f}°")
        return target

    def _wait_done(self, joint: Joint, m, timeout: Optional[float] = None) -> None:
        if timeout is None:
            timeout = 60.0
        time.sleep(0.20)
        start = time.monotonic()
        deadline = start + timeout
        stable = 0
        saw_busy = False
        zero_speed_since: Optional[float] = None
        last_err = ""
        while time.monotonic() < deadline:
            try:
                st = m.get_motor_status()
                sp = float(m.get_realtime_speed())
                try:
                    pos_err = float(m.get_position_error())
                except Exception:
                    pos_err = None
                last_err = ""
            except Exception as exc:
                last_err = str(exc)
                time.sleep(0.10)
                continue
            err_out = (abs(pos_err) / joint.gear_ratio
                       if pos_err is not None else 999.0)
            near_target = st.position_reached or err_out <= 0.10
            if st.stall_protected:
                m.stop()
                self._invalidate_joint(joint, "触发堵转保护")
                raise SafetyError(f"ID {joint.can_id} 触发堵转保护, 已停止")
            if not st.position_reached:
                saw_busy = True
            now = time.monotonic()
            if abs(sp) < 0.1 and not near_target:
                if zero_speed_since is None:
                    zero_speed_since = now
                elif now - zero_speed_since > 3.0:
                    m.stop()
                    self._invalidate_joint(joint, "3 s 转速为 0 且未到位")
                    raise SafetyError(
                        f"ID {joint.can_id} 指令后 3 s 转速仍为 0 且未到位; "
                        f"位置误差 {err_out:.3f}° 输出轴; 可能被重力/机械卡住。"
                        "已 stop。请托住手臂、检查负载后再试。"
                    )
            else:
                zero_speed_since = None
            if abs(sp) < 0.5 and near_target:
                stable += 1
                # 至少看到过一次“未到位”, 或已过 1.5 s, 才相信是本次运动完成
                if stable >= 3 and (saw_busy or now - start > 1.5):
                    return
            else:
                stable = 0
            time.sleep(0.10)
        m.stop()
        self._invalidate_joint(joint, "等待到位超时")
        raise ArmError(
            f"ID {joint.can_id} 等待到位超时 ({timeout:.0f}s)"
            + (f"; 最后错误: {last_err}" if last_err else "")
        )

    def move(self, can_id: int, deg: float, rpm: Optional[float], accel: int,
             wait: bool, skip_voltage: bool, allow_large: bool,
             wait_timeout: float = 60.0, check_limits: bool = True) -> float:
        j = self.cfg.by_can_id(can_id)
        rpm = self.cfg.default_output_rpm if rpm is None else rpm
        self._state_ready([j])
        target = self.state.angle(j.index) + deg
        if check_limits:
            j.check_target(target)
        self._check_rpm(j, rpm)
        if abs(deg) > self.cfg.max_step_deg and not allow_large:
            raise SafetyError(f"单次运动 {deg:.2f}° 超过 {self.cfg.max_step_deg:.1f}°; 加 --allow-large")
        self._voltage_ok([can_id], skip_voltage)
        t = self._move_one(j, deg, rpm, accel, wait, allow_large=allow_large,
                           wait_timeout=wait_timeout, check_limits=check_limits)
        print(f"J{j.index} 目标 {t:.3f}° 完成。")
        return t

    def move_all(self, deltas: Sequence[float], rpm: Optional[float], accel: int,
                 wait: bool, skip_voltage: bool, allow_large: bool,
                 wait_timeout: float = 60.0) -> int:
        if len(deltas) != len(self.cfg.joints):
            raise ArmError(
                f"--deg 需要 {len(self.cfg.joints)} 个数 (按关节序号), 收到 {len(deltas)} 个"
            )
        joints = sorted(self.cfg.joints, key=lambda x: x.index)
        self._state_ready(joints)
        rpm = self.cfg.default_output_rpm if rpm is None else rpm

        targets = []
        for j, d in zip(joints, deltas):
            if abs(d) > self.cfg.max_step_deg and not allow_large:
                raise SafetyError(f"J{j.index} 单次 {d:.2f}° 超过 {self.cfg.max_step_deg:.1f}°; 加 --allow-large")
            target = self.state.angle(j.index) + d
            j.check_target(target)
            self._check_rpm(j, rpm)
            targets.append(target)

        self._voltage_ok([j.can_id for j in joints], skip_voltage)

        # 0° 的关节不发命令, 避免 0 脉冲被驱动拒绝
        active = [(j, d, t) for j, d, t in zip(joints, deltas, targets)
                  if abs(d) > 1e-9]
        if not active:
            print("所有增量都是 0°, 不发送运动命令。")
            return 0

        # 1) 逐个缓存 sync 位置命令; 任一失败则全部停止, 不触发同步
        try:
            for j, d, _t in active:
                self._move_one(j, d, rpm, accel, wait=False, sync=True,
                               allow_large=allow_large)
            # 2) 广播 FF 66。手册: 只有 ID=1 会回复; 没有 ID1 时直接发, 不等 ACK。
            transport = self._ensure_transport()
            if 1 in self.cfg.joint_ids():
                from x42s_stepper import X42SDevice
                try:
                    X42SDevice.sync_move(transport)
                except Exception as exc:
                    self.stop_all(quiet=True)
                    raise ArmError(
                        "同步触发无应答。命令已缓存但可能未执行; 已发送 stop。"
                        "缓存目标可能仍留在驱动器里, 继续前先断电重启。"
                        f" 原因: {exc}"
                    ) from exc
            else:
                transport.send(b"\x00\xff\x66\x6b")
                print("[警告] 总线上没有配置 ID=1; FF66 已广播, 但无法确认 ACK。")
            # 3) 等待
            if wait:
                for j, _d, _t in active:
                    self._wait_done(j, self.motor(j.can_id), timeout=wait_timeout)
            else:
                print("[警告] 未等待到位; 软件角度按指令假设更新")
            for j, t in zip(joints, targets):
                self.state.set_angle(j.index, t)
            self.state.save(self.state_path)
        except Exception:
            self.stop_all(quiet=True)
            print("[警告] 同步流程中断: 驱动器里可能残留已缓存的 sync 目标。"
                  "继续运动前先断电重启, 或重新 zero 并确认。", file=sys.stderr)
            raise
        print("同步运动完成: " + ", ".join(
            f"J{j.index}={t:.3f}°" for j, t in zip(joints, targets)))
        return 0

    def jog(self, can_id: int, rpm: Optional[float], seconds: float,
            direction: str, accel: int, skip_voltage: bool,
            allow_long: bool) -> int:
        j = self.cfg.by_can_id(can_id)
        rpm = self.cfg.default_output_rpm if rpm is None else rpm
        self._check_rpm(j, rpm)
        if not 0 <= int(accel) <= 255:
            raise SafetyError("--accel 必须在 0..255 (Emm 档位)")
        if seconds > 10.0 and not allow_long:
            raise SafetyError("单次 jog 超过 10 s; 确认安全后加 --allow-long")
        self._voltage_ok([can_id], skip_voltage)
        motor_rpm = int(round(rpm * j.gear_ratio))
        if motor_rpm < 1:
            raise SafetyError(
                f"输出轴 {rpm:.3f} RPM × 减速比 {j.gear_ratio:g} "
                f"四舍五入后电机转速为 0；请把 --rpm 提高到至少 "
                f"{1.0 / j.gear_ratio:.3f}"
            )

        m = self.motor(can_id)
        start_motor = m.get_realtime_position()
        if start_motor is None:
            raise ArmError(f"ID {can_id} 读初始位置无应答")
        if not m.enable():
            raise ArmError(f"ID {can_id} 使能失败")
        self._touched.add(can_id)
        # --dir 指输出轴方向; invert 关节要翻转
        d = self._direction(j, direction == "cw")
        if not m.jog(speed_rpm=motor_rpm,
                     direction=d, acceleration=int(accel)):
            raise ArmError(f"ID {can_id} 速度命令被拒绝")

        print(f"J{j.index} 输出轴 {rpm:.2f} RPM ({direction.upper()}), "
              f"电机轴 {rpm*j.gear_ratio:.0f} RPM; "
              f"{'按 Ctrl+C 停止' if seconds == 0 else f'{seconds:.1f}s 后自动停止'}")
        t_end = time.monotonic() + seconds
        try:
            while seconds == 0 or time.monotonic() < t_end:
                time.sleep(0.25)
                try:
                    st = m.get_motor_status()
                    if st.stall_protected:
                        raise SafetyError("触发堵转保护")
                except SafetyError:
                    raise
                except Exception:
                    pass
        except KeyboardInterrupt:
            print("\n[中断] 停止 jog")
        finally:
            try:
                m.stop()
            except Exception:
                pass
            time.sleep(0.20)
            # 用驱动器的多圈累计位置更新软件角度, 不再强制重新 zero
            try:
                end_motor = m.get_realtime_position()
                if end_motor is None:
                    raise ArmError("读结束位置无应答")
                sign = -1.0 if j.invert else 1.0
                delta_out = (end_motor - start_motor) / j.gear_ratio * sign
                new_angle = self.state.angle(j.index) + delta_out
                self.state.set_angle(j.index, new_angle)
                if j.limits_ready and not (j.min_deg <= new_angle <= j.max_deg):
                    self.state.zeroed[str(j.index)] = False
                    print(f"[警告] jog 后 J{j.index}={new_angle:.3f}° 超出软限位, "
                          "该关节已标记 NOT-ZEROED。", file=sys.stderr)
                else:
                    self.state.zeroed[str(j.index)] = True
                self.state.valid = all(self.state.zeroed.get(str(jj.index), False)
                                       for jj in self.cfg.joints)
                self.state.save(self.state_path)
                print(f"jog 已停止。J{j.index} 软件角度更新为 "
                      f"{new_angle:.3f}° (delta={delta_out:+.3f}°)。")
            except Exception as exc:
                self.state.zeroed[str(j.index)] = False
                self.state.valid = False
                self.state.save(self.state_path)
                print(f"[警告] jog 后读位置失败, J{j.index} 标记 NOT-ZEROED: {exc}",
                      file=sys.stderr)
        return 0

    # ---------- 改 ID ----------

    def set_id(self, old: int, new: int, confirmed: bool) -> int:
        if not confirmed:
            raise SafetyError("修改 ID 会写入驱动器; 确认后加 --yes")
        if old == new:
            raise ArmError("新旧 ID 相同")
        if not (1 <= new <= 255):
            raise ArmError("新 ID 必须在 1..255")
        if new in self.cfg.joint_ids():
            raise SafetyError(f"新 ID {new} 已在配置中, 先处理冲突")

        # 先确认 new 没有被占用
        try:
            self.motor(new).ping()
            raise SafetyError(f"ID {new} 已有电机响应; 禁止覆盖")
        except SafetyError:
            raise
        except Exception:
            pass

        m = self.motor(old)
        if not m.set_id(new, store=True):
            raise ArmError(f"ID {old} -> {new} 写入失败")
        time.sleep(0.3)
        try:
            v = self.motor(new).ping()
            if v is None:
                raise ArmError("新 ID ping 返回 None")
            print(f"ID {old} -> {new} 成功, 新 ID 固件 {getattr(v, 'firmware_version_str', '?')}")
        except Exception as exc:
            raise ArmError(f"写入后新 ID {new} 无响应: {exc}")
        print(f"请手动把 {self.cfg.path} 中原来的 id={old} 改成 id={new}。")
        return 0

    # ---------- 监控 ----------

    def monitor(self, ids: Sequence[int], interval: float) -> int:
        print("Ctrl+C 退出。只读, 不使能, 不运动。")
        print(f"{'ID':>3} {'en':>2} {'到位':>4} {'堵转':>4} {'保护':>4} "
              f"{'转速RPM':>10} {'位置°':>10}")
        try:
            while True:
                for cid in ids:
                    try:
                        m = self.motor(cid)
                        st = m.get_motor_status()
                        sp = m.get_realtime_speed()
                        pos = m.get_realtime_position()
                        print(f"{cid:>3} {int(st.enabled):>2} "
                              f"{int(st.position_reached):>4} "
                              f"{int(st.stall_detected):>4} "
                              f"{int(st.stall_protected):>4} "
                              f"{sp:>10.2f} {pos:>10.2f}")
                    except Exception as exc:
                        print(f"{cid:>3} 读取失败: {str(exc).splitlines()[0][:60]}")
                print("-" * 58)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n退出 monitor")
        return 0


# ============================================================================
# CLI
# ============================================================================

def _common_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    here = Path(__file__).resolve().parent
    p.add_argument("--iface", default="slcan",
                   choices=["slcan", "socketcan", "virtual"],
                   help="CAN 接口 (默认 slcan; Linux SocketCAN 用 socketcan)")
    p.add_argument("--channel", default=("COM6" if os.name == "nt" else None),
                   help="SLCAN 串口 (COM6 / /dev/cu.usbmodemXXXX) 或 can0")
    p.add_argument("--bitrate", type=int, default=500000)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--config", default=str(here / "config" / "joints.json"))
    p.add_argument("--state", default=None,
                   help="软件角度状态文件 (默认与配置同目录 .arm_state.json)")
    p.add_argument("--microstep", type=int, default=None,
                   help="覆盖细分; 默认读驱动器/配置文件")
    return p


def _motion_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--rpm", type=float, default=None,
                   help="输出轴转速 RPM (默认配置 default_output_rpm)")
    p.add_argument("--accel", type=int, default=10,
                   help="Emm 加速度档位 0..255 (默认 10)")
    p.add_argument("--no-wait", action="store_true", help="发完不等待到位 (不推荐)")
    p.add_argument("--wait-timeout", type=float, default=60.0,
                   help="等待到位超时秒数 (默认 60)")
    p.add_argument("--skip-voltage-check", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    common = _common_parser()
    p = argparse.ArgumentParser(
        description="Episode 1 六轴机械臂 / X42S / Emm 命令集 / SLCAN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python armctl.py ports\n"
               "  python armctl.py scan --channel COM6\n"
               "  python armctl.py info --channel COM6 --id 1\n"
               "  python armctl.py zero --channel COM6 --yes\n"
               "  python armctl.py move --channel COM6 --id 1 --deg 10 --rpm 2\n",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("ports", help="列出串口")
    sp.set_defaults(func="ports")

    sp = sub.add_parser("scan", parents=[common], help="扫描 CAN ID (只读)")
    sp.add_argument("--start", type=int, default=1)
    sp.add_argument("--end", type=int, default=8)
    sp.set_defaults(func="scan")

    sp = sub.add_parser("info", parents=[common], help="读取版本/配置/电压/状态")
    sp.add_argument("--id", type=int, required=True, dest="can_id")
    sp.set_defaults(func="info")

    for name, helptext in (("enable", "使能"), ("disable", "失能")):
        sp = sub.add_parser(name, parents=[common], help=helptext)
        sp.add_argument("--id", type=int, required=True, dest="can_id")
        if name == "enable":
            sp.add_argument("--skip-voltage-check", action="store_true")
        sp.set_defaults(func=name)

    sp = sub.add_parser("stop", parents=[common], help="立即停止 (保持使能)")
    sp.add_argument("--id", type=int, default=None, dest="can_id")
    sp.add_argument("--all", action="store_true")
    sp.set_defaults(func="stop")

    sp = sub.add_parser("clear-protection", parents=[common],
                         help="解除驱动器堵转保护 (先 stop)")
    sp.add_argument("--id", type=int, required=True, dest="can_id")
    sp.set_defaults(func="clear_protection")

    sp = sub.add_parser("zero", parents=[common], help="把当前姿态定义为 0°")
    sp.add_argument("--yes", action="store_true")
    sp.add_argument("--id", type=int, default=None, dest="can_id",
                    help="只 zero 这一个关节 (按 CAN ID); 不给则 zero 全部")
    sp.add_argument("--at-deg", type=float, default=0.0, dest="at_deg",
                    help="把当前姿态定义为该角度 (默认 0); 非 0 时必须配 --id")
    sp.set_defaults(func="zero")

    sp = sub.add_parser("state", parents=[common], help="显示软件角度状态")
    sp.set_defaults(func="state")

    sp = sub.add_parser("move", parents=[common], help="单关节相对运动")
    sp.add_argument("--id", type=int, required=True, dest="can_id")
    sp.add_argument("--deg", type=float, required=True, help="相对当前角度, 输出轴°")
    sp.add_argument("--allow-large", action="store_true")
    _motion_args(sp)
    sp.set_defaults(func="move")

    sp = sub.add_parser("move-all", parents=[common], help="多关节同步运动")
    sp.add_argument("--deg", required=True,
                    help='按关节序号的增量, 逗号分隔, 如 "10,-5,0,0,0,0"')
    sp.add_argument("--allow-large", action="store_true")
    _motion_args(sp)
    sp.set_defaults(func="move_all")

    sp = sub.add_parser("jog", parents=[common], help="单关节定速 (测试速度用)")
    sp.add_argument("--id", type=int, required=True, dest="can_id")
    sp.add_argument("--rpm", type=float, default=None, help="输出轴 RPM")
    sp.add_argument("--seconds", type=float, default=2.0,
                    help="运行秒数; 0=一直转到 Ctrl+C")
    sp.add_argument("--dir", choices=["cw", "ccw"], default="cw")
    sp.add_argument("--allow-long", action="store_true")
    sp.add_argument("--accel", type=int, default=10)
    sp.add_argument("--skip-voltage-check", action="store_true")
    sp.set_defaults(func="jog")

    sp = sub.add_parser("set-id", parents=[common], help="修改驱动器 ID (写入)")
    sp.add_argument("--old", type=int, required=True)
    sp.add_argument("--new", type=int, required=True)
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func="set_id")

    sp = sub.add_parser("monitor", parents=[common], help="轮询状态")
    sp.add_argument("--ids", default="1,2,3,4,5,6")
    sp.add_argument("--interval", type=float, default=0.5)
    sp.set_defaults(func="monitor")

    return p


def list_ports() -> int:
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        print("缺少 pyserial: pip install pyserial")
        return 2
    ports = list(lp.comports())
    if not ports:
        print("没有发现串口。检查 USB-CAN 是否插好、驱动是否安装。")
        return 0
    for p in ports:
        print(f"{p.device:<38} {p.description}  [{p.hwid}]")
    print("\nWindows: 用 --channel COMx")
    print("macOS:   用 --channel /dev/cu.usbmodemXXXX 或 /dev/cu.wchusbserialXXXX")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.func == "ports":
        return list_ports()

    needs_bus = args.func not in ("zero", "state")
    if needs_bus and not args.channel:
        print("[错误] 未指定 --channel。先运行: python armctl.py ports", file=sys.stderr)
        return 2

    cfg = load_config(Path(args.config))
    ctrl: Optional[ArmController] = None
    try:
        ctrl = ArmController(cfg, args)
        if args.func == "scan":
            return ctrl.scan(args.start, args.end)
        if args.func == "info":
            return ctrl.info(args.can_id)
        if args.func == "enable":
            return ctrl.enable(args.can_id)
        if args.func == "disable":
            return ctrl.disable(args.can_id)
        if args.func == "clear_protection":
            return ctrl.clear_protection(args.can_id)
        if args.func == "stop":
            if args.all:
                ctrl._touched.update(cfg.joint_ids())
            elif args.can_id is not None:
                ctrl._touched.add(args.can_id)
            else:
                raise ArmError("stop 需要 --id 或 --all")
            ctrl.stop_all()
            return 0
        if args.func == "zero":
            return ctrl.zero(args.yes, args.can_id, args.at_deg)
        if args.func == "state":
            return ctrl.show_state()
        if args.func == "move":
            return ctrl.move(args.can_id, args.deg, args.rpm, args.accel,
                             not args.no_wait, args.skip_voltage_check, args.allow_large,
                             args.wait_timeout)
        if args.func == "move_all":
            deltas = [float(x.strip()) for x in args.deg.replace(";", ",").split(",") if x.strip()]
            return ctrl.move_all(deltas, args.rpm, args.accel, not args.no_wait,
                                 args.skip_voltage_check, args.allow_large,
                                 args.wait_timeout)
        if args.func == "jog":
            return ctrl.jog(args.can_id, args.rpm, args.seconds, args.dir,
                            args.accel, args.skip_voltage_check, args.allow_long)
        if args.func == "set_id":
            return ctrl.set_id(args.old, args.new, args.yes)
        if args.func == "monitor":
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
            return ctrl.monitor(ids, args.interval)
        raise ArmError(f"未知命令: {args.func}")
    except SafetyError as exc:
        print(f"\n[安全检查拒绝] {exc}", file=sys.stderr)
        if ctrl is not None:
            ctrl.stop_all(quiet=True)
        return EXIT_SAFETY
    except KeyboardInterrupt:
        print("\n[中断] 正在停止所有已使能关节 ...", file=sys.stderr)
        if ctrl is not None:
            ctrl.stop_all(quiet=True)
        return 130
    except ArmError as exc:
        print(f"\n[错误] {exc}", file=sys.stderr)
        if ctrl is not None:
            ctrl.stop_all(quiet=True)
        return EXIT_COMM
    except Exception as exc:
        print(f"\n[异常] {type(exc).__name__}: {exc}", file=sys.stderr)
        if ctrl is not None:
            ctrl.stop_all(quiet=True)
        return EXIT_COMM
    finally:
        if ctrl is not None:
            ctrl.close()


if __name__ == "__main__":
    raise SystemExit(main())
