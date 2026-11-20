"""Visual system for the Episode 1 control station."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

C = {
    "bg": "#080C11",
    "panel": "#0E151D",
    "panel_2": "#111B25",
    "line": "#1D2B38",
    "line_soft": "#16222D",
    "text": "#E8F0F7",
    "muted": "#8396A8",
    "dim": "#536577",
    "green": "#39D98A",
    "green_dim": "#12382A",
    "blue": "#53A8FF",
    "blue_dim": "#12263D",
    "amber": "#FFB454",
    "amber_dim": "#3A2A12",
    "red": "#FF5C6C",
    "red_dim": "#3A151C",
}


def _font_family() -> str:
    families = set(QFontDatabase.families())
    for name in ("SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Inter"):
        if name in families:
            return name
    return "Sans Serif"


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    family = _font_family()
    font = QFont(family, 12)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)


STYLESHEET = f"""
* {{
    outline: none;
}}
QMainWindow, QWidget#Root {{
    background: {C['bg']};
    color: {C['text']};
}}
QWidget {{
    color: {C['text']};
    font-size: 12px;
}}
QFrame#TopBar {{
    background: {C['panel']};
    border-bottom: 1px solid {C['line']};
}}
QFrame#Sidebar {{
    background: {C['panel']};
    border-right: 1px solid {C['line']};
}}
QFrame#Panel {{
    background: {C['panel']};
    border: 1px solid {C['line']};
    border-radius: 10px;
}}
QFrame#Card {{
    background: {C['panel_2']};
    border: 1px solid {C['line']};
    border-radius: 10px;
}}
QFrame#Card[selected="true"] {{
    border: 1px solid {C['green']};
    background: #0F1D1A;
}}
QFrame#Metric {{
    background: {C['panel']};
    border: 1px solid {C['line']};
    border-radius: 9px;
}}
QLabel#Logo {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C['green']}, stop:1 #1D9E67);
    color: #06110C;
    border-radius: 9px;
    font-size: 17px;
    font-weight: 800;
}}
QLabel#AppTitle {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#AppSub {{
    color: {C['muted']};
    font-size: 10px;
    letter-spacing: 1px;
}}
QLabel#PageTitle {{
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}
QLabel#PageSub {{
    color: {C['muted']};
    font-size: 11px;
}}
QLabel#SectionTitle {{
    color: {C['muted']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}
QLabel#MetricLabel {{
    color: {C['muted']};
    font-size: 10px;
    letter-spacing: 1px;
}}
QLabel#MetricValue {{
    font-size: 24px;
    font-weight: 700;
}}
QLabel#MetricUnit {{
    color: {C['muted']};
    font-size: 10px;
}}
QLabel#Muted {{
    color: {C['muted']};
}}
QLabel#Dim {{
    color: {C['dim']};
}}
QLabel#JointName {{
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QLabel#JointSub {{
    color: {C['dim']};
    font-size: 10px;
}}
QLabel#Angle {{
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.8px;
}}
QLabel#AngleUnit {{
    color: {C['muted']};
    font-size: 12px;
}}
QLabel#StatusReady {{
    color: {C['green']};
    background: {C['green_dim']};
    border: 1px solid #1B5B42;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel#StatusMove {{
    color: {C['blue']};
    background: {C['blue_dim']};
    border: 1px solid #1D4C78;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel#StatusWarn {{
    color: {C['amber']};
    background: {C['amber_dim']};
    border: 1px solid #60431A;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel#StatusError {{
    color: {C['red']};
    background: {C['red_dim']};
    border: 1px solid #6B2430;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QPushButton {{
    background: {C['panel_2']};
    border: 1px solid {C['line']};
    border-radius: 7px;
    padding: 8px 12px;
    color: {C['text']};
    font-size: 11px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: #172534;
    border-color: #2A3D4E;
}}
QPushButton:pressed {{
    background: #0B1219;
}}
QPushButton:disabled {{
    color: {C['dim']};
    background: #0D141B;
    border-color: #16222D;
}}
QPushButton#Primary {{
    background: {C['green']};
    border: 1px solid {C['green']};
    color: #06110C;
}}
QPushButton#Primary:hover {{
    background: #54E7A0;
}}
QPushButton#Danger {{
    background: {C['red']};
    border: 1px solid {C['red']};
    color: #170407;
    font-weight: 800;
}}
QPushButton#Danger:hover {{
    background: #FF7482;
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid {C['line']};
    color: {C['muted']};
}}
QPushButton#Nav {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    text-align: left;
    padding: 11px 16px;
    color: {C['muted']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}
QPushButton#Nav:hover {{
    color: {C['text']};
    background: #101922;
}}
QPushButton#Nav[active="true"] {{
    color: {C['green']};
    border-left: 2px solid {C['green']};
    background: #0D1A16;
}}
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: #0B1219;
    border: 1px solid {C['line']};
    border-radius: 7px;
    padding: 7px 9px;
    color: {C['text']};
    selection-background-color: {C['green']};
    selection-color: #06110C;
}}
QComboBox:hover, QLineEdit:hover, QDoubleSpinBox:hover {{
    border-color: #2A3D4E;
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background: {C['panel_2']};
    border: 1px solid {C['line']};
    selection-background-color: #163327;
    color: {C['text']};
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
    width: 14px;
    background: {C['panel_2']};
    border: none;
}}
QCheckBox {{
    color: {C['muted']};
    spacing: 7px;
}}
QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    border-radius: 4px;
    border: 1px solid {C['line']};
    background: #0B1219;
}}
QCheckBox::indicator:checked {{
    background: {C['green']};
    border-color: {C['green']};
}}
QTableWidget {{
    background: #0A1016;
    alternate-background-color: #0D151D;
    color: {C['text']};
    gridline-color: #1A2A37;
    border: 1px solid {C['line']};
    border-radius: 8px;
    selection-background-color: #12382A;
    selection-color: {C['text']};
}}
QHeaderView::section {{
    background: #111B25;
    color: {C['muted']};
    border: none;
    border-right: 1px solid {C['line']};
    border-bottom: 1px solid {C['line']};
    padding: 7px 6px;
    font-size: 10px;
    font-weight: 700;
}}
QTableCornerButton::section {{
    background: #111B25;
    border: none;
}}
QPlainTextEdit {{
    background: #0A1016;
    border: 1px solid {C['line']};
    border-radius: 8px;
    color: #A9C1D3;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
    font-size: 10px;
    padding: 8px;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #243646;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QSplitter::handle {{
    background: transparent;
}}
"""
