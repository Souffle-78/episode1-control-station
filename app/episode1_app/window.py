"""Main window for the Episode 1 control station.

The whole central widget is rebuilt when the language changes.  That keeps
the translation layer simple: every widget is constructed through ``tr()``
and no stale English text can survive a language switch.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .backend import BackendBase, DemoBackend, SlcanBackend
from .i18n import LANGUAGES, set_language, tr
from .models import Snapshot, STATUS_PROTECTED
from .theme import C
from .widgets import ArmCanvas, JointCard, LogView, MetricCard

NAV_ITEMS = (
    ("overview", "◈", "nav.overview"),
    ("joint", "◎", "nav.joint"),
    ("fk", "⌁", "nav.fk"),
    ("config", "⚙", "nav.config"),
    ("log", "≡", "nav.log"),
)


class MainWindow(QMainWindow):
    def __init__(self, backend: Optional[BackendBase] = None, demo: bool = True) -> None:
        super().__init__()
        self.backend = backend or DemoBackend(self)
        self.demo = demo
        self.settings = QSettings("TSU-Robotics", "Episode1-Station")
        lang = str(os.environ.get("EPISODE1_LANG") or self.settings.value("language", "zh"))
        if lang not in ("zh", "en", "ru"):
            lang = "zh"
        set_language(lang)
        self._lang_code = lang
        self.selected = 2
        self.cards: Dict[int, JointCard] = {}
        self.last_snapshot: Optional[Snapshot] = None
        self._nav_buttons: list[QPushButton] = []
        self._nav_keys: list[str] = []
        self.page_key = "overview"
        self._last_port = self.settings.value("last_port", "DEMO")

        self.setObjectName("Root")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 760)
        self._build_ui()

        self._attach_backend(self.backend)

    def _attach_backend(self, backend: BackendBase) -> None:
        """Connect signals for a backend and detach the previous one."""
        old = getattr(self, "backend", None)
        if old is not None and old is not backend:
            for sig, slot in (
                (old.snapshotChanged, self._on_snapshot),
                (old.log, self._on_log),
                (old.connectionChanged, self._on_connection),
            ):
                try:
                    sig.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
        self.backend = backend
        backend.snapshotChanged.connect(self._on_snapshot)
        backend.log.connect(self._on_log)
        backend.connectionChanged.connect(self._on_connection)
        self._on_connection(backend.connected)

    # ------------------------------------------------------------------ shell
    def _build_ui(self) -> None:
        old = self.takeCentralWidget()
        if old is not None:
            old.deleteLater()
        self.cards.clear()
        self._nav_buttons.clear()
        self._nav_keys.clear()

        self.setWindowTitle(tr("app.title"))
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(22, 16, 22, 18)
        content_lay.setSpacing(12)
        content_lay.addLayout(self._build_header())
        content_lay.addLayout(self._build_metrics())
        content_lay.addLayout(self._build_main_row(), 1)
        content_lay.addLayout(self._build_bottom_row())
        body.addWidget(content, 1)
        outer.addLayout(body, 1)

        self._on_connection(self.backend.connected)
        if self.last_snapshot is not None:
            self._on_snapshot(self.last_snapshot)
        self._append_welcome()

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(66)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(12)

        logo = QLabel("E1")
        logo.setObjectName("Logo")
        logo.setFixedSize(42, 42)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("EPISODE 1")
        t.setObjectName("AppTitle")
        s = QLabel(tr("app.sub"))
        s.setObjectName("AppSub")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        self.link_dot = QLabel("●")
        self.link_dot.setStyleSheet(f"color:{C['red']};font-size:13px;")
        lay.addWidget(self.link_dot)
        self.link_state = QLabel(tr("link.offline"))
        self.link_state.setStyleSheet(
            f"color:{C['red']};font-size:10px;font-weight:700;letter-spacing:1px;"
        )
        lay.addWidget(self.link_state)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(88)
        for code, label in LANGUAGES:
            self.lang_combo.addItem(label, code)
        idx = max(0, self.lang_combo.findData(self._lang_code))
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._language_changed)
        lay.addWidget(self.lang_combo)

        port_label = QLabel(tr("port"))
        port_label.setObjectName("SectionTitle")
        lay.addWidget(port_label)
        self.port = QComboBox()
        self.port.setEditable(True)
        ports = ["DEMO", "/dev/cu.usbmodem1101", "COM6"]
        if self._last_port and self._last_port not in ports:
            ports.insert(0, self._last_port)
        self.port.addItems(ports)
        if self._last_port:
            self.port.setCurrentText(self._last_port)
        self.port.setMinimumWidth(190)
        self.port.currentTextChanged.connect(self._remember_port)
        lay.addWidget(self.port)

        self.connect_btn = QPushButton(tr("connect"))
        self.connect_btn.setObjectName("Primary")
        self.connect_btn.setFixedWidth(104)
        self.connect_btn.clicked.connect(self._toggle_connection)
        lay.addWidget(self.connect_btn)

        self.stop_top = QPushButton(tr("stop_all"))
        self.stop_top.setObjectName("Danger")
        self.stop_top.setFixedWidth(130)
        self.stop_top.clicked.connect(self._stop_all)
        lay.addWidget(self.stop_top)
        return bar

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(184)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 18, 0, 14)
        lay.setSpacing(0)

        label = QLabel(tr("workspace"))
        label.setObjectName("SectionTitle")
        label.setContentsMargins(18, 0, 0, 8)
        lay.addWidget(label)

        for key, icon, label_key in NAV_ITEMS:
            b = QPushButton(f"{icon}   {tr(label_key)}")
            b.setObjectName("Nav")
            b.setProperty("active", key == self.page_key)
            b.setCheckable(False)
            b.clicked.connect(lambda _=False, k=key: self._nav_clicked(k))
            self._nav_buttons.append(b)
            self._nav_keys.append(key)
            lay.addWidget(b)

        lay.addStretch(1)

        foot = QFrame()
        foot.setObjectName("Panel")
        foot_lay = QVBoxLayout(foot)
        foot_lay.setContentsMargins(12, 10, 12, 10)
        foot_lay.setSpacing(3)
        a = QLabel(tr("bridge.title"))
        a.setObjectName("SectionTitle")
        b = QLabel(tr("bridge.protocol"))
        b.setObjectName("JointSub")
        c = QLabel(tr("bridge.adapter"))
        c.setObjectName("JointSub")
        foot_lay.addWidget(a)
        foot_lay.addWidget(b)
        foot_lay.addWidget(c)
        lay.addWidget(foot)
        lay.addSpacing(8)
        ver = QLabel(tr("app.version"))
        ver.setObjectName("Dim")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("font-size:9px;")
        lay.addWidget(ver)
        return side

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(1)
        self.page_title = QLabel(tr(f"page.{self.page_key}.title"))
        self.page_title.setObjectName("PageTitle")
        self.page_sub = QLabel(tr(f"page.{self.page_key}.sub"))
        self.page_sub.setObjectName("PageSub")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_sub)
        row.addLayout(titles)
        row.addStretch(1)

        self.axis_pill = QLabel(tr("axes.offline"))
        self.axis_pill.setStyleSheet(
            f"color:{C['red']};background:{C['red_dim']};border:1px solid #6B2430;"
            "border-radius:8px;padding:5px 10px;font-size:9px;font-weight:800;letter-spacing:0.8px;"
        )
        row.addWidget(self.axis_pill)
        return row

    def _build_metrics(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.m_voltage = MetricCard(tr("metric.voltage"), "—", "V", C["green"], tr("metric.voltage.note"))
        self.m_current = MetricCard(tr("metric.current"), "—", "A", C["blue"], tr("metric.current.note"))
        self.m_temp = MetricCard(tr("metric.temp"), "—", "°C", C["amber"], tr("metric.temp.note"))
        self.m_latency = MetricCard(tr("metric.loop"), "—", "ms", C["green"], tr("metric.loop.note"))
        for m in (self.m_voltage, self.m_current, self.m_temp, self.m_latency):
            row.addWidget(m, 1)
        return row

    def _build_main_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        grid_panel = QFrame()
        grid_panel.setObjectName("Panel")
        gl = QVBoxLayout(grid_panel)
        gl.setContentsMargins(14, 12, 14, 13)
        gl.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel(tr("joints.title"))
        title.setObjectName("SectionTitle")
        hint = QLabel(tr("joints.hint"))
        hint.setObjectName("Dim")
        hint.setStyleSheet("font-size:9px;")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(hint)
        gl.addLayout(head)

        grid = QGridLayout()
        grid.setSpacing(9)
        for i in range(6):
            card = JointCard()
            card.clicked.connect(self._select_joint)
            card.powerToggled.connect(self._toggle_joint_power)
            self.cards[i + 1] = card
            grid.addWidget(card, i // 2, i % 2)
        gl.addLayout(grid)
        row.addWidget(grid_panel, 1)

        row.addWidget(self._build_command_panel())
        return row

    def _build_command_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(352)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(15, 10, 15, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel(tr("manual.title"))
        title.setObjectName("SectionTitle")
        self.sel_pill = QLabel("J2")
        self.sel_pill.setStyleSheet(
            f"color:{C['blue']};background:{C['blue_dim']};border:1px solid #1D4C78;"
            "border-radius:6px;padding:3px 7px;font-size:9px;font-weight:800;"
        )
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.sel_pill)
        lay.addLayout(top)

        self.sel_name = QLabel(tr("joint.2"))
        self.sel_name.setStyleSheet("font-size:20px;font-weight:700;")
        self.sel_target_read = QLabel("—")
        self.sel_target_read.setObjectName("Muted")
        self.sel_target_read.setStyleSheet("font-size:10px;")
        lay.addWidget(self.sel_name)
        lay.addWidget(self.sel_target_read)
        lay.addSpacing(4)

        lay.addWidget(self._field_label(tr("field.target")))
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-180.0, 180.0)
        self.target_spin.setDecimals(2)
        self.target_spin.setSingleStep(0.5)
        self.target_spin.setSuffix(f" {tr('deg')}")
        self.target_spin.setValue(12.0)
        self.target_spin.setFixedHeight(30)
        lay.addWidget(self.target_spin)

        speed_row = QHBoxLayout()
        speed_row.setSpacing(8)
        speed_col = QVBoxLayout()
        speed_col.setSpacing(4)
        speed_col.addWidget(self._field_label(tr("field.speed")))
        self.rpm_spin = QDoubleSpinBox()
        self.rpm_spin.setRange(0.01, 6.0)
        self.rpm_spin.setDecimals(2)
        self.rpm_spin.setSingleStep(0.05)
        self.rpm_spin.setValue(0.20)
        self.rpm_spin.setMinimumWidth(108)
        self.rpm_spin.setFixedHeight(30)
        speed_col.addWidget(self.rpm_spin)
        speed_row.addLayout(speed_col, 1)
        acc_col = QVBoxLayout()
        acc_col.setSpacing(4)
        acc_col.addWidget(self._field_label(tr("field.accel")))
        self.accel_spin = QSpinBox()
        self.accel_spin.setRange(1, 100)
        self.accel_spin.setValue(1)
        self.accel_spin.setMinimumWidth(70)
        self.accel_spin.setFixedHeight(30)
        acc_col.addWidget(self.accel_spin)
        speed_row.addLayout(acc_col, 1)
        lay.addLayout(speed_row)

        lay.addWidget(self._field_label(tr("field.jog")))
        jog_row = QHBoxLayout()
        jog_row.setSpacing(5)
        for text, delta in (("−5°", -5.0), ("−1°", -1.0), ("+1°", 1.0), ("+5°", 5.0)):
            b = QPushButton(text)
            b.setMinimumHeight(30)
            b.clicked.connect(lambda _=False, d=delta: self._jog(d))
            jog_row.addWidget(b)
        lay.addLayout(jog_row)

        self.move_btn = QPushButton(tr("action.move"))
        self.move_btn.setObjectName("Primary")
        self.move_btn.setMinimumHeight(34)
        self.move_btn.clicked.connect(self._move_target)
        lay.addWidget(self.move_btn)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.zero_btn = QPushButton(tr("action.zero"))
        self.zero_btn.setObjectName("Ghost")
        self.zero_btn.setFixedHeight(30)
        self.zero_btn.clicked.connect(self._zero_selected)
        self.clear_btn = QPushButton(tr("action.clear"))
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.setFixedHeight(30)
        self.clear_btn.clicked.connect(self._clear_selected)
        row2.addWidget(self.zero_btn)
        row2.addWidget(self.clear_btn)
        lay.addLayout(row2)

        self.enable_btn = QPushButton(tr("action.disable"))
        self.enable_btn.setFixedHeight(30)
        self.enable_btn.clicked.connect(self._toggle_selected)
        lay.addWidget(self.enable_btn)

        lay.addStretch(1)
        note = QLabel(tr("note.safety"))
        note.setWordWrap(True)
        note.setObjectName("Dim")
        note.setStyleSheet("font-size:8.5px;line-height:1.35;")
        lay.addWidget(note)
        return panel

    def _field_label(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("SectionTitle")
        lab.setStyleSheet("font-size:9px;")
        return lab

    def _build_bottom_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        canvas_panel = QFrame()
        canvas_panel.setObjectName("Panel")
        cl = QVBoxLayout(canvas_panel)
        cl.setContentsMargins(10, 8, 10, 10)
        cl.setSpacing(5)
        head = QHBoxLayout()
        title = QLabel(tr("bottom.workspace"))
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch(1)
        proj = QLabel(tr("bottom.projection"))
        proj.setObjectName("Dim")
        head.addWidget(proj)
        cl.addLayout(head)
        self.canvas = ArmCanvas()
        cl.addWidget(self.canvas)
        row.addWidget(canvas_panel, 1)

        self.log = LogView()
        self.log.setFixedWidth(480)
        row.addWidget(self.log)
        return row

    # ------------------------------------------------------------- language
    def _current_lang(self) -> str:
        return self._lang_code

    def _remember_port(self, text: str) -> None:
        self._last_port = text.strip()
        self.settings.setValue("last_port", self._last_port)

    def _language_changed(self, _index: int) -> None:
        code = self.lang_combo.currentData()
        if not code or code == self._lang_code:
            return
        self._lang_code = str(code)
        set_language(self._lang_code)
        self.settings.setValue("language", self._lang_code)
        self._build_ui()

    def _nav_clicked(self, key: str) -> None:
        if key == "fk":
            try:
                from .kinematics_page import KinematicsDialog
                KinematicsDialog(self).exec()
            except Exception as exc:
                self._on_log("error", f"FK/IK: {exc}")
            return
        self.page_key = key
        for k, b in zip(self._nav_keys, self._nav_buttons):
            active = k == key
            b.setProperty("active", active)
            b.style().unpolish(b)
            b.style().polish(b)
        self.page_title.setText(tr(f"page.{key}.title"))
        self.page_sub.setText(tr(f"page.{key}.sub"))

    # ------------------------------------------------------------- actions
    def _toggle_connection(self) -> None:
        if self.backend.connected:
            self.backend.disconnect_device()
            self.connect_btn.setText(tr("connect"))
            return
        port = self.port.currentText().strip() or "DEMO"
        self._remember_port(port)
        target_cls = DemoBackend if port.upper() == "DEMO" else SlcanBackend
        if not isinstance(self.backend, target_cls):
            old = self.backend
            self.last_snapshot = None
            self._attach_backend(target_cls(self))
            old.deleteLater()
        try:
            self.connect_btn.setEnabled(False)
            self.backend.connect_device(port)
        except Exception as exc:  # noqa: BLE001
            self._on_log("error", tr("msg.connect_failed", error=exc))
        finally:
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText(
                tr("disconnect") if self.backend.connected else tr("connect")
            )

    def _on_connection(self, connected: bool) -> None:
        self.link_dot.setStyleSheet(
            f"color:{C['green'] if connected else C['red']};font-size:13px;"
        )
        self.link_state.setText(tr("link.online") if connected else tr("link.offline"))
        self.link_state.setStyleSheet(
            f"color:{C['green'] if connected else C['red']};"
            "font-size:10px;font-weight:700;letter-spacing:1px;"
        )
        self.axis_pill.setText(tr("axes.online") if connected else tr("axes.offline"))
        self.axis_pill.setStyleSheet(
            f"color:{C['green'] if connected else C['red']};"
            f"background:{C['green_dim'] if connected else C['red_dim']};"
            f"border:1px solid {'#1B5B42' if connected else '#6B2430'};"
            "border-radius:8px;padding:5px 10px;font-size:9px;font-weight:800;letter-spacing:0.8px;"
        )
        self.connect_btn.setText(tr("disconnect") if connected else tr("connect"))
        self._update_command_sensitivity(connected)
        if not connected:
            self.last_snapshot = None
            for card in self.cards.values():
                card.setEnabled(False)
                card.setProperty("selected", False)
                card.style().unpolish(card)
                card.style().polish(card)

    def _update_command_sensitivity(self, connected: bool) -> None:
        for w in (
            self.target_spin,
            self.rpm_spin,
            self.accel_spin,
            self.move_btn,
            self.zero_btn,
            self.clear_btn,
            self.enable_btn,
        ):
            w.setEnabled(connected)

    def _on_snapshot(self, snap: Snapshot) -> None:
        self.last_snapshot = snap
        for j in snap.joints:
            card = self.cards.get(j.index)
            if card is None:
                continue
            card.setEnabled(True)
            card.set_state(j, selected=j.index == self.selected)
        self.m_voltage.set_value(f"{snap.voltage:.2f}", tr("metric.voltage.note"))
        self.m_current.set_value(f"{snap.current_a:.2f}", tr("metric.current.note"))
        max_temp = max((j.temp_c for j in snap.joints), default=snap.temp_c)
        self.m_temp.set_value(f"{max_temp:.1f}", tr("metric.temp.note"))
        self.m_latency.set_value(f"{snap.latency_ms:.1f}", f"{snap.loop_hz:.0f} Hz")
        self.canvas.set_snapshot(snap)
        self._update_selected(snap)

    def _update_selected(self, snap: Snapshot) -> None:
        j = next((x for x in snap.joints if x.index == self.selected), None)
        if not j:
            return
        name = tr(f"joint.{j.index}")
        self.sel_name.setText(name)
        self.sel_pill.setText(f"J{j.index}  ·  {name.upper()}")
        self.sel_target_read.setText(
            f"{tr('manual.position')}  {j.angle:+.2f}°   ·   {tr('target')}  {j.target:+.2f}°"
        )
        if j.min_deg is not None and j.max_deg is not None:
            self.target_spin.setRange(j.min_deg, j.max_deg)
        if not self.target_spin.hasFocus():
            self.target_spin.setValue(j.target)
        self.enable_btn.setText(tr("action.disable") if j.enabled else tr("action.enable"))
        self.clear_btn.setEnabled(j.status == STATUS_PROTECTED)

    def _select_joint(self, index: int) -> None:
        self.selected = index
        if self.last_snapshot:
            self._on_snapshot(self.last_snapshot)
            j = next((x for x in self.last_snapshot.joints if x.index == index), None)
            if j:
                self.target_spin.setValue(j.target)
        self._on_log("info", tr("msg.selected", index=index))

    def _toggle_joint_power(self, index: int, _unused: bool) -> None:
        if not self.backend.connected or not self.last_snapshot:
            return
        j = next((x for x in self.last_snapshot.joints if x.index == index), None)
        if j:
            try:
                self.backend.set_enabled(index, not j.enabled)
            except Exception as exc:
                self._on_log("error", str(exc))

    def _toggle_selected(self) -> None:
        if not self.backend.connected or not self.last_snapshot:
            return
        j = next((x for x in self.last_snapshot.joints if x.index == self.selected), None)
        if j:
            try:
                self.backend.set_enabled(self.selected, not j.enabled)
            except Exception as exc:
                self._on_log("error", str(exc))

    def _jog(self, delta: float) -> None:
        if not self.backend.connected:
            self._on_log("warn", tr("msg.connect_first"))
            return
        try:
            self.backend.jog(self.selected, delta, self.rpm_spin.value())
        except Exception as exc:
            self._on_log("error", str(exc))

    def _move_target(self) -> None:
        if not self.backend.connected:
            self._on_log("warn", tr("msg.connect_first"))
            return
        try:
            self.backend.move(
                self.selected,
                self.target_spin.value(),
                self.rpm_spin.value(),
                self.accel_spin.value(),
            )
        except Exception as exc:
            self._on_log("error", str(exc))

    def _stop_all(self) -> None:
        if self.backend.connected:
            self.backend.stop_all()
        else:
            self._on_log("warn", tr("msg.offline_stop"))

    def _zero_selected(self) -> None:
        if not self.backend.connected:
            self._on_log("warn", tr("msg.connect_first"))
            return
        result = QMessageBox.question(
            self,
            tr("msg.zero_confirm.title"),
            tr("msg.zero_confirm.body", index=self.selected),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            try:
                self.backend.zero(self.selected)
            except Exception as exc:
                self._on_log("error", str(exc))

    def _clear_selected(self) -> None:
        if self.backend.connected:
            try:
                self.backend.clear_protection(self.selected)
            except Exception as exc:
                self._on_log("error", str(exc))

    def _on_log(self, level: str, message: str) -> None:
        if hasattr(self, "log"):
            self.log.append(level, message)

    def _append_welcome(self) -> None:
        self._on_log("info", tr("msg.ready"))
        self._on_log("info", tr("msg.backend"))
        self._on_log("ok", tr("msg.safety"))
