"""
sidebar.py — Sidebar navigation widget
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFrame, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor
from src.ui.styles import COLOR_NAVY, COLOR_ORANGE, COLOR_WHITE, COLOR_SIDEBAR_SELECTED


NAV_ITEMS = [
    ("charts",      "  \u2503  Charts"),
    ("annual",      "  \u2503  Annual Totals"),
    ("categories",  "  \u2503  Categories"),
    ("budgets",     "  \u2503  Budgets"),
    ("settings",    "  \u2503  Settings"),
]


class Sidebar(QWidget):
    account_selected = pyqtSignal(int)   # account_id
    nav_selected = pyqtSignal(str)       # key string
    add_account_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(250)
        self.setStyleSheet(f"background-color: {COLOR_NAVY};")
        self._accounts = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ----- Accounts header -----
        acct_header = QLabel("  ACCOUNTS")
        acct_header.setStyleSheet(
            f"color: rgba(255,255,255,0.55); font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; background-color: {COLOR_NAVY}; "
            f"padding: 14px 0 6px 14px;"
        )
        layout.addWidget(acct_header)

        # Account list
        self._account_list = QListWidget()
        self._account_list.setObjectName("sidebar")
        self._account_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._account_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._account_list.setMaximumHeight(300)
        self._account_list.setStyleSheet(
            f"QListWidget#sidebar {{ background-color: {COLOR_NAVY}; border: none; }}"
            f"QListWidget#sidebar::item {{ padding: 8px 0 8px 20px; color: rgba(255,255,255,0.85); }}"
            f"QListWidget#sidebar::item:selected {{ background-color: {COLOR_SIDEBAR_SELECTED}; color: white; font-weight: 600; }}"
            f"QListWidget#sidebar::item:hover:!selected {{ background-color: rgba(255,255,255,0.10); }}"
        )
        self._account_list.itemClicked.connect(self._on_account_clicked)
        layout.addWidget(self._account_list)

        # Add account button
        add_btn = QPushButton("  + Add Account")
        add_btn.setStyleSheet(
            f"background-color: transparent; color: {COLOR_ORANGE}; border: none; "
            f"text-align: left; padding: 8px 0 8px 20px; font-size: 12px; "
            f"font-weight: 600; min-height: 0;"
        )
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_account_clicked.emit)
        layout.addWidget(add_btn)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: rgba(255,255,255,0.15); max-height: 1px; margin: 6px 14px;")
        layout.addWidget(divider)

        # Nav header
        nav_header = QLabel("  TOOLS")
        nav_header.setStyleSheet(
            f"color: rgba(255,255,255,0.55); font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.5px; background-color: {COLOR_NAVY}; "
            f"padding: 10px 0 6px 14px;"
        )
        layout.addWidget(nav_header)

        # Nav items list
        self._nav_list = QListWidget()
        self._nav_list.setObjectName("sidebar")
        self._nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._nav_list.setStyleSheet(
            f"QListWidget#sidebar {{ background-color: {COLOR_NAVY}; border: none; }}"
            f"QListWidget#sidebar::item {{ padding: 9px 0 9px 20px; color: rgba(255,255,255,0.85); }}"
            f"QListWidget#sidebar::item:selected {{ background-color: {COLOR_SIDEBAR_SELECTED}; color: white; font-weight: 600; }}"
            f"QListWidget#sidebar::item:hover:!selected {{ background-color: rgba(255,255,255,0.10); }}"
        )

        nav_labels = {
            "charts":     "\U0001F4CA  Charts",
            "annual":     "\U0001F4C5  Annual Totals",
            "categories": "\U0001F3F7  Categories",
            "budgets":    "\U0001F4B0  Budgets",
            "settings":   "\u2699\uFE0F  Settings",
        }

        for key, label in NAV_ITEMS:
            item = QListWidgetItem(nav_labels.get(key, label))
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(250, 38))
            self._nav_list.addItem(item)

        self._nav_list.itemClicked.connect(self._on_nav_clicked)
        layout.addWidget(self._nav_list)

        layout.addStretch()

    def load_accounts(self, accounts: list):
        """Populate the accounts list. accounts = list of dicts."""
        self._accounts = accounts
        self._account_list.clear()
        for acc in accounts:
            type_icon = {
                "Checking": "\U0001F4B3",
                "Savings": "\U0001F4B0",
                "Credit Card": "\U0001F4B8",
                "Cash": "\U0001F4B5",
                "Investment": "\U0001F4C8",
                "Other": "\U0001F4BC",
            }.get(acc['type'], "\U0001F4BC")
            label = f"  {type_icon}  {acc['name']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, acc['id'])
            item.setSizeHint(QSize(250, 36))
            self._account_list.addItem(item)

        # Resize list dynamically
        count = self._account_list.count()
        self._account_list.setMaximumHeight(min(300, count * 36 + 4))

    def _on_account_clicked(self, item: QListWidgetItem):
        account_id = item.data(Qt.ItemDataRole.UserRole)
        if account_id is not None:
            self._nav_list.clearSelection()
            self.account_selected.emit(account_id)

    def _on_nav_clicked(self, item: QListWidgetItem):
        key = item.data(Qt.ItemDataRole.UserRole)
        if key:
            self._account_list.clearSelection()
            self.nav_selected.emit(key)

    def select_account(self, account_id: int):
        for i in range(self._account_list.count()):
            item = self._account_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == account_id:
                self._account_list.setCurrentItem(item)
                self._nav_list.clearSelection()
                break

    def clear_selection(self):
        self._account_list.clearSelection()
        self._nav_list.clearSelection()
