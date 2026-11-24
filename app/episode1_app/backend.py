"""Backends for the Episode 1 station.

The UI only talks to this interface, so a real SLCAN backend can be added without
touching widgets. `DemoBackend` is deliberately deterministic and hardware-free.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import sys
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Iterable, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from .i18n import tr
from .models import (
    JointState,
    Snapshot,
    STATUS_HOLD,
    STATUS_MOVING,
    STATUS_OFFLINE,
    STATUS_PROTECTED,
    STATUS_READY,
)

DEFAULT_JOINTS = [
    # index, name, can_id, min, max, gear
    (1, "Base", 1, -160.0, 160.0, 25.0),
    (2, "Shoulder", 2, -30.0, 45.0, 20.0),
    (3, "Elbow", 3, -86.5, 85.9, 25.0),
    (4, "Wrist pitch", 4, -134.5, 179.7, 10.0),
    (5, "Wrist roll", 5, -99.1, 100.9, 4.0),
    (6, "Tool flange", 6, -158.5, 158.5, 1.0),
]


class BackendBase(QObject):
    snapshotChanged = Signal(object)
    log = Signal(str, str)  # level, message
    connectionChanged = Signal(bool)
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect_device(self, port: str) -> None:
        raise NotImplementedError

    def disconnect_device(self) -> None:
        raise NotImplementedError

    def set_enabled(self, index: int, enabled: bool) -> None:
        raise NotImplementedError

    def jog(self, index: int, delta_deg: float, rpm: float) -> None:
        raise NotImplementedError

    def jog_raw(self, index: int, delta_deg: float, rpm: float) -> None:
        """Jog without soft-limit checks; only for limit calibration."""
        raise NotImplementedError

    def set_limits(self, index: int, min_deg: float, max_deg: float) -> None:
        raise NotImplementedError

    def move(self, index: int, angle_deg: float, rpm: float, accel: int) -> None:
        raise NotImplementedError

    def move_all(self, angles: Iterable[float], rpm: float, accel: int) -> None:
        raise NotImplementedError

    def stop_all(self) -> None:
        raise NotImplementedError

    def clear_protection(self, index: int) -> None:
        raise NotImplementedError

    def zero(self, index: int) -> None:
        raise NotImplementedError

    def snapshot(self) -> Snapshot:
        raise NotImplementedError

    def _emit_log(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.emit(level, f"{stamp}  {message}")


class DemoBackend(BackendBase):
    """A live-looking simulator used for UI development and screenshots."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._joints: List[JointState] = []
        self._port = "DEMO"
        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(160)
        self._timer.timeout.connect(self._tick)
        self._noise = random.Random(7)
        self._start_pose = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    # ---- lifecycle -----------------------------------------------------
    def connect_device(self, port: str) -> None:
        self._port = port or "DEMO"
        self._joints = [
            JointState(
                index=i,
                name=name,
                can_id=cid,
                angle=self._start_pose[i - 1],
                target=self._start_pose[i - 1],
                enabled=True,
                status=STATUS_READY,
                min_deg=lo,
                max_deg=hi,
                gear_ratio=gear,
                current_a=0.02 + 0.01 * i,
                temp_c=33.0 + i * 0.6,
            )
            for i, name, cid, lo, hi, gear in DEFAULT_JOINTS
        ]
        self._connected = True
        self._t0 = time.monotonic()
        self._timer.start()
        self.connectionChanged.emit(True)
        self._emit_log("ok", tr("log.connected", port=self._port))
        self._emit_log("info", tr("log.firmware"))
        self.snapshotChanged.emit(self.snapshot())

    def disconnect_device(self) -> None:
        self._timer.stop()
        self._connected = False
        self.connectionChanged.emit(False)
        self._emit_log("warn", tr("log.closed"))
        self.snapshotChanged.emit(self.snapshot())

    # ---- state ---------------------------------------------------------
    def _joint(self, index: int) -> JointState:
        for j in self._joints:
            if j.index == index:
                return j
        raise KeyError(index)

    def snapshot(self) -> Snapshot:
        t = time.monotonic() - self._t0
        moving = any(j.status == STATUS_MOVING for j in self._joints)
        voltage = 12.02 + 0.02 * math.sin(t * 0.8) - (0.04 if moving else 0.0)
        current = 0.08 + (0.42 if moving else 0.0) + 0.01 * math.sin(t * 2.3)
        temp = 35.2 + 0.25 * math.sin(t * 0.17)
        return Snapshot(
            connected=self._connected,
            port=self._port,
            voltage=round(voltage, 2),
            current_a=round(current, 2),
            temp_c=round(temp, 1),
            latency_ms=round(17.0 + 2.0 * math.sin(t * 1.7), 1),
            loop_hz=20.0,
            joints=list(self._joints),
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )

    def _tick(self) -> None:
        if not self._connected:
            return
        for j in self._joints:
            if not j.enabled:
                j.status = STATUS_HOLD
                continue
            if j.status == STATUS_PROTECTED:
                continue
            err = j.target - j.angle
            if abs(err) > 0.035:
                # Simulated output-shaft slew: deliberately unhurried.
                step = max(-1.1, min(1.1, err * 0.45))
                j.angle = round(j.angle + step, 4)
                j.status = STATUS_MOVING
            else:
                j.angle = round(j.target, 4)
                j.status = STATUS_READY
            j.current_a = round(0.05 + (0.38 if j.status == STATUS_MOVING else 0.02), 2)
        self.snapshotChanged.emit(self.snapshot())

    def _check_limits(self, j: JointState, value: float) -> bool:
        if value < j.min_deg or value > j.max_deg:
            msg = tr("log.limit", index=j.index, value=value, lo=j.min_deg, hi=j.max_deg)
            self._emit_log("error", msg)
            self.error.emit(msg)
            return False
        return True

    # ---- commands ------------------------------------------------------
    def set_enabled(self, index: int, enabled: bool) -> None:
        j = self._joint(index)
        j.enabled = enabled
        if not enabled:
            j.target = j.angle
            j.status = STATUS_HOLD
            self._emit_log("warn", tr("log.disabled", index=index))
        else:
            j.status = STATUS_READY
            self._emit_log("ok", tr("log.enabled", index=index))
        self.snapshotChanged.emit(self.snapshot())

    def jog(self, index: int, delta_deg: float, rpm: float) -> None:
        j = self._joint(index)
        if not self._check_limits(j, j.target + delta_deg):
            return
        if not j.enabled:
            self._emit_log("warn", tr("log.needs_enable", index=index))
            return
        j.target = round(j.target + delta_deg, 3)
        j.status = STATUS_MOVING
        self._emit_log(
            "cmd",
            tr("log.jog", index=index, delta=delta_deg, target=j.target, rpm=rpm),
        )
        self.snapshotChanged.emit(self.snapshot())

    def jog_raw(self, index: int, delta_deg: float, rpm: float) -> None:
        j = self._joint(index)
        if not j.enabled:
            self._emit_log("warn", tr("log.needs_enable", index=index))
            return
        j.target = round(j.target + delta_deg, 3)
        j.status = STATUS_MOVING
        self._emit_log("cmd", tr("log.jog", index=index, delta=delta_deg, target=j.target, rpm=rpm))
        self.snapshotChanged.emit(self.snapshot())

    def set_limits(self, index: int, min_deg: float, max_deg: float) -> None:
        j = self._joint(index)
        j.min_deg = float(min_deg)
        j.max_deg = float(max_deg)
        self._emit_log("ok", tr("log.limits", index=index, lo=j.min_deg, hi=j.max_deg))
        self.snapshotChanged.emit(self.snapshot())

    def move(self, index: int, angle_deg: float, rpm: float, accel: int) -> None:
        j = self._joint(index)
        if not self._check_limits(j, angle_deg):
            return
        if not j.enabled:
            self._emit_log("warn", tr("log.needs_enable", index=index))
            return
        j.target = round(angle_deg, 3)
        j.status = STATUS_MOVING
        self._emit_log(
            "cmd",
            tr("log.move", index=index, target=j.target, rpm=rpm, accel=accel),
        )
        self.snapshotChanged.emit(self.snapshot())

    def move_all(self, angles: Iterable[float], rpm: float, accel: int) -> None:
        values = list(angles)
        if len(values) != len(self._joints):
            self._emit_log("error", "move-all needs six angles")
            return
        for j, value in zip(self._joints, values):
            if not self._check_limits(j, value):
                return
        for j, value in zip(self._joints, values):
            j.target = round(value, 3)
            j.status = STATUS_MOVING if abs(j.target - j.angle) > 0.01 else STATUS_READY
        self._emit_log(
            "cmd",
            tr("log.move_all", values=", ".join(f"{v:+.1f}" for v in values), rpm=rpm),
        )
        self.snapshotChanged.emit(self.snapshot())

    def stop_all(self) -> None:
        for j in self._joints:
            j.target = j.angle
            if j.status != STATUS_PROTECTED:
                j.status = STATUS_READY if j.enabled else STATUS_HOLD
        self._emit_log("warn", tr("log.stop"))
        self.snapshotChanged.emit(self.snapshot())

    def clear_protection(self, index: int) -> None:
        j = self._joint(index)
        j.status = STATUS_READY if j.enabled else STATUS_HOLD
        self._emit_log("ok", tr("log.cleared", index=index))
        self.snapshotChanged.emit(self.snapshot())

    def zero(self, index: int) -> None:
        j = self._joint(index)
        j.angle = 0.0
        j.target = 0.0
        j.status = STATUS_READY if j.enabled else STATUS_HOLD
        self._emit_log("warn", tr("log.zero", index=index))
        self.snapshotChanged.emit(self.snapshot())


class SlcanBackend(BackendBase):
    """Real arm backend: python-can SLCAN + the project's ArmController.

    All blocking CAN work runs on a single-worker executor so the Qt event loop
    stays responsive. Commands are serialized: a long move blocks the next poll
    or command instead of overlapping on the bus.
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._snapshot = Snapshot(protocol="SLCAN / 500 kbit/s")
        self._ctl = None
        self._armctl = None
        self._config_path: Optional[Path] = None
        self._port = ""
        self._joints: List[JointState] = []
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="arm-can")
        self._bus_lock = threading.RLock()
        self._poll_pending = False
        self._generation = 0
        self._timer = QTimer(self)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self._poll)

    # ---- lifecycle -----------------------------------------------------
    def connect_device(self, port: str) -> None:
        if self._connected:
            self.disconnect_device()
        self._generation += 1
        self._poll_pending = False
        if getattr(sys, "frozen", False):
            base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            arm_dir = base / "arm"
            if sys.platform.startswith("win"):
                state_dir = Path(os.environ.get("APPDATA", Path.home())) / "Episode1"
            elif sys.platform == "darwin":
                state_dir = Path.home() / "Library" / "Application Support" / "Episode1"
            else:
                state_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Episode1"
            state_dir.mkdir(parents=True, exist_ok=True)
            state_path = state_dir / ".arm_state.json"
            config_path = state_dir / "joints.json"
            bundled = arm_dir / "config" / "joints.json"
            if not config_path.exists() and bundled.exists():
                shutil.copy2(bundled, config_path)
        else:
            arm_dir = Path(__file__).resolve().parents[2] / "arm"
            state_path = arm_dir / "config" / ".arm_state.json"
            config_path = arm_dir / "config" / "joints.json"
        if not (arm_dir / "armctl.py").exists():
            raise RuntimeError(f"找不到 armctl.py: {arm_dir}")
        if str(arm_dir) not in sys.path:
            sys.path.insert(0, str(arm_dir))
        import armctl  # local import: package only needed for hardware

        self._config_path = config_path
        cfg = armctl.load_config(config_path)
        args = argparse.Namespace(
            iface="slcan", channel=port, bitrate=500000, timeout=0.5,
            state=str(state_path),
            microstep=cfg.microstep, firmware=cfg.firmware,
            skip_voltage_check=False,
        )
        ctl = armctl.ArmController(cfg, args)
        self._emit_log("info", tr("log.connecting", port=port))
        try:
            ctl.scan(1, 6)
            found = []
            for cid in range(1, 7):
                try:
                    if ctl.motor(cid).ping() is not None:
                        found.append(cid)
                except Exception:
                    pass
            if len(found) != 6:
                raise RuntimeError(
                    f"只发现 {len(found)} 个驱动器 {found}; 需要 ID 1–6 全部在线"
                )
            self._ctl = ctl
            self._armctl = armctl
            self._port = port
            self._joints = [
                JointState(
                    index=j.index, name=j.name, can_id=j.can_id,
                    angle=ctl.state.angle(j.index), target=ctl.state.angle(j.index),
                    enabled=False, status=STATUS_OFFLINE,
                    min_deg=j.min_deg if j.min_deg is not None else -180.0,
                    max_deg=j.max_deg if j.max_deg is not None else 180.0,
                    gear_ratio=j.gear_ratio,
                )
                for j in sorted(cfg.joints, key=lambda x: x.index)
            ]
            self._snapshot = self._read_hw()
            self._connected = True
            self._timer.start()
            self.connectionChanged.emit(True)
            self._emit_log("ok", tr("log.connected", port=port))
            self._emit_log("info", tr("log.firmware"))
            self.snapshotChanged.emit(self._snapshot)
            if not ctl.state.valid:
                self._emit_log("warn", tr("msg.state_invalid"))
        except Exception:
            try:
                ctl.close()
            except Exception:
                pass
            self._ctl = None
            self._armctl = None
            self._joints = []
            self._connected = False
            self.connectionChanged.emit(False)
            raise

    def disconnect_device(self) -> None:
        # Invalidate in-flight poll callbacks before touching the bus.
        self._connected = False
        self._generation += 1
        self._poll_pending = False
        self._timer.stop()
        if self._ctl is not None:
            with self._bus_lock:
                try:
                    self._ctl.stop_all(quiet=True)
                except Exception as exc:  # noqa: BLE001
                    self._emit_log("error", str(exc))
                finally:
                    try:
                        self._ctl.close()
                    except Exception:
                        pass
        self._ctl = None
        self._armctl = None
        self._snapshot = Snapshot(
            connected=False, port=self._port, protocol="SLCAN / 500 kbit/s",
            joints=[], timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        self.connectionChanged.emit(False)
        self.snapshotChanged.emit(self._snapshot)
        self._emit_log("warn", tr("log.closed"))

    def shutdown(self) -> None:
        """Stop the poll timer and release the executor at app exit."""
        self._timer.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ---- telemetry -----------------------------------------------------
    def _read_hw(self) -> Snapshot:
        assert self._ctl is not None
        with self._bus_lock:
            return self._read_hw_locked()

    def _read_hw_locked(self) -> Snapshot:
        t0 = time.monotonic()
        voltage = current = temp = 0.0
        joints: List[JointState] = []
        for js in self._joints:
            j = self._ctl.cfg.by_can_id(js.can_id)
            status = STATUS_OFFLINE
            enabled = False
            try:
                m = self._ctl.motor(js.can_id)
                st = m.get_motor_status()
                enabled = bool(st.enabled)
                if st.stall_protected:
                    status = STATUS_PROTECTED
                elif not st.position_reached:
                    status = STATUS_MOVING
                else:
                    status = STATUS_READY if enabled else STATUS_HOLD
                if js.index == 1:
                    v = m.get_bus_voltage()
                    voltage = (float(v) / 1000.0) if v is not None else 0.0
                    i = m.get_phase_current()
                    current = (float(i) / 1000.0) if i is not None else 0.0
                    t = m.get_temperature()
                    temp = float(t) if t is not None else 0.0
            except Exception:
                status = STATUS_OFFLINE
            angle = self._ctl.state.angle(js.index)
            joints.append(JointState(
                index=js.index, name=js.name, can_id=js.can_id,
                angle=angle, target=angle, enabled=enabled, status=status,
                min_deg=js.min_deg, max_deg=js.max_deg,
                gear_ratio=js.gear_ratio, current_a=current, temp_c=temp,
            ))
        return Snapshot(
            connected=True, port=self._port, protocol="SLCAN / 500 kbit/s",
            voltage=voltage, current_a=current, temp_c=temp,
            latency_ms=(time.monotonic() - t0) * 1000.0, loop_hz=1.6,
            joints=joints, timestamp=datetime.now().strftime("%H:%M:%S"),
        )

    def _poll(self) -> None:
        if not self._connected or self._ctl is None or self._poll_pending:
            return
        self._poll_pending = True
        gen = self._generation
        fut = self._executor.submit(self._read_hw)
        def done(f):
            if gen != self._generation:
                return
            self._poll_pending = False
            try:
                self._snapshot = f.result()
                self.snapshotChanged.emit(self._snapshot)
            except Exception as exc:
                self.error.emit(str(exc))
                self._emit_log("error", str(exc))
        fut.add_done_callback(done)

    # ---- helpers -------------------------------------------------------
    def _run(self, fn, ok_message: str = "") -> None:
        gen = self._generation
        def guarded():
            with self._bus_lock:
                return fn()
        fut = self._executor.submit(guarded)
        def done(f):
            if gen != self._generation:
                return
            try:
                f.result()
            except Exception as exc:
                self.error.emit(str(exc))
                self._emit_log("error", str(exc))
                return
            if ok_message:
                self._emit_log("ok", ok_message)
            self._poll()
        fut.add_done_callback(done)

    def _joint(self, index: int) -> JointState:
        for j in self._joints:
            if j.index == index:
                return j
        raise ValueError(f"joint {index} not found")

    def _can(self, index: int) -> int:
        return self._joint(index).can_id

    # ---- commands ------------------------------------------------------
    def set_enabled(self, index: int, enabled: bool) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        cid = self._can(index)
        if enabled:
            self._run(lambda: self._ctl.enable(cid), tr("log.enabled", index=index))
        else:
            self._run(lambda: self._ctl.disable(cid), tr("log.disabled", index=index))

    def _max_step(self) -> float:
        return max(0.1, float(self._ctl.cfg.max_step_deg))

    def jog(self, index: int, delta_deg: float, rpm: float) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        cid = self._can(index)
        j = self._ctl.cfg.by_can_id(cid)
        # Validate against the current state; recompute target in the worker
        # so commands queued back-to-back do not use a stale base angle.
        target = self._ctl.state.angle(j.index) + delta_deg
        j.check_target(target)
        def fn():
            target = self._ctl.state.angle(j.index) + delta_deg
            j.check_target(target)
            # armctl rejects a single move above max_step_deg; split it.
            remaining = float(delta_deg)
            while abs(remaining) > 1e-9:
                step = max(-self._max_step(), min(self._max_step(), remaining))
                self._ctl.move(cid, step, rpm=rpm, accel=1, wait=True,
                               skip_voltage=False, allow_large=False, wait_timeout=30.0)
                remaining -= step
        self._run(fn, tr("log.jog", index=index, delta=delta_deg, target=target, rpm=rpm))

    def jog_raw(self, index: int, delta_deg: float, rpm: float) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        cid = self._can(index)
        j = self._ctl.cfg.by_can_id(cid)
        target = self._ctl.state.angle(j.index) + delta_deg

        def fn():
            remaining = float(delta_deg)
            while abs(remaining) > 1e-9:
                step = max(-self._max_step(), min(self._max_step(), remaining))
                self._ctl.move(cid, step, rpm=rpm, accel=1, wait=True,
                               skip_voltage=False, allow_large=False,
                               wait_timeout=30.0, check_limits=False)
                remaining -= step
        self._run(fn, tr("log.jog", index=index, delta=delta_deg, target=target, rpm=rpm))

    def set_limits(self, index: int, min_deg: float, max_deg: float) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        if min_deg >= max_deg:
            raise ValueError("min must be smaller than max")
        j = self._ctl.cfg.by_index(index)
        j.min_deg = float(min_deg)
        j.max_deg = float(max_deg)
        for item in self._joints:
            if item.index == index:
                item.min_deg = float(min_deg)
                item.max_deg = float(max_deg)
        if self._config_path is not None:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            for row in data.get("joints", []):
                if int(row.get("joint", row.get("id", -1))) == index:
                    row["min_deg"] = float(min_deg)
                    row["max_deg"] = float(max_deg)
            tmp = self._config_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(self._config_path)
        for item in self._snapshot.joints:
            if item.index == index:
                item.min_deg = float(min_deg)
                item.max_deg = float(max_deg)
        self._emit_log("ok", tr("log.limits", index=index, lo=min_deg, hi=max_deg))
        self.snapshotChanged.emit(self._snapshot)

    def move(self, index: int, angle_deg: float, rpm: float, accel: int) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        cid = self._can(index)
        j = self._ctl.cfg.by_can_id(cid)
        j.check_target(angle_deg)
        def fn():
            remaining = angle_deg - self._ctl.state.angle(j.index)
            while abs(remaining) > 1e-9:
                step = max(-self._max_step(), min(self._max_step(), remaining))
                self._ctl.move(cid, step, rpm=rpm, accel=accel, wait=True,
                               skip_voltage=False, allow_large=False, wait_timeout=60.0)
                remaining -= step
        self._run(fn, tr("log.move", index=index, target=angle_deg, rpm=rpm, accel=accel))

    def move_all(self, angles: Iterable[float], rpm: float, accel: int) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        values = list(angles)
        joints = sorted(self._ctl.cfg.joints, key=lambda x: x.index)
        if len(values) != len(joints):
            raise ValueError("move-all needs six angles")
        for j, target in zip(joints, values):
            j.check_target(target)
        def fn():
            remaining = [target - self._ctl.state.angle(j.index)
                         for j, target in zip(joints, values)]
            while max(abs(d) for d in remaining) > 1e-9:
                chunk = [max(-self._max_step(), min(self._max_step(), d)) for d in remaining]
                self._ctl.move_all(chunk, rpm=rpm, accel=accel, wait=True,
                                   skip_voltage=False, allow_large=False, wait_timeout=60.0)
                remaining = [r - c for r, c in zip(remaining, chunk)]
        self._run(fn, tr("log.move_all", values=", ".join(f"{v:+.1f}" for v in values), rpm=rpm))

    def stop_all(self) -> None:
        if self._ctl is None:
            return
        self._run(lambda: self._ctl.stop_all(), tr("log.stop"))

    def clear_protection(self, index: int) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        cid = self._can(index)
        self._run(lambda: self._ctl.clear_protection(cid), tr("log.cleared", index=index))

    def zero(self, index: int) -> None:
        if self._ctl is None:
            raise RuntimeError(tr("msg.connect_first"))
        cid = self._can(index)
        self._run(lambda: self._ctl.zero(True, can_id=cid), tr("log.zero", index=index))

    def snapshot(self) -> Snapshot:
        return self._snapshot
