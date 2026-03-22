"""
main_window.py — Main application window for LankAmerica Compass
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QStatusBar, QFrame, QMessageBox,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QColor

from pathlib import Path

from src.database import Database
from src.utils import get_assets_dir, format_currency
from src.ui.sidebar import Sidebar
from src.ui.accounts_widget import AccountDialog
from src.ui.register_widget import RegisterWidget
from src.ui.categories_widget import CategoriesWidget
from src.ui.budget_widget import BudgetWidget
from src.ui.charts_widget import ChartsWidget
from src.ui.annual_widget import AnnualWidget
from src.ui.settings_widget import SettingsWidget
from src.ui.styles import COLOR_NAVY, COLOR_WHITE, COLOR_ORANGE, COLOR_BORDER, COLOR_LIGHT_BG


# Index constants for stacked widget
IDX_WELCOME = 0
IDX_REGISTER = 1   # dynamic — one per account
IDX_CHARTS = 2
IDX_ANNUAL = 3
IDX_CATEGORIES = 4
IDX_BUDGETS = 5
IDX_SETTINGS = 6


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, db: Database, user: dict):
        super().__init__()
        self.db = db
        self.user = user
        self._register_widgets = {}  # account_id -> RegisterWidget

        self.setWindowTitle("LankAmerica Compass — Personal Financial Planner")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._load_accounts()

        # Show welcome or first account
        accounts = self.db.get_accounts_for_user(self.user['id'])
        if accounts:
            self._open_account(accounts[0]['id'])
        else:
            self._stack.setCurrentIndex(IDX_WELCOME)

    # -------------------------------------------------------------------------
    # Build UI
    # -------------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        main_layout.addWidget(self._build_topbar())

        # Body: sidebar + stack
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar(self)
        self._sidebar.account_selected.connect(self._open_account)
        self._sidebar.nav_selected.connect(self._open_nav)
        self._sidebar.add_account_clicked.connect(self._add_account)
        body.addWidget(self._sidebar)

        # Right content area
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {COLOR_LIGHT_BG};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {COLOR_LIGHT_BG};")

        # Index 0: Welcome
        self._stack.addWidget(self._build_welcome())

        # Index 1: placeholder (register widgets are added dynamically from idx 1+)
        # We use a placeholder; real register widgets replace slots by account_id mapping
        # Store as {account_id: stack_index}
        self._register_stack_indices = {}
        # We track a running next_index for dynamic pages
        self._next_stack_idx = 1  # will be incremented as registers added

        # Charts (idx = assigned later, use dict)
        self._charts_widget = ChartsWidget(self.db, self.user['id'], self)
        self._stack.addWidget(self._charts_widget)
        self._charts_idx = self._stack.count() - 1

        self._annual_widget = AnnualWidget(self.db, self.user['id'], self)
        self._stack.addWidget(self._annual_widget)
        self._annual_idx = self._stack.count() - 1

        self._categories_widget = CategoriesWidget(self.db, self.user['id'], self)
        self._stack.addWidget(self._categories_widget)
        self._cats_idx = self._stack.count() - 1

        self._budget_widget = BudgetWidget(self.db, self.user['id'], self)
        self._stack.addWidget(self._budget_widget)
        self._budgets_idx = self._stack.count() - 1

        self._settings_widget = SettingsWidget(self.db, self.user, self)
        self._settings_widget.database_changed.connect(self._on_db_changed)
        self._settings_widget.user_updated.connect(self._on_user_updated)
        self._stack.addWidget(self._settings_widget)
        self._settings_idx = self._stack.count() - 1

        right_layout.addWidget(self._stack)
        body.addWidget(right_panel, 1)

        main_layout.addLayout(body, 1)

        # Status bar
        self._status = QStatusBar()
        self._status.setFixedHeight(24)
        self.setStatusBar(self._status)
        self._update_statusbar()

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"background-color: {COLOR_NAVY}; border-bottom: 2px solid {COLOR_ORANGE};"
        )
        hlay = QHBoxLayout(bar)
        hlay.setContentsMargins(14, 6, 14, 6)
        hlay.setSpacing(10)

        # Logo / title
        assets = get_assets_dir()
        logo_small = assets / "logo_small.png"
        if logo_small.exists():
            lbl = QLabel()
            pix = QPixmap(str(logo_small))
            if not pix.isNull():
                pix = pix.scaledToHeight(36, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(pix)
                hlay.addWidget(lbl)

        title_lbl = QLabel("LankAmerica Compass")
        title_lbl.setStyleSheet(
            "color: white; font-size: 16px; font-weight: 700; "
            "letter-spacing: 0.5px; background: transparent;"
        )
        hlay.addWidget(title_lbl)
        hlay.addStretch()

        # User display
        self._user_btn = QPushButton(f"\U0001F464  {self.user.get('display_name', 'User')}")
        self._user_btn.setStyleSheet(
            "QPushButton { background: transparent; color: rgba(255,255,255,0.85); "
            "border: 1px solid rgba(255,255,255,0.25); border-radius: 4px; "
            "padding: 4px 12px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.1); }"
        )
        hlay.addWidget(self._user_btn)

        # Settings button
        settings_btn = QPushButton("\u2699\uFE0F")
        settings_btn.setToolTip("Settings")
        settings_btn.setStyleSheet(
            "QPushButton { background: transparent; color: white; border: none; "
            "font-size: 16px; padding: 4px 8px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.15); border-radius: 4px; }"
        )
        settings_btn.clicked.connect(lambda: self._open_nav("settings"))
        hlay.addWidget(settings_btn)

        # Logout button
        logout_btn = QPushButton("\u23FB")
        logout_btn.setToolTip("Log Out")
        logout_btn.setStyleSheet(
            "QPushButton { background: transparent; color: rgba(255,255,255,0.7); border: none; "
            "font-size: 16px; padding: 4px 8px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.15); border-radius: 4px; color: white; }"
        )
        logout_btn.clicked.connect(self._confirm_logout)
        hlay.addWidget(logout_btn)

        return bar

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {COLOR_LIGHT_BG};")
        vlay = QVBoxLayout(w)
        vlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vlay.setSpacing(16)

        lbl = QLabel("Welcome to LankAmerica Compass")
        lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 24px; font-weight: 700;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vlay.addWidget(lbl)

        sub = QLabel("Get started by adding an account in the sidebar.")
        sub.setStyleSheet("color: #555; font-size: 14px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vlay.addWidget(sub)

        btn = QPushButton("+ Add Your First Account")
        btn.setProperty("accent", True)
        btn.setFixedWidth(240)
        btn.clicked.connect(self._add_account)
        vlay.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        return w

    # -------------------------------------------------------------------------
    # Account management
    # -------------------------------------------------------------------------

    def _load_accounts(self):
        accounts = self.db.get_accounts_for_user(self.user['id'])
        self._sidebar.load_accounts(accounts)

    def _open_account(self, account_id: int):
        if account_id not in self._register_stack_indices:
            rw = RegisterWidget(self.db, account_id, self.user['id'], self)
            self._stack.addWidget(rw)
            idx = self._stack.count() - 1
            self._register_stack_indices[account_id] = idx
            self._register_widgets[account_id] = rw
        else:
            rw = self._register_widgets[account_id]
            rw.refresh()

        self._stack.setCurrentIndex(self._register_stack_indices[account_id])
        self._sidebar.select_account(account_id)
        self._update_statusbar()

    def _add_account(self):
        dlg = AccountDialog(
            parent=self, db=self.db, current_user_id=self.user['id']
        )
        if dlg.exec() == AccountDialog.DialogCode.Accepted:
            data = dlg.get_result()
            try:
                acc_id = self.db.create_account(
                    name=data['name'],
                    type=data['type'],
                    owner_user_id=self.user['id'],
                    opening_balance=data['opening_balance'],
                    notes=data['notes']
                )
                if data.get('shared_user_ids'):
                    self.db.set_account_shares(acc_id, data['shared_user_ids'])
                self._load_accounts()
                self._open_account(acc_id)
            except Exception as e:
                self.show_status_message(f"Error creating account: {e}")

    def _edit_account(self, account_id: int):
        account = self.db.get_account_by_id(account_id)
        if not account:
            return
        dlg = AccountDialog(
            parent=self, db=self.db,
            current_user_id=self.user['id'],
            account=dict(account)
        )
        if dlg.exec() == AccountDialog.DialogCode.Accepted:
            data = dlg.get_result()
            try:
                self.db.update_account(
                    account_id,
                    name=data['name'],
                    type=data['type'],
                    opening_balance=data['opening_balance'],
                    notes=data['notes']
                )
                if 'shared_user_ids' in data:
                    self.db.set_account_shares(account_id, data['shared_user_ids'])
                self._load_accounts()
                if account_id in self._register_widgets:
                    self._register_widgets[account_id].load_account()
                    self._register_widgets[account_id].refresh()
            except Exception as e:
                self.show_status_message(f"Error updating account: {e}")

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def _open_nav(self, key: str):
        nav_map = {
            "charts": self._charts_idx,
            "annual": self._annual_idx,
            "categories": self._cats_idx,
            "budgets": self._budgets_idx,
            "settings": self._settings_idx,
        }
        if key == "charts":
            self._charts_widget.refresh()
        elif key == "annual":
            self._annual_widget.refresh()
        elif key == "categories":
            self._categories_widget.refresh()
        elif key == "budgets":
            self._budget_widget.refresh()
        elif key == "settings":
            self._settings_widget.refresh(self.user)

        idx = nav_map.get(key)
        if idx is not None:
            self._stack.setCurrentIndex(idx)
        self._update_statusbar()

    def open_account_month(self, account_id: int, month: int, year: int):
        """Called from AnnualWidget drill-down: open register filtered to month/year."""
        self._open_account(account_id)
        rw = self._register_widgets.get(account_id)
        if rw:
            import calendar
            from PyQt6.QtCore import QDate
            last_day = calendar.monthrange(year, month)[1]
            rw._from_date.setDate(QDate(year, month, 1))
            rw._to_date.setDate(QDate(year, month, last_day))
            rw._month_bar.show()
            rw._set_month_pill(month)
            rw.refresh()

    # -------------------------------------------------------------------------
    # Status bar
    # -------------------------------------------------------------------------

    def _update_statusbar(self):
        db_path = self.db.db_path
        truncated = db_path if len(db_path) < 60 else "…" + db_path[-57:]
        name = self.user.get('display_name', self.user.get('username', 'Unknown'))
        self._status.showMessage(f"  Database: {truncated}    |    Logged in as: {name}")

    def show_status_message(self, msg: str, timeout: int = 5000):
        self._status.showMessage(msg, timeout)

    # -------------------------------------------------------------------------
    # Logout
    # -------------------------------------------------------------------------

    def _confirm_logout(self):
        reply = QMessageBox.question(
            self, "Log Out",
            "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    def _on_db_changed(self, new_path: str):
        self.show_status_message(f"Database path updated. Restart to apply: {new_path}")

    def _on_user_updated(self):
        updated = self.db.get_user_by_id(self.user['id'])
        if updated:
            self.user = dict(updated)
        self._user_btn.setText(f"\U0001F464  {self.user.get('display_name', 'User')}")
        self._update_statusbar()
