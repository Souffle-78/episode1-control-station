"""Functional dialogs for the sidebar sections."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .i18n import tr
from .models import Snapshot
from .theme import C
from .widgets import JointCard


def _style(dialog: QDialog) -> None:
    dialog.setObjectName("Root")
    app = QApplication.instance()
    if app is not None:
        dialog.setStyleSheet(app.styleSheet())


class JointControlDialog(QDialog):
    """Large six-joint control surface; all commands go through the backend."""

    def __init__(self, backend, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self.selected = 1
        self.snap: Optional[Snapshot] = None
        self.cards: dict[int, JointCard] = {}
        _style(self)
        self.setWindowTitle(tr("nav.joint"))
        self.resize(1120, 650)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        head = QHBoxLayout()
        title = QLabel(tr("page.joint.title"))
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.state_label = QLabel(tr("link.offline"))
        self.state_label.setObjectName("Dim")
        head.addWidget(self.state_label)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(12)
        grid = QGridLayout()
        grid.setSpacing(10)
        for i in range(6):
            card = JointCard(i + 1)
            card.clicked.connect(self._select)
            card.powerToggled.connect(self._toggle)
            self.cards[i + 1] = card
            grid.addWidget(card, (i // 2), i % 2)
        body.addLayout(grid, 1)

        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(340)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        self.sel_label = QLabel(tr("joint.1"))
        self.sel_label.setObjectName("SectionTitle")
        lay.addWidget(self.sel_label)

        lay.addWidget(QLabel(tr("target")))
        self.target = QDoubleSpinBox()
        self.target.setRange(-10000, 10000)
        self.target.setMinimumHeight(34)
        self.target.setMaximumWidth(300)
        self.target.setStyleSheet("QDoubleSpinBox { padding-left: 14px; }")
        if self.target.lineEdit() is not None:
            self.target.lineEdit().setTextMargins(5, 0, 2, 0)
        self.target.setDecimals(2)
        self.target.setSuffix(" °")
        self.target.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        lay.addWidget(self.target)

        params = QGridLayout()
        params.setHorizontalSpacing(8)
        params.addWidget(QLabel(tr("field.speed")), 0, 0)
        params.addWidget(QLabel(tr("field.accel")), 0, 1)
        self.rpm = QDoubleSpinBox()
        self.rpm.setRange(0.01, 30.0)
        self.rpm.setSingleStep(0.05)
        self.rpm.setValue(0.20)
        self.rpm.setDecimals(2)
        self.rpm.setMaximumWidth(145)
        self.rpm.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        if self.rpm.lineEdit() is not None:
            self.rpm.lineEdit().setTextMargins(4, 0, 2, 0)
        params.addWidget(self.rpm, 1, 0)
        self.accel = QDoubleSpinBox()
        self.accel.setRange(1, 200)
        self.accel.setValue(1)
        self.accel.setDecimals(0)
        self.accel.setMaximumWidth(145)
        self.accel.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        params.addWidget(self.accel, 1, 1)
        lay.addLayout(params)

        jrow = QGridLayout()
        for n, d in enumerate((-5, -1, 1, 5)):
            b = QPushButton(f"{d:+d}°")
            b.clicked.connect(lambda _=False, delta=d: self._jog(delta))
            jrow.addWidget(b, 0, n)
        lay.addLayout(jrow)

        move = QPushButton(tr("action.move"))
        move.setObjectName("Primary")
        move.clicked.connect(self._move)
        lay.addWidget(move)
        sync = QPushButton(tr("action.sync"))
        sync.clicked.connect(self._open_sync)
        lay.addWidget(sync)
        limits = QPushButton(tr("action.limits"))
        limits.clicked.connect(self._open_limits)
        lay.addWidget(limits)
        self.enable_btn = QPushButton(tr("action.disable"))
        self.enable_btn.clicked.connect(self._toggle_selected)
        lay.addWidget(self.enable_btn)
        zrow = QHBoxLayout()
        z = QPushButton(tr("action.zero"))
        z.clicked.connect(self._zero)
        c = QPushButton(tr("action.clear"))
        c.clicked.connect(self._clear)
        zrow.addWidget(z)
        zrow.addWidget(c)
        lay.addLayout(zrow)
        stop = QPushButton(tr("stop_all"))
        stop.setObjectName("Danger")
        stop.clicked.connect(self._stop)
        lay.addWidget(stop)
        body.addWidget(panel)
        root.addLayout(body, 1)

        close = QPushButton(tr("dialog.close"))
        close.clicked.connect(self.accept)
        root.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

        self.backend.snapshotChanged.connect(self._on_snapshot)
        self._on_snapshot(self.backend.snapshot())
        self._select(1)

    def _open_sync(self) -> None:
        SyncDialog(self.backend, self).exec()

    def _open_limits(self) -> None:
        LimitDialog(self.backend, self.selected, self).exec()

    def _on_snapshot(self, snap: Snapshot) -> None:
        self.snap = snap
        if not snap.connected:
            self.state_label.setText(tr("link.offline"))
        else:
            self.state_label.setText(f"{snap.port}  ·  {snap.voltage:.2f} V")
        for i, card in self.cards.items():
            state = next((j for j in snap.joints if j.index == i), None)
            if state:
                card.set_state(state, i == self.selected)
        for w in (self.target, self.rpm, self.accel):
            w.setEnabled(snap.connected and bool(snap.joints))
        self._update_selected()

    def _select(self, index: int) -> None:
        self.selected = int(index)
        self._update_selected()
        if self.snap:
            self._on_snapshot(self.snap)

    def _update_selected(self) -> None:
        if not self.snap:
            return
        state = next((j for j in self.snap.joints if j.index == self.selected), None)
        if not state:
            return
        self.sel_label.setText(f"J{state.index}  {tr(f'joint.{state.index}')}")
        self.target.setRange(state.min_deg, state.max_deg)
        min_rpm = max(0.01, 1.0 / state.gear_ratio) if state.gear_ratio else 0.01
        self.rpm.setMinimum(min_rpm)
        if self.rpm.value() < min_rpm:
            self.rpm.setValue(min_rpm)
        if not self.target.hasFocus():
            self.target.setValue(state.target)
        self.enable_btn.setText(tr("action.disable") if state.enabled else tr("action.enable"))

    def _cmd(self, fn) -> None:
        if not self.backend.connected:
            self.state_label.setText(tr("msg.connect_first"))
            return
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.state_label.setText(str(exc))

    def _move(self) -> None:
        self._cmd(lambda: self.backend.move(
            self.selected, self.target.value(), self.rpm.value(), int(self.accel.value())))

    def _jog(self, delta: float) -> None:
        self._cmd(lambda: self.backend.jog(self.selected, delta, self.rpm.value()))

    def _toggle_selected(self) -> None:
        if not self.snap:
            return
        state = next((j for j in self.snap.joints if j.index == self.selected), None)
        if state:
            self._cmd(lambda: self.backend.set_enabled(self.selected, not state.enabled))

    def _toggle(self, index: int, enabled: bool) -> None:
        self._cmd(lambda: self.backend.set_enabled(index, enabled))

    def _zero(self) -> None:
        if not self.backend.connected:
            self.state_label.setText(tr("msg.connect_first"))
            return
        if QMessageBox.question(self, tr("action.zero"), tr("msg.zero_confirm.body", index=self.selected)) == QMessageBox.StandardButton.Yes:
            self._cmd(lambda: self.backend.zero(self.selected))

    def _clear(self) -> None:
        self._cmd(lambda: self.backend.clear_protection(self.selected))

    def _stop(self) -> None:
        self._cmd(lambda: self.backend.stop_all())


class LimitDialog(QDialog):
    """Manual mechanical-limit calibration.

    The user jogs with the normal low-speed buttons; this dialog deliberately
    bypasses software-limit checks so a newly shifted zero can be re-measured.
    """

    def __init__(self, backend, index: int = 1, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self.index = int(index)
        self.snap: Optional[Snapshot] = backend.snapshot()
        _style(self)
        self.setWindowTitle(tr("limit.title"))
        self.resize(680, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        title = QLabel(tr("limit.title"))
        title.setObjectName("SectionTitle")
        root.addWidget(title)
        sub = QLabel(tr("limit.sub"))
        sub.setObjectName("Dim")
        sub.setWordWrap(True)
        root.addWidget(sub)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("limit.joint")))
        self.joint = QComboBox()
        for i in range(1, 7):
            self.joint.addItem(f"J{i}  {tr(f'joint.{i}')}", i)
        self.joint.setCurrentIndex(max(0, self.index - 1))
        self.joint.currentIndexChanged.connect(self._joint_changed)
        row.addWidget(self.joint, 1)
        row.addWidget(QLabel(tr("limit.current")))
        self.current = QLabel("—")
        self.current.setObjectName("SectionTitle")
        row.addWidget(self.current)
        root.addLayout(row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.addWidget(QLabel(tr("limit.min")), 0, 0)
        grid.addWidget(QLabel(tr("limit.max")), 0, 1)
        self.min_spin = QDoubleSpinBox()
        self.max_spin = QDoubleSpinBox()
        for w in (self.min_spin, self.max_spin):
            w.setRange(-10000.0, 10000.0)
            w.setDecimals(2)
            w.setSuffix(" °")
            w.setMinimumHeight(34)
            w.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        grid.addWidget(self.min_spin, 1, 0)
        grid.addWidget(self.max_spin, 1, 1)
        bmin = QPushButton(tr("limit.record_min"))
        bmax = QPushButton(tr("limit.record_max"))
        bmin.clicked.connect(lambda: self._record_min())
        bmax.clicked.connect(lambda: self._record_max())
        grid.addWidget(bmin, 2, 0)
        grid.addWidget(bmax, 2, 1)
        root.addLayout(grid)

        jogrow = QHBoxLayout()
        for d in (-5, -1, 1, 5):
            b = QPushButton(f"{d:+d}°")
            b.clicked.connect(lambda _=False, delta=d: self._jog(delta))
            jogrow.addWidget(b)
        jogrow.addWidget(QLabel("RPM"))
        self.rpm = QDoubleSpinBox()
        self.rpm.setRange(0.02, 1.0)
        self.rpm.setSingleStep(0.02)
        self.rpm.setValue(0.10)
        self.rpm.setDecimals(2)
        self.rpm.setMaximumWidth(100)
        self.rpm.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        jogrow.addWidget(self.rpm)
        root.addLayout(jogrow)

        note = QLabel(tr("limit.note"))
        note.setObjectName("Dim")
        note.setWordWrap(True)
        root.addWidget(note)

        actions = QHBoxLayout()
        save = QPushButton(tr("limit.save"))
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        clear = QPushButton(tr("limit.clear"))
        clear.clicked.connect(self._clear)
        stop = QPushButton(tr("stop_all"))
        stop.setObjectName("Danger")
        stop.clicked.connect(lambda: self.backend.stop_all())
        actions.addWidget(save, 1)
        actions.addWidget(clear)
        actions.addWidget(stop)
        close = QPushButton(tr("dialog.close"))
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        root.addLayout(actions)

        self.backend.snapshotChanged.connect(self._on_snapshot)
        self._on_snapshot(self.backend.snapshot())

    def _state(self):
        if not self.snap:
            return None
        return next((j for j in self.snap.joints if j.index == self.index), None)

    def _joint_changed(self, *_args) -> None:
        self.index = int(self.joint.currentData())
        self._on_snapshot(self.snap or self.backend.snapshot())

    def _on_snapshot(self, snap: Snapshot) -> None:
        self.snap = snap
        st = self._state()
        if not st:
            self.current.setText("—")
            return
        self.current.setText(f"{st.angle:+.2f}°")
        # Load configured limits only when the joint changes; do not overwrite
        # values the user is editing during jogging.
        if not getattr(self, "_loaded", None) == self.index:
            self._loaded = self.index
            self.min_spin.setValue(st.min_deg)
            self.max_spin.setValue(st.max_deg)

    def _record_min(self) -> None:
        st = self._state()
        if st:
            self.min_spin.setValue(st.angle)

    def _record_max(self) -> None:
        st = self._state()
        if st:
            self.max_spin.setValue(st.angle)

    def _jog(self, delta: float) -> None:
        if not self.backend.connected:
            QMessageBox.warning(self, tr("limit.title"), tr("msg.connect_first"))
            return
        try:
            st = self._state()
            if st is not None and not st.enabled:
                self.backend.set_enabled(self.index, True)
            self.backend.jog_raw(self.index, delta, self.rpm.value())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("limit.title"), str(exc))

    def _clear(self) -> None:
        try:
            self.backend.clear_protection(self.index)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("limit.title"), str(exc))

    def _save(self) -> None:
        lo, hi = self.min_spin.value(), self.max_spin.value()
        if lo >= hi:
            QMessageBox.warning(self, tr("limit.title"), tr("limit.err_order"))
            return
        try:
            self.backend.set_limits(self.index, lo, hi)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("limit.title"), str(exc))
            return
        QMessageBox.information(self, tr("limit.title"), tr("limit.saved", index=self.index, lo=lo, hi=hi))


class SyncDialog(QDialog):
    """Six-axis synchronized absolute targets."""

    def __init__(self, backend, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self.snap: Optional[Snapshot] = None
        _style(self)
        self.setWindowTitle(tr("sync.title"))
        self.resize(620, 440)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)
        title = QLabel(tr("sync.title"))
        title.setObjectName("SectionTitle")
        root.addWidget(title)
        sub = QLabel(tr("sync.sub"))
        sub.setObjectName("Dim")
        sub.setWordWrap(True)
        root.addWidget(sub)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        self.targets: list[QDoubleSpinBox] = []
        self.current: list[QLabel] = []
        for i in range(6):
            lab = QLabel(tr(f"joint.{i + 1}"))
            lab.setObjectName("Dim")
            cur = QLabel("—")
            cur.setObjectName("Dim")
            cur.setFixedWidth(72)
            spin = QDoubleSpinBox()
            spin.setRange(-10000, 10000)
            spin.setDecimals(2)
            spin.setSingleStep(1.0)
            spin.setSuffix(" °")
            spin.setMinimumHeight(30)
            spin.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            grid.addWidget(lab, i, 0)
            grid.addWidget(cur, i, 1)
            grid.addWidget(spin, i, 2)
            self.targets.append(spin)
            self.current.append(cur)
        grid.setColumnStretch(2, 1)
        root.addLayout(grid)
        root.addStretch(1)

        params = QHBoxLayout()
        params.addWidget(QLabel(tr("field.speed")))
        self.rpm = QDoubleSpinBox()
        self.rpm.setRange(0.01, 30.0)
        self.rpm.setValue(0.20)
        self.rpm.setDecimals(2)
        self.rpm.setMaximumWidth(120)
        params.addWidget(self.rpm)
        params.addWidget(QLabel(tr("field.accel")))
        self.accel = QDoubleSpinBox()
        self.accel.setRange(1, 200)
        self.accel.setValue(1)
        self.accel.setDecimals(0)
        self.accel.setMaximumWidth(100)
        params.addWidget(self.accel)
        params.addStretch(1)
        root.addLayout(params)

        row = QHBoxLayout()
        self.move_btn = QPushButton(tr("sync.move"))
        self.move_btn.setObjectName("Primary")
        self.move_btn.clicked.connect(self._move_all)
        self.stop_btn = QPushButton(tr("stop_all"))
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.clicked.connect(self._stop)
        close = QPushButton(tr("dialog.close"))
        close.clicked.connect(self.accept)
        row.addWidget(self.move_btn, 1)
        row.addWidget(self.stop_btn)
        row.addWidget(close)
        root.addLayout(row)

        self.backend.snapshotChanged.connect(self._on_snapshot)
        self._on_snapshot(self.backend.snapshot())

    def _on_snapshot(self, snap: Snapshot) -> None:
        self.snap = snap
        first = not getattr(self, "_initialized", False)
        for i, (spin, cur) in enumerate(zip(self.targets, self.current)):
            state = next((j for j in snap.joints if j.index == i + 1), None)
            if state:
                if first:
                    spin.setValue(state.angle)
                cur.setText(f"{state.angle:+.2f}°")
            else:
                cur.setText("—")
            spin.setEnabled(snap.connected and bool(snap.joints))
        if first and snap.connected and snap.joints:
            self._initialized = True
        self.move_btn.setEnabled(snap.connected and bool(snap.joints))
        self.rpm.setEnabled(snap.connected)
        self.accel.setEnabled(snap.connected)

    def _move_all(self) -> None:
        if not self.backend.connected:
            return
        try:
            self.backend.move_all([s.value() for s in self.targets], self.rpm.value(), int(self.accel.value()))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("sync.title"), str(exc))

    def _stop(self) -> None:
        try:
            self.backend.stop_all()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("sync.title"), str(exc))

class ConfigDialog(QDialog):
    def __init__(self, backend, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.backend = backend
        _style(self)
        self.setWindowTitle(tr("nav.config"))
        self.resize(860, 430)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        title = QLabel(tr("page.config.title"))
        title.setObjectName("SectionTitle")
        lay.addWidget(title)
        self.info = QLabel()
        self.info.setObjectName("Dim")
        lay.addWidget(self.info)
        self.table = QTableWidget(6, 7)
        self.table.setHorizontalHeaderLabels([
            tr("joint"), "CAN", tr("gear"), tr("minimum"), tr("maximum"),
            tr("position"), tr("status"),
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table, 1)
        note = QLabel(tr("config.note"))
        note.setObjectName("Dim")
        note.setWordWrap(True)
        lay.addWidget(note)
        close = QPushButton(tr("dialog.close"))
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        self.backend.snapshotChanged.connect(self._refresh)
        self._refresh(self.backend.snapshot())

    def _refresh(self, snap: Snapshot) -> None:
        self.info.setText(
            f"{tr('port')}: {snap.port}    {snap.voltage:.2f} V    "
            f"{snap.current_a:.2f} A    {snap.temp_c:.1f} °C"
        )
        for row, j in enumerate(snap.joints):
            values = [
                f"J{j.index} {tr(f'joint.{j.index}')}", str(j.can_id), f"{j.gear_ratio:g}:1",
                f"{j.min_deg:+.1f}°", f"{j.max_deg:+.1f}°", f"{j.angle:+.2f}°",
                tr("on") if j.enabled else tr("off"),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))


class LogDialog(QDialog):
    def __init__(self, lines: List[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        _style(self)
        self.setWindowTitle(tr("nav.log"))
        self.resize(980, 620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        head = QHBoxLayout()
        title = QLabel(tr("page.log.title"))
        title.setObjectName("SectionTitle")
        head.addWidget(title)
        head.addStretch(1)
        copy = QPushButton(tr("dialog.copy"))
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.text.toPlainText()))
        head.addWidget(copy)
        export = QPushButton(tr("dialog.export"))
        export.clicked.connect(self._export)
        head.addWidget(export)
        lay.addLayout(head)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText("\n".join(lines))
        lay.addWidget(self.text, 1)
        close = QPushButton(tr("dialog.close"))
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, tr("dialog.export"), "episode1-log.txt", "Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.text.toPlainText())
