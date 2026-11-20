"""Reusable widgets for the control station."""
from __future__ import annotations

import html
import math
import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .models import JointState, Snapshot, STATUS_HOLD, STATUS_MOVING, STATUS_PROTECTED, STATUS_READY
from .theme import C

STATUS_KEYS = {
    STATUS_READY: "status.ready",
    STATUS_MOVING: "status.moving",
    STATUS_HOLD: "status.hold",
    STATUS_PROTECTED: "status.protected",
}


class StatusPill(QLabel):
    def __init__(self, status: str = STATUS_HOLD, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        self.setText(tr(STATUS_KEYS.get(status, "status.hold")))
        if status == STATUS_MOVING:
            self.setObjectName("StatusMove")
        elif status == STATUS_PROTECTED:
            self.setObjectName("StatusError")
        elif status == STATUS_READY:
            self.setObjectName("StatusReady")
        else:
            self.setObjectName("StatusWarn")
        self.style().unpolish(self)
        self.style().polish(self)


class LimitBar(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(6)
        self._lo = -180.0
        self._hi = 180.0
        self._value = 0.0

    def set_range(self, lo: float, hi: float, value: float) -> None:
        self._lo, self._hi, self._value = lo, hi, value
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 2, self.width(), 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C["line"]))
        p.drawRoundedRect(r, 1.5, 1.5)
        span = max(1.0, self._hi - self._lo)
        t = min(1.0, max(0.0, (self._value - self._lo) / span))
        fill = QRectF(0, 2, self.width() * t, 3)
        p.setBrush(QColor(C["green"]))
        p.drawRoundedRect(fill, 1.5, 1.5)
        x = max(2.0, min(self.width() - 2.0, self.width() * t))
        p.setBrush(QColor(C["text"]))
        p.drawEllipse(QPointF(x, 3.5), 3.2, 3.2)


class JointCard(QFrame):
    clicked = Signal(int)
    powerToggled = Signal(int, bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(142)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._index = 0
        self._enabled = False

        root = QVBoxLayout(self)
        root.setContentsMargins(15, 12, 15, 12)
        root.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.badge = QLabel("J1")
        self.badge.setFixedSize(28, 22)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(
            f"background:{C['blue_dim']};color:{C['blue']};border:1px solid #1D4C78;"
            "border-radius:6px;font-size:10px;font-weight:800;"
        )
        self.name = QLabel("Base")
        self.name.setObjectName("JointName")
        self.status = StatusPill(STATUS_HOLD)
        self.power = QLabel("OFF")
        self.power.setFixedSize(34, 20)
        self.power.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power.setStyleSheet(
            f"color:{C['dim']};border:1px solid {C['line']};border-radius:6px;"
            "font-size:9px;font-weight:700;"
        )
        head.addWidget(self.badge)
        head.addWidget(self.name)
        head.addStretch(1)
        head.addWidget(self.status)
        head.addSpacing(4)
        head.addWidget(self.power)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(6)
        self.angle = QLabel("0.00")
        self.angle.setObjectName("Angle")
        self.unit = QLabel(tr("deg"))
        self.unit.setObjectName("AngleUnit")
        self.unit.setAlignment(Qt.AlignmentFlag.AlignBottom)
        body.addWidget(self.angle)
        body.addWidget(self.unit)
        body.addStretch(1)
        self.target = QLabel("target  0.00°")
        self.target.setObjectName("Dim")
        self.target.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        body.addWidget(self.target)
        root.addLayout(body)

        self.bar = LimitBar()
        root.addWidget(self.bar)

        foot = QHBoxLayout()
        self.limits = QLabel("limits  —")
        self.limits.setObjectName("JointSub")
        self.can = QLabel("CAN 1 · 25:1")
        self.can.setObjectName("JointSub")
        self.can.setAlignment(Qt.AlignmentFlag.AlignRight)
        foot.addWidget(self.limits)
        foot.addStretch(1)
        foot.addWidget(self.can)
        root.addLayout(foot)

    def set_state(self, state: JointState, selected: bool = False) -> None:
        self._index = state.index
        self.badge.setText(f"J{state.index}")
        self.name.setText(tr(f"joint.{state.index}"))
        self.angle.setText(f"{state.angle:+.2f}")
        self.target.setText(f"{tr('target')}  {state.target:+.2f}°")
        self.status.set_status(state.status)
        self.limits.setText(f"{tr('limits')}  {state.min_deg:+.1f} … {state.max_deg:+.1f}°")
        self.can.setText(f"CAN {state.can_id} · {state.gear_ratio:g}:1")
        self.bar.set_range(state.min_deg, state.max_deg, state.angle)
        self._enabled = state.enabled
        self.power.setText(tr("on") if state.enabled else tr("off"))
        self.power.setStyleSheet(
            f"color:{C['green'] if state.enabled else C['dim']};"
            f"border:1px solid {C['green_dim'] if state.enabled else C['line']};"
            "border-radius:6px;font-size:9px;font-weight:700;"
        )
        if self.property("selected") != selected:
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.powerToggled.emit(self._index, not self._enabled)
        super().mouseDoubleClickEvent(event)


class MetricCard(QFrame):
    def __init__(self, label: str, value: str, unit: str, accent: str, note: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Metric")
        self.setMinimumHeight(74)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(13, 9, 13, 9)
        lay.setSpacing(1)
        top = QHBoxLayout()
        lab = QLabel(label.upper())
        lab.setObjectName("MetricLabel")
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{accent};font-size:8px;")
        top.addWidget(lab)
        top.addStretch(1)
        top.addWidget(dot)
        lay.addLayout(top)
        row = QHBoxLayout()
        row.setSpacing(5)
        self.value = QLabel(value)
        self.value.setObjectName("MetricValue")
        self.unit = QLabel(unit)
        self.unit.setObjectName("MetricUnit")
        self.unit.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self.value)
        row.addWidget(self.unit)
        row.addStretch(1)
        lay.addLayout(row)
        self.note = QLabel(note)
        self.note.setObjectName("Dim")
        self.note.setStyleSheet("font-size:9px;")
        lay.addWidget(self.note)

    def set_value(self, value: str, note: Optional[str] = None) -> None:
        self.value.setText(value)
        if note is not None:
            self.note.setText(note)


class ArmCanvas(QWidget):
    """Live schematic side view driven by the six software joint angles.

    Zero pose matches the CAD pose: vertical upper arm, horizontal forearm.
    It is a schematic, not a calibrated FK projection.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(170)
        self._angles = [0.0] * 6
        self._moving = False

    def set_snapshot(self, snap: Snapshot) -> None:
        self._angles = [j.angle for j in snap.joints]
        self._moving = any(j.status == STATUS_MOVING for j in snap.joints)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(C["panel_2"]))
        p.setPen(QPen(QColor("#182633"), 1))
        for x in range(20, w, 24):
            for y in range(18, h, 24):
                p.drawPoint(x, y)
        p.setPen(QPen(QColor("#243646"), 1))
        p.drawLine(24, h - 18, w - 24, h - 18)

        cx = w * 0.38
        base_y = h - 24
        base_h = min(30.0, h * 0.19)
        shoulder = QPointF(cx, base_y - base_h)
        upper_len = min(54.0, h * 0.36)
        short_len = 16.0
        forearm_len = min(112.0, w * 0.20)
        wrist_len = 26.0

        a1 = math.radians(self._angles[0])
        a2 = math.radians(-self._angles[1])
        a3 = math.radians(-self._angles[2])
        a4 = math.radians(-self._angles[3])
        proj = math.cos(a1)
        th_upper = a2
        th_short = th_upper + a3
        th_forearm = th_short + a4 + math.pi / 2.0

        def step(pt: QPointF, ang: float, length: float) -> QPointF:
            return QPointF(pt.x() + math.sin(ang) * length * proj,
                           pt.y() - math.cos(ang) * length)

        elbow = step(shoulder, th_upper, upper_len)
        j4 = step(elbow, th_short, short_len)
        wrist = step(j4, th_forearm, forearm_len)
        tcp = step(wrist, th_forearm, wrist_len)

        # base
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#172531"))
        p.drawRoundedRect(QRectF(cx - 44, base_y - base_h, 88, base_h), 6, 6)
        p.setBrush(QColor("#0C141B"))
        p.drawRoundedRect(QRectF(cx - 51, base_y - 7, 102, 11), 3, 3)
        p.setBrush(QColor("#1E3444"))
        p.drawRoundedRect(QRectF(cx - 38, base_y - base_h + 3, 76, 8), 3, 3)

        def link(a: QPointF, b: QPointF, outer: float, inner: float, col_out: str, col_in: str) -> None:
            p.setPen(QPen(QColor(col_out), outer, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(a, b)
            p.setPen(QPen(QColor(col_in), inner, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(a, b)

        link(shoulder, elbow, 24, 14, "#233B4D", "#4F8090")
        link(elbow, j4, 18, 10, "#28495B", "#5D96A2")
        link(j4, wrist, 22, 12, "#28495B", "#5D96A2")
        link(wrist, tcp, 16, 8, "#2F5C6A", "#76B6B4")

        joints = [
            (QPointF(cx, base_y - 4), "J1", "left"),
            (shoulder, "J2", "left"),
            (elbow, "J3", "left"),
            (j4, "J4", "below"),
            (wrist, "J5/J6", "above"),
        ]
        for pt, label, side in joints:
            p.setBrush(QColor(C["panel_2"]))
            p.setPen(QPen(QColor(C["blue"]), 2))
            p.drawEllipse(pt, 5, 5)
            p.setPen(QPen(QColor(C["muted"]), 1))
            if side == "left":
                p.drawText(QPointF(pt.x() - 28, pt.y() + 4), label)
            elif side == "below":
                p.drawText(QPointF(pt.x() - 8, pt.y() - 8), label)
            else:
                p.drawText(QPointF(pt.x() - 16, pt.y() - 10), label)

        p.setPen(QPen(QColor(C["green"]), 1, Qt.PenStyle.DashLine))
        p.drawLine(tcp.x() - 6, tcp.y(), tcp.x() + 6, tcp.y())
        p.drawLine(tcp.x(), tcp.y() - 6, tcp.x(), tcp.y() + 6)
        p.setPen(QPen(QColor(C["green"]), 1))
        p.drawText(QPointF(tcp.x() + 8, tcp.y() + 4), "TCP")

        p.setPen(QPen(QColor(C["muted"]), 1))
        p.drawText(24, 24, tr("bottom.illustrative"))
        p.drawText(QRectF(w - 250, 16, 230, 20), Qt.AlignmentFlag.AlignRight,
                   f"J2 {self._angles[1]:+.1f}°  J3 {self._angles[2]:+.1f}°")
        if self._moving:
            p.setPen(QPen(QColor(C["green"]), 2))
            p.drawEllipse(shoulder, 10, 10)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()


class LogView(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 9)
        lay.setSpacing(5)
        head = QHBoxLayout()
        title = QLabel(tr("nav.log").upper())
        title.setObjectName("SectionTitle")
        live = QLabel(tr("log.live"))
        live.setStyleSheet(f"color:{C['green']};font-size:9px;font-weight:700;letter-spacing:1px;")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(live)
        lay.addLayout(head)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(400)
        self.text.setFrameShape(QFrame.Shape.NoFrame)
        self.text.setStyleSheet("background:transparent;border:none;")
        lay.addWidget(self.text)

    def append(self, level: str, message: str) -> None:
        color = {
            "ok": C["green"],
            "warn": C["amber"],
            "error": C["red"],
            "cmd": C["blue"],
            "info": C["muted"],
        }.get(level, C["muted"])
        tag = {"ok": "OK  ", "warn": "WARN", "error": "ERR ", "cmd": "CMD ", "info": "INFO"}.get(level, "INFO")
        self.text.appendHtml(
            f'<span style="color:{C["dim"]}">{tag}</span> '
            f'<span style="color:{color}">{html.escape(message)}</span>'
        )
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())
