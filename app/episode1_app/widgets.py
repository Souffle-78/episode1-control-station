"""Reusable widgets for the control station."""
from __future__ import annotations

import html
import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .models import JointState, Snapshot, STATUS_HOLD, STATUS_MOVING, STATUS_OFFLINE, STATUS_PROTECTED, STATUS_READY
from .theme import C

STATUS_KEYS = {
    STATUS_READY: "status.ready",
    STATUS_MOVING: "status.moving",
    STATUS_HOLD: "status.hold",
    STATUS_PROTECTED: "status.protected",
    STATUS_OFFLINE: "status.offline",
}


class PortComboBox(QComboBox):
    """Editable port picker that refreshes its list when the popup opens."""

    refreshRequested = Signal()

    def showPopup(self) -> None:  # noqa: N802
        self.refreshRequested.emit()
        super().showPopup()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(C["muted"]), 1.5))
        x = self.width() - 13
        y = self.height() / 2 - 2
        p.drawPolyline([QPointF(x, y), QPointF(x + 4, y + 4), QPointF(x + 8, y)])
        p.end()


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
        elif status == STATUS_OFFLINE:
            self.setObjectName("StatusOffline")
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

    def __init__(self, index: int = 1, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(126)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._index = index
        self._enabled = False

        root = QVBoxLayout(self)
        self._root = root
        root.setContentsMargins(15, 12, 15, 12)
        root.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.badge = QLabel(f"J{index}")
        self.badge.setFixedSize(28, 22)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(
            f"background:{C['blue_dim']};color:{C['blue']};border:1px solid {C['blue_border']};"
            "border-radius:6px;font-size:10px;font-weight:800;"
        )
        self.name = QLabel(tr(f"joint.{index}"))
        self.name.setObjectName("JointName")
        self.status = StatusPill(STATUS_OFFLINE)
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
        self.can = QLabel(f"CAN {index}")
        self.can.setObjectName("JointSub")
        self.can.setAlignment(Qt.AlignmentFlag.AlignRight)
        foot.addWidget(self.limits)
        foot.addStretch(1)
        foot.addWidget(self.can)
        root.addLayout(foot)

    def set_offline(self) -> None:
        self.status.set_status(STATUS_OFFLINE)
        self.power.setText(tr("off"))
        self.angle.setText("—")
        self.target.setText(f"{tr('target')}  —")
        self.limits.setText(f"{tr('limits')}  —")
        self.can.setText(f"CAN {self._index}")
        self.bar.set_range(-180.0, 180.0, 0.0)
        self._enabled = False

    def set_compact(self, compact: bool) -> None:
        """Small-window mode: hide the footer and reduce the card height."""
        self.limits.setVisible(not compact)
        self.can.setVisible(not compact)
        self._root.setContentsMargins(12, 8, 12, 8) if compact else self._root.setContentsMargins(15, 12, 15, 12)
        self._root.setSpacing(3 if compact else 6)
        if compact:
            self.setFixedHeight(96)
        else:
            self.setMinimumHeight(126)
            self.setMaximumHeight(16777215)

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
        self.setMinimumHeight(150)
        self._angles = [0.0] * 6
        self._moving = False

    def set_zero(self) -> None:
        self._angles = [0.0] * 6
        self._moving = False
        self.update()

    def set_snapshot(self, snap: Snapshot) -> None:
        self._angles = [j.angle for j in snap.joints]
        self._moving = any(j.status == STATUS_MOVING for j in snap.joints)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(C["panel_2"]))
        p.setPen(QPen(QColor(C["line_soft"]), 1))
        for x in range(20, w, 24):
            for y in range(18, h, 24):
                p.drawPoint(x, y)
        p.setPen(QPen(QColor(C["line"]), 1))
        p.drawLine(24, h - 18, w - 24, h - 18)

        base_h = 34.0
        upper_len = 54.0
        short_len = 16.0
        forearm_len = 112.0
        wrist_len = 26.0

        a1 = math.radians(self._angles[0])
        a2 = math.radians(-self._angles[1])
        a3 = math.radians(-self._angles[2])
        a4 = math.radians(-self._angles[3])
        proj = math.cos(a1)
        th_upper = a2
        th_short = th_upper + a3
        th_forearm = th_short + a4 + math.pi / 2.0

        def step(pt: tuple[float, float], ang: float, length: float) -> tuple[float, float]:
            return (pt[0] + math.sin(ang) * length * proj,
                    pt[1] - math.cos(ang) * length)

        shoulder = (0.0, -base_h)
        elbow = step(shoulder, th_upper, upper_len)
        j4 = step(elbow, th_short, short_len)
        wrist = step(j4, th_forearm, forearm_len)
        tcp = step(wrist, th_forearm, wrist_len)

        # Fit the whole arm, including the base, into the widget.  This keeps
        # the drawing inside the panel at every joint angle instead of using
        # fixed pixel lengths that clip when the arm swings out.
        xs = [shoulder[0], elbow[0], j4[0], wrist[0], tcp[0], -51.0, 51.0]
        ys = [shoulder[1], elbow[1], j4[1], wrist[1], tcp[1], -base_h, 7.0]
        pad_x = 12.0
        pad_top = 30.0
        pad_bottom = 20.0
        bw = max(1.0, max(xs) - min(xs))
        bh = max(1.0, max(ys) - min(ys))
        scale = min((w - 2 * pad_x) / bw, (h - pad_top - pad_bottom) / bh, 1.0)
        scale = max(0.28, scale)
        tx = w / 2.0 - (min(xs) + max(xs)) / 2.0 * scale
        ty = h - pad_bottom - max(ys) * scale

        def T(pt: tuple[float, float]) -> QPointF:
            return QPointF(tx + pt[0] * scale, ty + pt[1] * scale)

        # base
        p.setPen(QPen(QColor(C["line"]), 1))
        p.setBrush(QColor(C["panel"]))
        base_rect = QRectF(T((-44.0, -base_h)), T((44.0, 0.0)))
        p.drawRoundedRect(base_rect, 6, 6)
        p.setBrush(QColor(C["line"]))
        p.drawRoundedRect(QRectF(T((-51.0, -7.0)), T((51.0, 4.0))), 3, 3)
        p.setBrush(QColor(C["line_soft"]))
        p.drawRoundedRect(QRectF(T((-38.0, -base_h + 3.0)), T((38.0, -base_h + 11.0))), 3, 3)

        def link(a: tuple[float, float], b: tuple[float, float], outer: float, inner: float) -> None:
            p.setPen(QPen(QColor(C["green_dim"]), max(7.0, outer * scale),
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(T(a), T(b))
            p.setPen(QPen(QColor(C["green"]), max(4.0, inner * scale),
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(T(a), T(b))

        link(shoulder, elbow, 24, 14)
        link(elbow, j4, 18, 10)
        link(j4, wrist, 22, 12)
        link(wrist, tcp, 16, 8)

        joints = [
            (T((0.0, -4.0)), "J1", "left"),
            (T(shoulder), "J2", "left"),
            (T(elbow), "J3", "left"),
            (T(j4), "J4", "below"),
            (T(wrist), "J5/J6", "above"),
        ]
        for pt, label, side in joints:
            p.setBrush(QColor(C["panel_2"]))
            p.setPen(QPen(QColor(C["blue"]), 2))
            p.drawEllipse(pt, 5, 5)
            p.setPen(QPen(QColor(C["muted"]), 1))
            if side == "left":
                p.drawText(QPointF(max(2.0, pt.x() - 30), pt.y() + 4), label)
            elif side == "below":
                p.drawText(QPointF(max(2.0, pt.x() - 8), max(14.0, pt.y() - 8)), label)
            else:
                p.drawText(QPointF(min(pt.x() - 16, w - 46), max(14.0, pt.y() - 10)), label)

        tcp_pt = T(tcp)
        p.setPen(QPen(QColor(C["green"]), 1, Qt.PenStyle.DashLine))
        p.drawLine(tcp_pt.x() - 6, tcp_pt.y(), tcp_pt.x() + 6, tcp_pt.y())
        p.drawLine(tcp_pt.x(), tcp_pt.y() - 6, tcp_pt.x(), tcp_pt.y() + 6)
        p.setPen(QPen(QColor(C["green"]), 1))
        p.drawText(QPointF(min(tcp_pt.x() + 8, w - 34), tcp_pt.y() + 4), "TCP")

        p.setPen(QPen(QColor(C["muted"]), 1))
        p.drawText(24, 24, tr("bottom.illustrative"))
        p.drawText(QRectF(w - 250, 16, 230, 20), Qt.AlignmentFlag.AlignRight,
                   f"J2 {self._angles[1]:+.1f}°  J3 {self._angles[2]:+.1f}°")
        if self._moving:
            p.setPen(QPen(QColor(C["green"]), 2))
            p.drawEllipse(T(shoulder), 10, 10)

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
