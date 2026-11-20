"""Tiny runtime translation layer: 中文 / English / Русский.

The UI is rebuilt when the language changes, so every visible string is
re-read through `tr()`.  Keeping the dictionaries here avoids Qt .ts tooling
and makes the three languages easy to audit in one place.
"""
from __future__ import annotations

from typing import Dict

LANGUAGES = (("zh", "中文"), ("en", "EN"), ("ru", "РУ"))

_STRINGS: Dict[str, Dict[str, str]] = {
    "app.title": {
        "zh": "Episode 1 · 机械臂控制站",
        "en": "Episode 1 · Arm Control Station",
        "ru": "Episode 1 · Пульт управления рукой",
    },
    "app.sub": {
        "zh": "六轴机械臂控制站  /  托木斯克理工 2026",
        "en": "ARM CONTROL STATION  /  TPU ROBOTICS 2026",
        "ru": "СТАНЦИЯ УПРАВЛЕНИЯ РУКОЙ  /  ТПУ 2026",
    },
    "app.version": {
        "zh": "正式版 1.0.0  ·  桌面端",
        "en": "RELEASE 1.0.0  ·  DESKTOP",
        "ru": "ВЕРСИЯ 1.0.0  ·  DESKTOP",
    },
    "language": {"zh": "语言", "en": "LANG", "ru": "ЯЗЫК"},
    "link.online": {"zh": "●  已连接", "en": "●  LINK ONLINE", "ru": "●  СВЯЗЬ ЕСТЬ"},
    "link.offline": {"zh": "●  未连接", "en": "●  LINK OFFLINE", "ru": "●  СВЯЗИ НЕТ"},
    "port": {"zh": "端口", "en": "PORT", "ru": "ПОРТ"},
    "connect": {"zh": "连接", "en": "Connect", "ru": "Подключить"},
    "disconnect": {"zh": "断开", "en": "Disconnect", "ru": "Отключить"},
    "stop_all": {"zh": "■  全部停止", "en": "■  STOP ALL", "ru": "■  СТОП"},
    "axes.online": {"zh": "●  6 轴在线", "en": "●  6 AXES ONLINE", "ru": "●  6 ОСЕЙ В СЕТИ"},
    "axes.offline": {"zh": "●  6 轴离线", "en": "●  6 AXES OFFLINE", "ru": "●  6 ОСЕЙ НЕТ"},
    "workspace": {"zh": "工作区", "en": "WORKSPACE", "ru": "РАБОЧАЯ ОБЛАСТЬ"},
    "nav.overview": {"zh": "总览", "en": "Overview", "ru": "Обзор"},
    "nav.joint": {"zh": "关节控制", "en": "Joint control", "ru": "Управление осями"},
    "nav.fk": {"zh": "正逆运动学", "en": "FK / IK", "ru": "Кинематика"},
    "nav.config": {"zh": "配置", "en": "Configuration", "ru": "Конфигурация"},
    "nav.log": {"zh": "事件日志", "en": "Event log", "ru": "Журнал событий"},
    "bridge.title": {"zh": "SLCAN 桥", "en": "SLCAN BRIDGE", "ru": "МОСТ SLCAN"},
    "bridge.protocol": {"zh": "500 kbit/s  ·  CAN 2.0A", "en": "500 kbit/s  ·  CAN 2.0A", "ru": "500 кбит/с  ·  CAN 2.0A"},
    "bridge.adapter": {"zh": "UTC-T01 / CH340", "en": "UTC-T01 / CH340", "ru": "UTC-T01 / CH340"},
    "page.overview.title": {"zh": "总览", "en": "Overview", "ru": "Обзор"},
    "page.overview.sub": {
        "zh": "六轴实时遥测与手动命令台",
        "en": "Six-axis live telemetry and manual command console",
        "ru": "Телеметрия шести осей и ручное управление",
    },
    "page.joint.title": {"zh": "关节控制", "en": "Joint control", "ru": "Управление осями"},
    "page.joint.sub": {
        "zh": "单轴点动、目标角度和使能控制",
        "en": "Per-joint jog, target move and enable control",
        "ru": "Покачивание, целевой угол и включение оси",
    },
    "page.fk.title": {"zh": "正逆运动学", "en": "FK / IK", "ru": "Прямая / обратная задача"},
    "page.fk.sub": {
        "zh": "由关节角计算末端位姿，或由目标位姿求关节角",
        "en": "Joint angles to TCP pose, or target pose to joint angles",
        "ru": "Углы в позу TCP или целевая поза в углы",
    },
    "page.config.title": {"zh": "配置", "en": "Configuration", "ru": "Конфигурация"},
    "page.config.sub": {
        "zh": "减速比、软限位与零点标定",
        "en": "Ratios, soft limits and zero calibration",
        "ru": "Передаточные числа, пределы и нули",
    },
    "page.log.title": {"zh": "事件日志", "en": "Event log", "ru": "Журнал событий"},
    "page.log.sub": {"zh": "完整控制器事件记录", "en": "Full controller event history", "ru": "Полная история событий"},
    "metric.voltage": {"zh": "母线电压", "en": "Bus voltage", "ru": "Напряжение шины"},
    "metric.voltage.note": {"zh": "驱动器输入", "en": "driver input", "ru": "вход драйвера"},
    "metric.current": {"zh": "相电流", "en": "Phase current", "ru": "Фазный ток"},
    "metric.current.note": {"zh": "J1..J6 平均", "en": "J1..J6 average", "ru": "среднее J1..J6"},
    "metric.temp": {"zh": "驱动器温度", "en": "Driver temp", "ru": "Температура драйвера"},
    "metric.temp.note": {"zh": "六轴最大值", "en": "max of six", "ru": "максимум из шести"},
    "metric.loop": {"zh": "控制周期", "en": "Control loop", "ru": "Цикл управления"},
    "metric.loop.note": {"zh": "轮询周期", "en": "poll period", "ru": "период опроса"},
    "joints.title": {"zh": "关节遥测", "en": "JOINT TELEMETRY", "ru": "ТЕЛЕМЕТРИЯ ОСЕЙ"},
    "joints.hint": {
        "zh": "单击选择  ·  双击使能/失能",
        "en": "click a card to select  ·  double-click power",
        "ru": "клик — выбрать  ·  двойной клик — питание",
    },
    "joint.1": {"zh": "底座", "en": "Base", "ru": "Основание"},
    "joint.2": {"zh": "大臂", "en": "Shoulder", "ru": "Плечо"},
    "joint.3": {"zh": "小臂", "en": "Elbow", "ru": "Локоть"},
    "joint.4": {"zh": "腕俯仰", "en": "Wrist pitch", "ru": "Наклон кисти"},
    "joint.5": {"zh": "腕旋转", "en": "Wrist roll", "ru": "Вращение кисти"},
    "joint.6": {"zh": "末端法兰", "en": "Tool flange", "ru": "Фланец инструмента"},
    "status.ready": {"zh": "就绪", "en": "READY", "ru": "ГОТОВ"},
    "status.moving": {"zh": "运动", "en": "MOVING", "ru": "ДВИЖЕНИЕ"},
    "status.hold": {"zh": "保持", "en": "HOLD", "ru": "УДЕРЖАНИЕ"},
    "status.protected": {"zh": "保护", "en": "PROTECTED", "ru": "ЗАЩИТА"},
    "status.offline": {"zh": "离线", "en": "OFFLINE", "ru": "НЕТ СВЯЗИ"},
    "on": {"zh": "开", "en": "ON", "ru": "ВКЛ"},
    "off": {"zh": "关", "en": "OFF", "ru": "ВЫКЛ"},
    "target": {"zh": "目标", "en": "target", "ru": "цель"},
    "limits": {"zh": "限位", "en": "limits", "ru": "пределы"},
    "deg": {"zh": "度", "en": "deg", "ru": "град"},
    "manual.title": {"zh": "手动控制", "en": "MANUAL CONTROL", "ru": "РУЧНОЕ УПРАВЛЕНИЕ"},
    "manual.position": {"zh": "位置", "en": "position", "ru": "позиция"},
    "field.target": {"zh": "目标角度  /  度", "en": "TARGET ANGLE  /  deg", "ru": "ЦЕЛЕВОЙ УГОЛ  /  град"},
    "field.speed": {"zh": "速度  /  RPM", "en": "SPEED  /  RPM", "ru": "СКОРОСТЬ  /  RPM"},
    "field.accel": {"zh": "加速度", "en": "ACCEL", "ru": "УСКОР."},
    "field.jog": {"zh": "点动  /  相对当前角度", "en": "JOG  /  relative to current", "ru": "ПОКАЧИВАНИЕ  /  от текущего"},
    "action.move": {"zh": "运动到目标", "en": "Move to target", "ru": "В цель"},
    "action.zero": {"zh": "设为零点", "en": "Set zero", "ru": "Задать ноль"},
    "action.clear": {"zh": "清除保护", "en": "Clear protect", "ru": "Снять защиту"},
    "action.disable": {"zh": "失能所选关节", "en": "Disable selected joint", "ru": "Отключить ось"},
    "action.enable": {"zh": "使能所选关节", "en": "Enable selected joint", "ru": "Включить ось"},
    "note.safety": {
        "zh": "所有命令先经过软限位检查。全部停止只取消运动，不切断 12 V 电源。",
        "en": "Soft limits are enforced before any command. STOP ALL cancels motion; it does not cut power.",
        "ru": "Перед командой проверяются программные пределы. СТОП отменяет движение, но не снимает питание.",
    },
    "bottom.workspace": {"zh": "工作空间  /  侧视", "en": "WORKSPACE  /  SIDE VIEW", "ru": "РАБОЧАЯ ЗОНА  /  ВИД СБОКУ"},
    "bottom.projection": {"zh": "J2 / J3 投影", "en": "J2 / J3 projection", "ru": "Проекция J2 / J3"},
    "bottom.illustrative": {"zh": "侧视示意，非等比", "en": "illustrative, not to scale", "ru": "схема, не в масштабе"},
    "log.live": {"zh": "●  实时", "en": "●  LIVE", "ru": "●  ОНЛАЙН"},
    "msg.ready": {"zh": "Episode 1 控制站就绪 · 离线预览", "en": "Episode 1 station ready · offline preview", "ru": "Пульт Episode 1 готов · офлайн-просмотр"},
    "msg.backend": {"zh": "后端：Demo（无硬件）；下一步接 SLCAN。", "en": "Backend: Demo (no hardware). SLCAN link is next.", "ru": "Бэкенд: Demo (без железа). Далее — SLCAN."},
    "msg.safety": {"zh": "安全包络：12–32 V · 六轴软限位 · 全部停止可用", "en": "Safety envelope: 12–32 V · 6-axis soft limits · STOP ALL available", "ru": "Защита: 12–32 В · пределы 6 осей · СТОП доступен"},
    "msg.selected": {"zh": "已选择 J{index}", "en": "Selected J{index}", "ru": "Выбрана ось J{index}"},
    "msg.connect_first": {"zh": "请先连接控制器", "en": "Connect the controller first", "ru": "Сначала подключите контроллер"},
    "msg.offline_stop": {"zh": "离线状态按下停止 — 没有连接", "en": "STOP pressed while offline — no link", "ru": "СТОП без связи — соединения нет"},
    "msg.port_placeholder": {"zh": "当前为 Demo 模式；硬件后端未接入时不会发送命令。", "en": "Demo mode. No hardware command is sent until the SLCAN backend is connected.", "ru": "Режим Demo. Команды на железо не отправляются до подключения SLCAN."},
    "msg.connect_failed": {"zh": "连接失败：{error}", "en": "Connection failed: {error}", "ru": "Ошибка подключения: {error}"},
    "msg.zero_confirm.title": {"zh": "确认设置零点", "en": "Confirm zero", "ru": "Подтвердить ноль"},
    "msg.zero_confirm.body": {
        "zh": "把 J{index} 当前姿态定义为 0°？这会改变软限位参考点，不会驱动电机。",
        "en": "Define the current J{index} pose as 0°? This changes the soft-limit reference; the motor will not move.",
        "ru": "Принять текущее положение J{index} за 0°? Это изменит опорную точку пределов; мотор не двинется.",
    },
    "msg.language": {"zh": "界面语言已切换为中文", "en": "UI language switched to English", "ru": "Язык интерфейса переключён на русский"},
    "kin.title": {
        "zh": "正 / 逆运动学工作台",
        "en": "Forward / Inverse Kinematics",
        "ru": "Прямая / обратная кинематика",
    },
    "kin.sub": {
        "zh": "官方 DH 模型；FK 由关节角算 TCP，IK 用阻尼最小二乘数值解。角度单位 °，位置 mm。",
        "en": "Official DH model; FK computes TCP from joint angles, IK uses damped least squares. Degrees, millimetres.",
        "ru": "Официальная DH-модель; FK считает TCP по углам, IK — демпфированный МНК. Градусы, миллиметры.",
    },
    "kin.joints": {
        "zh": "关节角 q（DH）", "en": "Joint angles q (DH)", "ru": "Углы q (DH)",
    },
    "kin.target": {
        "zh": "目标位姿（TCP）", "en": "Target pose (TCP)", "ru": "Целевая поза (TCP)",
    },
    "kin.fk": {"zh": "计算 FK", "en": "Compute FK", "ru": "Прямая задача"},
    "kin.ik": {"zh": "求解 IK", "en": "Solve IK", "ru": "Обратная задача"},
    "kin.close": {"zh": "关闭", "en": "Close", "ru": "Закрыть"},
    "kin.ready": {"zh": "输入角度后计算。", "en": "Enter angles and compute.", "ru": "Введите углы и вычислите."},
    "kin.fk_ok": {
        "zh": "FK: TCP = ({x}, {y}, {z}) mm",
        "en": "FK: TCP = ({x}, {y}, {z}) mm",
        "ru": "FK: TCP = ({x}, {y}, {z}) мм",
    },
    "kin.result": {
        "zh": "TCP x={x} y={y} z={z} mm；RPY r={r} p={p} y={yaw} °",
        "en": "TCP x={x} y={y} z={z} mm; RPY r={r} p={p} y={yaw} °",
        "ru": "TCP x={x} y={y} z={z} мм; RPY r={r} p={p} y={yaw} °",
    },
    "kin.ik_ok": {
        "zh": "IK 收敛：位置误差 {e} mm，姿态误差 {r}°",
        "en": "IK converged: position error {e} mm, rotation error {r}°",
        "ru": "IK сошлась: ошибка позиции {e} мм, ориентации {r}°",
    },
    "kin.unreachable": {
        "zh": "IK 未收敛：位置误差 {e} mm，姿态误差 {r}°（可能超出工作空间）",
        "en": "IK did not converge: position error {e} mm, rotation error {r}° (possibly unreachable)",
        "ru": "IK не сошлась: ошибка позиции {e} мм, ориентации {r}° (возможно, вне зоны)",
    },
    "kin.error": {
        "zh": "计算失败：{error}", "en": "Calculation failed: {error}", "ru": "Ошибка расчёта: {error}",
    },
    "log.connecting": {
        "zh": "正在连接 {port} … 扫描 CAN ID 1–6",
        "en": "Connecting to {port} … scanning CAN IDs 1–6",
        "ru": "Подключение к {port} … сканирование CAN ID 1–6",
    },
    "msg.state_invalid": {
        "zh": "软件零点状态不完整；运动前请对相应关节重新 zero。",
        "en": "Software zero state is incomplete; re-zero the affected joints before motion.",
        "ru": "Состояние программных нулей неполное; перед движением задайте нули заново.",
    },
    "log.connected": {
        "zh": "已连接 {port} · 6 轴在线 · 500 kbit/s",
        "en": "Connected to {port} · 6 axes online · 500 kbit/s",
        "ru": "Подключено: {port} · 6 осей · 500 кбит/с",
    },
    "log.firmware": {
        "zh": "固件 V1.0.2 · hw_series=2 (Y42) · 细分 16",
        "en": "Firmware V1.0.2 · hw_series=2 (Y42) · microstep 16",
        "ru": "Прошивка V1.0.2 · hw_series=2 (Y42) · микрошаг 16",
    },
    "log.closed": {
        "zh": "链路已关闭，不再轮询电机。",
        "en": "Link closed. Motors are no longer being polled.",
        "ru": "Связь закрыта. Опрос моторов остановлен.",
    },
    "log.enabled": {"zh": "J{index} 已使能", "en": "J{index} enabled", "ru": "J{index} включена"},
    "log.disabled": {"zh": "J{index} 已失能，保持力矩释放", "en": "J{index} disabled — holding torque released", "ru": "J{index} отключена — удержание снято"},
    "log.jog": {"zh": "J{index} 点动 {delta:+.2f}° → {target:+.2f}°  @ {rpm:.2f} RPM", "en": "J{index} jog {delta:+.2f}° → {target:+.2f}°  @ {rpm:.2f} RPM", "ru": "J{index} покачивание {delta:+.2f}° → {target:+.2f}°  @ {rpm:.2f} RPM"},
    "log.move": {"zh": "J{index} 运动 → {target:+.2f}°  @ {rpm:.2f} RPM · 加速 {accel}", "en": "J{index} move → {target:+.2f}°  @ {rpm:.2f} RPM · accel {accel}", "ru": "J{index} движение → {target:+.2f}°  @ {rpm:.2f} RPM · ускор. {accel}"},
    "log.move_all": {"zh": "六轴同步  [{values}]°  @ {rpm:.2f} RPM", "en": "move-all  [{values}]°  @ {rpm:.2f} RPM", "ru": "синхронно  [{values}]°  @ {rpm:.2f} RPM"},
    "log.stop": {"zh": "已停止 — 取消全部运动，保持当前位置", "en": "STOP — all motion cancelled; holding position", "ru": "СТОП — движение отменено, удержание позиции"},
    "log.cleared": {"zh": "J{index} 保护已清除", "en": "J{index} protection cleared", "ru": "J{index} защита снята"},
    "log.zero": {"zh": "J{index} 当前姿态定义为 0.000°（软件零点）", "en": "J{index} current pose defined as 0.000° (software zero)", "ru": "J{index} текущее положение принято за 0.000° (программный ноль)"},
    "log.limit": {"zh": "J{index} 目标 {value:+.2f}° 超出软限位 [{lo:+.1f}, {hi:+.1f}]°", "en": "J{index} target {value:+.2f}° outside soft limits [{lo:+.1f}, {hi:+.1f}]°", "ru": "J{index} цель {value:+.2f}° вне пределов [{lo:+.1f}, {hi:+.1f}]°"},
    "log.needs_enable": {"zh": "J{index} 未使能；请先使能", "en": "J{index} is disabled; enable it first", "ru": "J{index} отключена; сначала включите"},
    "dlg.yes": {"zh": "确定", "en": "Yes", "ru": "Да"},
    "dlg.no": {"zh": "取消", "en": "Cancel", "ru": "Отмена"},
}

LANG = "zh"


def set_language(code: str) -> None:
    global LANG
    LANG = code if code in ("zh", "en", "ru") else "en"


def tr(key: str, **kwargs) -> str:
    entry = _STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(LANG) or entry.get("en") or next(iter(entry.values()))
    try:
        return text.format(**kwargs)
    except Exception:
        return text
