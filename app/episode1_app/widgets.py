"""Reusable widgets for the control station."""
from __future__ import annotations

import html
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
    """Stylised side view; not a metrology view (the kinematics module owns FK)."""

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
        # dot grid
        p.setPen(QPen(QColor("#182633"), 1))
        for x in range(20, w, 24):
            for y in range(18, h, 24):
                p.drawPoint(x, y)

        # ground
        p.setPen(QPen(QColor("#243646"), 1))
        p.drawLine(24, h - 22, w - 24, h - 22)

        cx = w * 0.30
        base_y = h - 30
        scale = min(1.0, max(0.42, (h - 56) / 300.0))
        base_h = 54 * scale
        l1, l2, l3 = 88 * scale, 96 * scale, 54 * scale
        # base
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#172531"))
        p.drawRoundedRect(QRectF(cx - 42 * scale, base_y - base_h, 84 * scale, base_h), 5, 5)
        p.setBrush(QColor("#0C141B"))
        p.drawRoundedRect(QRectF(cx - 48 * scale, base_y - 8, 96 * scale, 12), 3, 3)

        # planar arm using J2/J3; purely illustrative, scaled to the panel
        a2 = math.radians(80.0 - self._angles[1])
        a3 = math.radians(self._angles[2] * 0.8)
        shoulder = QPointF(cx, base_y - base_h)
        elbow = QPointF(
            shoulder.x() + l1 * math.sin(a2),
            shoulder.y() - l1 * math.cos(a2),
        )
        wrist = QPointF(
            elbow.x() + l2 * math.sin(a2 + a3),
            elbow.y() - l2 * math.cos(a2 + a3),
        )
        tcp = QPointF(
            wrist.x() + l3 * math.sin(a2 + a3),
            wrist.y() - l3 * math.cos(a2 + a3),
        )

        def link(a: QPointF, b: QPointF, width: float, color: str) -> None:
            pen = QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(a, b)

        link(shoulder, elbow, max(8, 16 * scale), "#233B4D")
        link(elbow, wrist, max(7, 13 * scale), "#28495B")
        link(wrist, tcp, max(4, 8 * scale), "#2F5C6A")
        # highlight
        link(shoulder, elbow, max(3, 5 * scale), "#4F8090")
        link(elbow, wrist, max(2, 4 * scale), "#5D96A2")
        link(wrist, tcp, max(2, 3 * scale), "#76B6B4")

        for pt, label, col in ((shoulder, "J2", C["blue"]), (elbow, "J3", C["blue"]), (wrist, "J4", C["blue"])):
            p.setBrush(QColor(C["panel_2"]))
            p.setPen(QPen(QColor(col), 2))
            p.drawEllipse(pt, 6, 6)
            p.setPen(QPen(QColor(C["muted"]), 1))
            p.drawText(QPointF(pt.x() + 9, pt.y() - 8), label)

        # TCP marker
        p.setPen(QPen(QColor(C["green"]), 1, Qt.PenStyle.DashLine))
        p.drawLine(tcp.x() - 7, tcp.y(), tcp.x() + 7, tcp.y())
        p.drawLine(tcp.x(), tcp.y() - 7, tcp.x(), tcp.y() + 7)
        p.setPen(QPen(QColor(C["green"]), 1))
        p.drawText(QPointF(tcp.x() + 10, tcp.y() + 4), "TCP")

        # labels
        p.setPen(QPen(QColor(C["dim"]), 1))
        p.drawText(24, 24, tr("bottom.illustrative"))
        p.setPen(QPen(QColor(C["muted"]), 1))
        p.drawText(QRectF(w - 210, 16, 190, 20), Qt.AlignmentFlag.AlignRight, tr("bottom.workspace"))
        if self._moving:
            p.setPen(QPen(QColor(C["green"]), 2))
            p.drawEllipse(shoulder, 12, 12)

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
