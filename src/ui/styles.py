"""
styles.py — Global stylesheet for LankAmerica Compass
"""

# Color constants
COLOR_NAVY = "#0D2B5C"
COLOR_MEDIUM_BLUE = "#1565C0"
COLOR_ORANGE = "#E07B39"
COLOR_LIGHT_BG = "#EEF4FB"
COLOR_WHITE = "#FFFFFF"
COLOR_RED = "#C62828"
COLOR_GREEN = "#2E7D32"
COLOR_BORDER = "#C5D5E8"
COLOR_ALT_ROW = "#F4F8FD"
COLOR_RECONCILED_BG = "#E0E0E0"
COLOR_RECONCILED_TEXT = "#888888"
COLOR_TABLE_HEADER_BG = "#0D2B5C"
COLOR_TABLE_HEADER_TEXT = "#FFFFFF"
COLOR_SIDEBAR_BG = "#0D2B5C"
COLOR_SIDEBAR_TEXT = "#FFFFFF"
COLOR_SIDEBAR_SELECTED = "#1565C0"

STYLESHEET = f"""
/* ===== Global ===== */
QMainWindow, QWidget {{
    background-color: {COLOR_LIGHT_BG};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #1A1A2E;
}}

QDialog {{
    background-color: {COLOR_WHITE};
}}

/* ===== Buttons ===== */
QPushButton {{
    background-color: {COLOR_NAVY};
    color: {COLOR_WHITE};
    border: none;
    border-radius: 5px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 600;
    min-height: 32px;
}}
QPushButton:hover {{
    background-color: {COLOR_MEDIUM_BLUE};
}}
QPushButton:pressed {{
    background-color: #0a2048;
}}
QPushButton:disabled {{
    background-color: #aabbd4;
    color: #dde5ef;
}}

QPushButton[secondary="true"] {{
    background-color: transparent;
    color: {COLOR_NAVY};
    border: 2px solid {COLOR_NAVY};
    border-radius: 5px;
}}
QPushButton[secondary="true"]:hover {{
    background-color: {COLOR_LIGHT_BG};
    border-color: {COLOR_MEDIUM_BLUE};
    color: {COLOR_MEDIUM_BLUE};
}}

QPushButton[danger="true"] {{
    background-color: {COLOR_RED};
    color: {COLOR_WHITE};
}}
QPushButton[danger="true"]:hover {{
    background-color: #b71c1c;
}}

QPushButton[accent="true"] {{
    background-color: {COLOR_ORANGE};
    color: {COLOR_WHITE};
}}
QPushButton[accent="true"]:hover {{
    background-color: #c9692a;
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    color: {COLOR_NAVY};
    border: none;
    padding: 4px 8px;
    font-weight: 500;
}}
QPushButton[flat="true"]:hover {{
    background-color: rgba(21, 101, 192, 0.12);
    border-radius: 4px;
}}

/* ===== Inputs ===== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLOR_WHITE};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 5px 9px;
    font-size: 13px;
    color: #1A1A2E;
    selection-background-color: {COLOR_MEDIUM_BLUE};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLOR_MEDIUM_BLUE};
    outline: none;
}}
QLineEdit:read-only {{
    background-color: #f0f4f8;
    color: #555;
}}

QComboBox {{
    background-color: {COLOR_WHITE};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 5px 9px;
    font-size: 13px;
    color: #1A1A2E;
    min-height: 28px;
}}
QComboBox:focus {{
    border-color: {COLOR_MEDIUM_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLOR_NAVY};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_MEDIUM_BLUE};
    selection-color: {COLOR_WHITE};
    padding: 2px;
}}

QDateEdit {{
    background-color: {COLOR_WHITE};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 5px 9px;
    font-size: 13px;
    color: #1A1A2E;
    min-height: 28px;
}}
QDateEdit:focus {{
    border-color: {COLOR_MEDIUM_BLUE};
}}
QDateEdit::drop-down {{
    border: none;
    width: 22px;
}}

QDoubleSpinBox, QSpinBox {{
    background-color: {COLOR_WHITE};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 5px 9px;
    font-size: 13px;
    color: #1A1A2E;
    min-height: 28px;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {COLOR_MEDIUM_BLUE};
}}

/* ===== Table ===== */
QTableWidget {{
    background-color: {COLOR_WHITE};
    alternate-background-color: {COLOR_ALT_ROW};
    border: 1px solid {COLOR_BORDER};
    gridline-color: {COLOR_BORDER};
    font-size: 13px;
    selection-background-color: rgba(21, 101, 192, 0.18);
    selection-color: #1A1A2E;
}}
QTableWidget::item {{
    padding: 4px 6px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: rgba(21, 101, 192, 0.18);
    color: #1A1A2E;
}}
QHeaderView::section {{
    background-color: {COLOR_TABLE_HEADER_BG};
    color: {COLOR_TABLE_HEADER_TEXT};
    font-weight: 700;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #1a4080;
    border-bottom: 2px solid {COLOR_ORANGE};
}}
QHeaderView::section:last {{
    border-right: none;
}}
QHeaderView::section:checked {{
    background-color: {COLOR_MEDIUM_BLUE};
}}

/* ===== Sidebar ===== */
QListWidget#sidebar {{
    background-color: {COLOR_SIDEBAR_BG};
    color: {COLOR_SIDEBAR_TEXT};
    border: none;
    font-size: 13px;
    padding: 4px 0;
    outline: none;
}}
QListWidget#sidebar::item {{
    padding: 9px 18px;
    border-radius: 0;
    color: rgba(255,255,255,0.85);
}}
QListWidget#sidebar::item:selected {{
    background-color: {COLOR_SIDEBAR_SELECTED};
    color: {COLOR_WHITE};
    font-weight: 600;
}}
QListWidget#sidebar::item:hover:!selected {{
    background-color: rgba(255,255,255,0.10);
    color: {COLOR_WHITE};
}}

/* ===== Tab Widget ===== */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    border-top: 2px solid {COLOR_MEDIUM_BLUE};
    background-color: {COLOR_WHITE};
}}
QTabBar::tab {{
    background-color: #dde8f5;
    color: {COLOR_NAVY};
    padding: 7px 20px;
    border: 1px solid {COLOR_BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {COLOR_WHITE};
    color: {COLOR_NAVY};
    font-weight: 700;
    border-bottom: 2px solid {COLOR_WHITE};
}}
QTabBar::tab:hover:!selected {{
    background-color: #c8daed;
}}

/* ===== GroupBox ===== */
QGroupBox {{
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 8px;
    font-weight: 600;
    color: {COLOR_NAVY};
    background-color: {COLOR_WHITE};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {COLOR_NAVY};
    font-weight: 700;
    font-size: 13px;
}}

/* ===== Labels ===== */
QLabel {{
    color: #1A1A2E;
}}
QLabel[heading="true"] {{
    font-size: 20px;
    font-weight: 700;
    color: {COLOR_NAVY};
}}
QLabel[subheading="true"] {{
    font-size: 14px;
    font-weight: 600;
    color: {COLOR_MEDIUM_BLUE};
}}
QLabel[balance="true"] {{
    font-size: 24px;
    font-weight: 700;
}}
QLabel[badge="true"] {{
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel[error="true"] {{
    color: {COLOR_RED};
    font-size: 12px;
}}
QLabel[success="true"] {{
    color: {COLOR_GREEN};
    font-size: 12px;
}}

/* ===== Scrollbar ===== */
QScrollBar:vertical {{
    background: #e8eef6;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_NAVY};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}
QScrollBar:horizontal {{
    background: #e8eef6;
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {COLOR_NAVY};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

/* ===== CheckBox ===== */
QCheckBox {{
    spacing: 6px;
    color: #1A1A2E;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 3px;
    background-color: {COLOR_WHITE};
}}
QCheckBox::indicator:checked {{
    background-color: {COLOR_MEDIUM_BLUE};
    border-color: {COLOR_MEDIUM_BLUE};
}}
QCheckBox::indicator:hover {{
    border-color: {COLOR_MEDIUM_BLUE};
}}

/* ===== RadioButton ===== */
QRadioButton {{
    spacing: 6px;
    color: #1A1A2E;
    font-size: 13px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 8px;
    background-color: {COLOR_WHITE};
}}
QRadioButton::indicator:checked {{
    background-color: {COLOR_MEDIUM_BLUE};
    border-color: {COLOR_MEDIUM_BLUE};
}}

/* ===== Splitter ===== */
QSplitter::handle {{
    background-color: {COLOR_BORDER};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

/* ===== Dialog Button Box ===== */
QDialogButtonBox QPushButton {
    background-color: #0D2B5C;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 600;
    min-height: 32px;
    min-width: 80px;
}
QDialogButtonBox QPushButton:hover {
    background-color: #1565C0;
}

/* ===== Status Bar ===== */
QStatusBar {{
    background-color: {COLOR_NAVY};
    color: rgba(255,255,255,0.8);
    font-size: 11px;
    padding: 2px 8px;
    border-top: 1px solid #1a4080;
}}
QStatusBar::item {{
    border: none;
}}

/* ===== Menu ===== */
QMenu {{
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 20px;
    color: #1A1A2E;
}}
QMenu::item:selected {{
    background-color: {COLOR_LIGHT_BG};
    color: {COLOR_NAVY};
}}
QMenu::separator {{
    height: 1px;
    background-color: {COLOR_BORDER};
    margin: 4px 0;
}}

/* ===== ToolTip ===== */
QToolTip {{
    background-color: {COLOR_NAVY};
    color: {COLOR_WHITE};
    border: none;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 12px;
}}

/* ===== Progress Bar ===== */
QProgressBar {{
    border: none;
    background-color: rgba(255,255,255,0.3);
    border-radius: 3px;
    text-align: center;
    color: {COLOR_WHITE};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {COLOR_ORANGE};
    border-radius: 3px;
}}

/* ===== Frame ===== */
QFrame[card="true"] {{
    background-color: {COLOR_WHITE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}
"""


def make_badge_style(bg: str, text_color: str) -> str:
    """Return an inline style string for a badge label."""
    return (
        f"background-color: {bg}; color: {text_color}; "
        f"border-radius: 10px; padding: 2px 10px; "
        f"font-size: 11px; font-weight: 600;"
    )


ACCOUNT_TYPE_COLORS = {
    "Checking":    ("#1565C0", "#FFFFFF"),
    "Savings":     ("#2E7D32", "#FFFFFF"),
    "Credit Card": ("#C62828", "#FFFFFF"),
    "Cash":        ("#E07B39", "#FFFFFF"),
    "Investment":  ("#6A1B9A", "#FFFFFF"),
    "Other":       ("#546E7A", "#FFFFFF"),
}
