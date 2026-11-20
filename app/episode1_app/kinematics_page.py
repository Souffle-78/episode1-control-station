from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

from .i18n import tr
from .theme import C

try:
    from kinematics.episode1_model import fk, ik, Q_LIMITS_DEG, _rpy_matrix
except Exception:  # pragma: no cover - path bootstrap
    _root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from kinematics.episode1_model import fk, ik, Q_LIMITS_DEG, _rpy_matrix


def _spin(lo: float, hi: float, value: float, suffix: str = "") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(1)
    s.setSingleStep(1.0)
    s.setValue(value)
    if suffix:
        s.setSuffix(suffix)
    s.setMinimumHeight(30)
    s.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
    return s


class KinematicsDialog(QDialog):
    """Small FK/IK workbench using the official DH model."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Root")
        self.setWindowTitle(tr("kin.title"))
        self.resize(980, 600)
        app = QApplication.instance()
        self.setStyleSheet((parent.styleSheet() if parent else "") or (app.styleSheet() if app else ""))

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        title = QLabel(tr("kin.title"))
        title.setStyleSheet(f"font-size:20px;font-weight:800;color:{C['text']};")
        root.addWidget(title)
        sub = QLabel(tr("kin.sub"))
        sub.setObjectName("JointSub")
        sub.setWordWrap(True)
        root.addWidget(sub)

        cols = QHBoxLayout()
        cols.setSpacing(18)
        root.addLayout(cols, 1)

        # joint angles
        left = QWidget()
        lg = QGridLayout(left)
        lg.setContentsMargins(0, 0, 0, 0)
        lg.setHorizontalSpacing(10)
        lg.setVerticalSpacing(8)
        lg.addWidget(self._section(tr("kin.joints")), 0, 0, 1, 2)
        self.q_spins: list[QDoubleSpinBox] = []
        for i in range(6):
            lg.addWidget(QLabel(f"q{i + 1}"), i + 1, 0)
            s = _spin(-360, 360, (0, 90, 0, 0, 0, 0)[i], " °")
            self.q_spins.append(s)
            lg.addWidget(s, i + 1, 1)
        self.fk_btn = QPushButton(tr("kin.fk"))
        self.fk_btn.setObjectName("Primary")
        self.fk_btn.clicked.connect(self._compute_fk)
        lg.addWidget(self.fk_btn, 7, 0, 1, 2)
        lg.setRowStretch(8, 1)
        cols.addWidget(left, 1)

        # target pose
        right = QWidget()
        rg = QGridLayout(right)
        rg.setContentsMargins(0, 0, 0, 0)
        rg.setHorizontalSpacing(10)
        rg.setVerticalSpacing(8)
        rg.addWidget(self._section(tr("kin.target")), 0, 0, 1, 4)
        self.xyz = [_spin(-1000, 1000, v, " mm") for v in (302, 0, 422)]
        self.rpy = [_spin(-180, 180, v, " °") for v in (135, -90, 45)]
        for i, lab in enumerate(("X", "Y", "Z")):
            rg.addWidget(QLabel(lab), i + 1, 0)
            rg.addWidget(self.xyz[i], i + 1, 1)
        for i, lab in enumerate(("R", "P", "Y")):
            rg.addWidget(QLabel(lab), i + 1, 2)
            rg.addWidget(self.rpy[i], i + 1, 3)
        self.ik_btn = QPushButton(tr("kin.ik"))
        self.ik_btn.setObjectName("Primary")
        self.ik_btn.clicked.connect(self._solve_ik)
        rg.addWidget(self.ik_btn, 5, 0, 1, 4)
        self.status = QLabel(tr("kin.ready"))
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color:{C['green']};font-size:12px;")
        rg.addWidget(self.status, 6, 0, 1, 4)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.result.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        rg.addWidget(self.result, 7, 0, 1, 4)
        rg.setRowStretch(8, 1)
        cols.addWidget(right, 1)

        close = QPushButton(tr("kin.close"))
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        root.addLayout(row)

        self._compute_fk()

    @staticmethod
    def _section(text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("SectionTitle")
        return lab

    def _q(self) -> list[float]:
        return [s.value() for s in self.q_spins]

    def _compute_fk(self) -> None:
        try:
            T = fk(np.deg2rad(self._q()))
            x, y, z = T[:3, 3]
            rpy = np.rad2deg([
                math.atan2(T[2, 1], T[2, 2]),
                math.asin(float(np.clip(-T[2, 0], -1.0, 1.0))),
                math.atan2(T[1, 0], T[0, 0]),
            ])
            self.xyz[0].setValue(float(x))
            self.xyz[1].setValue(float(y))
            self.xyz[2].setValue(float(z))
            for s, v in zip(self.rpy, rpy):
                s.setValue(float(v))
            self.status.setText(tr("kin.fk_ok", x=f"{x:.1f}", y=f"{y:.1f}", z=f"{z:.1f}"))
            self.result.setText(
                tr("kin.result", x=f"{x:.1f}", y=f"{y:.1f}", z=f"{z:.1f}",
                   r=f"{rpy[0]:.1f}", p=f"{rpy[1]:.1f}", yaw=f"{rpy[2]:.1f}")
            )
        except Exception as exc:
            self.status.setText(tr("kin.error", error=str(exc)))

    def _solve_ik(self) -> None:
        target = np.eye(4)
        target[:3, 3] = [s.value() for s in self.xyz]
        target[:3, :3] = _rpy_matrix([s.value() for s in self.rpy])
        try:
            res = ik(target, np.deg2rad(self._q()), q_limits_deg=Q_LIMITS_DEG)
        except Exception as exc:
            self.status.setText(tr("kin.error", error=str(exc)))
            return
        if not res.success:
            self.status.setText(tr("kin.unreachable", e=f"{res.position_error_mm:.1f}",
                                   r=f"{res.rotation_error_deg:.1f}"))
            return
        for s, v in zip(self.q_spins, np.rad2deg(res.q)):
            s.setValue(float(v))
        self._compute_fk()
        self.status.setText(tr("kin.ik_ok", e=f"{res.position_error_mm:.2f}",
                               r=f"{res.rotation_error_deg:.2f}"))
