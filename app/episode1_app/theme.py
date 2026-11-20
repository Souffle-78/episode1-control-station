"""Visual system for the Episode 1 control station (light + dark)."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

PALETTES = {
    "light": {
        "bg": "#F4F7FB", "panel": "#FFFFFF", "panel_2": "#F9FBFE",
        "line": "#DFE7F0", "line_soft": "#EDF2F7",
        "text": "#17212B", "muted": "#617286", "dim": "#93A2B2",
        "green": "#0E9F6E", "green_dim": "#E8F7F1", "green_border": "#B7E8D5",
        "on_green": "#FFFFFF", "blue": "#2563EB", "blue_dim": "#EAF1FF",
        "blue_border": "#C7D9FF", "amber": "#B45309", "amber_dim": "#FFF4E5",
        "amber_border": "#F5D3A6", "red": "#DC3545", "red_dim": "#FDECEE",
        "red_border": "#F5C2C7", "on_red": "#FFFFFF",
        "hover": "#F1F5FA", "pressed": "#E7EEF7", "input_bg": "#FFFFFF",
        "nav_hover": "#F7FAFD", "nav_active": "#EAF7F1", "selected_card": "#F3FCF8",
        "table_bg": "#FFFFFF", "table_alt": "#F8FAFD", "table_header": "#F1F5F9",
        "table_select": "#E8F5EF", "scroll": "#C9D6E3",
        "log_bg": "#FBFCFE", "log_text": "#3A4C5E",
        "disabled_bg": "#F2F5F9", "disabled_text": "#A6B4C2",
    },
    "dark": {
        "bg": "#0B1117", "panel": "#111A23", "panel_2": "#16212B",
        "line": "#24313D", "line_soft": "#1B2733",
        "text": "#E8F0F7", "muted": "#8DA0B2", "dim": "#5D7285",
        "green": "#3DDB95", "green_dim": "#12382A", "green_border": "#1E5F47",
        "on_green": "#06110C", "blue": "#5AA9FF", "blue_dim": "#12263D",
        "blue_border": "#234B74", "amber": "#FFB454", "amber_dim": "#3A2A12",
        "amber_border": "#60431A", "red": "#FF6474", "red_dim": "#3A151C",
        "red_border": "#6B2430", "on_red": "#170407",
        "hover": "#172634", "pressed": "#0B1219", "input_bg": "#0B1219",
        "nav_hover": "#101922", "nav_active": "#0D1A16", "selected_card": "#0F1D1A",
        "table_bg": "#0A1016", "table_alt": "#0D151D", "table_header": "#111B25",
        "table_select": "#12382A", "scroll": "#243646",
        "log_bg": "#0A1016", "log_text": "#A9C1D3",
        "disabled_bg": "#0D141B", "disabled_text": "#536577",
    },
}

C = dict(PALETTES["light"])
MODE = "light"


def _font_family() -> str:
    families = set(QFontDatabase.families())
    for name in ("SF Pro Text", "SF Pro Display", "Helvetica Neue", "PingFang SC", "Inter"):
        if name in families:
            return name
    return "Sans Serif"


def _stylesheet() -> str:
    return f"""
* {{ outline: none; }}
QMainWindow, QWidget#Root, QDialog#Root {{ background: {C['bg']}; color: {C['text']}; }}
QWidget {{ color: {C['text']}; font-size: 12px; }}
QToolTip {{ background: {C['panel']}; color: {C['text']}; border: 1px solid {C['line']}; padding: 6px; }}
QFrame#TopBar {{ background: {C['panel']}; border-bottom: 1px solid {C['line']}; }}
QFrame#Sidebar {{ background: {C['panel']}; border-right: 1px solid {C['line']}; }}
QFrame#Panel {{ background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 14px; }}
QFrame#Card {{ background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 13px; }}
QFrame#Card:hover {{ background: {C['hover']}; }}
QFrame#Card[selected="true"] {{ border: 1px solid {C['green']}; background: {C['selected_card']}; }}
QFrame#Metric {{ background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 13px; }}
QLabel#Logo {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {C['green']}, stop:1 #158C67);
    color: #FFFFFF; border-radius: 10px; font-size: 17px; font-weight: 800;
}}
QLabel#AppTitle {{ font-size: 15px; font-weight: 700; letter-spacing: 1px; }}
QLabel#AppSub {{ color: {C['muted']}; font-size: 10px; letter-spacing: 1px; }}
QLabel#PageTitle {{ font-size: 26px; font-weight: 700; letter-spacing: -0.4px; }}
QLabel#PageSub {{ color: {C['muted']}; font-size: 11px; }}
QLabel#SectionTitle {{ color: {C['muted']}; font-size: 10px; font-weight: 700; letter-spacing: 1.6px; }}
QLabel#MetricLabel {{ color: {C['muted']}; font-size: 10px; letter-spacing: 1px; }}
QLabel#MetricValue {{ font-size: 25px; font-weight: 700; }}
QLabel#MetricUnit {{ color: {C['muted']}; font-size: 10px; }}
QLabel#Muted {{ color: {C['muted']}; }}
QLabel#Dim {{ color: {C['dim']}; }}
QLabel#JointName {{ font-size: 14px; font-weight: 700; letter-spacing: 0.3px; }}
QLabel#JointSub {{ color: {C['dim']}; font-size: 10px; }}
QLabel#Angle {{ font-size: 30px; font-weight: 700; letter-spacing: -0.8px; }}
QLabel#AngleUnit {{ color: {C['muted']}; font-size: 12px; }}
QLabel#StatusReady {{ color: {C['green']}; background: {C['green_dim']}; border: 1px solid {C['green_border']}; border-radius: 8px; padding: 3px 9px; font-size: 9px; font-weight: 700; }}
QLabel#StatusMove {{ color: {C['blue']}; background: {C['blue_dim']}; border: 1px solid {C['blue_border']}; border-radius: 8px; padding: 3px 9px; font-size: 9px; font-weight: 700; }}
QLabel#StatusWarn {{ color: {C['amber']}; background: {C['amber_dim']}; border: 1px solid {C['amber_border']}; border-radius: 8px; padding: 3px 9px; font-size: 9px; font-weight: 700; }}
QLabel#StatusError {{ color: {C['red']}; background: {C['red_dim']}; border: 1px solid {C['red_border']}; border-radius: 8px; padding: 3px 9px; font-size: 9px; font-weight: 700; }}
QPushButton {{
    background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 8px;
    padding: 8px 13px; color: {C['text']}; font-size: 11px; font-weight: 600;
}}
QPushButton:hover {{ background: {C['hover']}; border-color: {C['green_border']}; }}
QPushButton:pressed {{ background: {C['pressed']}; }}
QPushButton:disabled {{ color: {C['disabled_text']}; background: {C['disabled_bg']}; border-color: {C['line_soft']}; }}
QPushButton#Primary {{ background: {C['green']}; border: 1px solid {C['green']}; color: {C['on_green']}; font-weight: 700; }}
QPushButton#Primary:hover {{ background: #18B37E; border-color: #18B37E; }}
QPushButton#Primary:pressed {{ background: #0B8A5F; }}
QPushButton#Danger {{ background: {C['red']}; border: 1px solid {C['red']}; color: {C['on_red']}; font-weight: 700; }}
QPushButton#Danger:hover {{ background: #E84A5A; border-color: #E84A5A; }}
QPushButton#Danger:pressed {{ background: #C62E3E; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {C['line']}; color: {C['muted']}; }}
QPushButton#Ghost:hover {{ background: {C['hover']}; color: {C['text']}; }}
QPushButton#Nav {{
    background: transparent; border: none; border-left: 3px solid transparent;
    border-radius: 0; text-align: left; padding: 12px 16px;
    color: {C['muted']}; font-size: 11px; font-weight: 600; letter-spacing: 0.3px;
}}
QPushButton#Nav:hover {{ color: {C['text']}; background: {C['nav_hover']}; }}
QPushButton#Nav[active="true"] {{ color: {C['green']}; border-left: 3px solid {C['green']}; background: {C['nav_active']}; }}
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {C['input_bg']}; border: 1px solid {C['line']}; border-radius: 8px;
    padding: 7px 9px; color: {C['text']}; selection-background-color: {C['green']}; selection-color: {C['on_green']};
}}
QComboBox:hover, QLineEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: {C['green_border']}; }}
QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border: 1px solid {C['green']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: {C['panel']}; border: 1px solid {C['line']}; selection-background-color: {C['green_dim']}; selection-color: {C['text']}; color: {C['text']}; }}
QDoubleSpinBox QLineEdit, QSpinBox QLineEdit {{ padding-left: 6px; background: transparent; border: none; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::up-button, QSpinBox::down-button {{ width: 15px; background: {C['line_soft']}; border: none; }}
QCheckBox {{ color: {C['muted']}; spacing: 7px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 4px; border: 1px solid {C['line']}; background: {C['input_bg']}; }}
QCheckBox::indicator:checked {{ background: {C['green']}; border-color: {C['green']}; }}
QTableWidget {{
    background: {C['table_bg']}; alternate-background-color: {C['table_alt']}; color: {C['text']};
    gridline-color: {C['line_soft']}; border: 1px solid {C['line']}; border-radius: 10px;
    selection-background-color: {C['table_select']}; selection-color: {C['text']};
}}
QHeaderView::section {{ background: {C['table_header']}; color: {C['muted']}; border: none; border-right: 1px solid {C['line']}; border-bottom: 1px solid {C['line']}; padding: 8px 6px; font-size: 10px; font-weight: 700; }}
QTableCornerButton::section {{ background: {C['table_header']}; border: none; }}
QPlainTextEdit {{ background: {C['log_bg']}; border: 1px solid {C['line']}; border-radius: 10px; color: {C['log_text']}; font-family: "SF Mono", "Menlo", "Consolas", monospace; font-size: 10px; padding: 9px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['scroll']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {C['scroll']}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSplitter::handle {{ background: transparent; }}
"""


def apply_theme(app: QApplication, mode: str = "light") -> None:
    global MODE
    if mode not in PALETTES:
        mode = "light"
    MODE = mode
    C.clear()
    C.update(PALETTES[mode])
    app.setStyle("Fusion")
    family = _font_family()
    font = QFont(family, 12)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(C["input_bg"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C["table_alt"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(C["panel"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C["green"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C["on_green"]))
    app.setPalette(pal)
    app.setStyleSheet(_stylesheet())
