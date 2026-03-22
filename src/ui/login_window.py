"""
login_window.py — Login / Register window for LankAmerica Compass
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QFrame, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont
from pathlib import Path
from src.database import Database
from src.auth import create_user, authenticate
from src.utils import get_db_default_path, load_config, save_config, get_assets_dir


class LoginWindow(QWidget):
    login_success = pyqtSignal(dict, str)  # user_dict, db_path

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LankAmerica Compass — Sign In")
        self.setFixedSize(440, 600)
        self.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint)

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.geometry()
            self.move(sg.center().x() - 220, sg.center().y() - 300)

        # Load saved db path
        cfg = load_config()
        self._db_path = cfg.get('db_path', get_db_default_path())

        self._db: Database = None
        self._init_db()
        self._build_ui()

    def _init_db(self):
        try:
            self._db = Database(self._db_path)
        except Exception as e:
            self._db = None

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 24, 30, 24)
        main_layout.setSpacing(12)

        # Logo / header
        logo_label = self._make_logo()
        main_layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        # App name fallback text
        name_label = QLabel("LankAmerica Compass")
        name_label.setProperty("heading", True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #0D2B5C;")
        main_layout.addWidget(name_label)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._login_tab = QWidget()
        self._register_tab = QWidget()
        self._build_login_tab()
        self._build_register_tab()

        self._tabs.addTab(self._login_tab, "Sign In")
        self._tabs.addTab(self._register_tab, "Create Account")
        main_layout.addWidget(self._tabs)

        # DB file row
        db_frame = QFrame()
        db_frame.setStyleSheet(
            "background-color: #EEF4FB; border: 1px solid #C5D5E8; border-radius: 6px;"
        )
        db_layout = QVBoxLayout(db_frame)
        db_layout.setContentsMargins(10, 8, 10, 8)
        db_layout.setSpacing(4)

        db_title = QLabel("Database File")
        db_title.setStyleSheet("color: #0D2B5C; font-weight: 600; font-size: 11px; border: none;")
        db_layout.addWidget(db_title)

        db_row = QHBoxLayout()
        db_row.setSpacing(6)
        self._db_path_edit = QLineEdit(self._db_path)
        self._db_path_edit.setReadOnly(True)
        self._db_path_edit.setStyleSheet(
            "background-color: white; border: 1px solid #C5D5E8; "
            "border-radius: 4px; padding: 4px 7px; font-size: 11px; color: #444;"
        )
        self._db_path_edit.setToolTip(self._db_path)
        db_row.addWidget(self._db_path_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(76)
        browse_btn.setStyleSheet(
            "background-color: #0D2B5C; color: white; border-radius: 4px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 600; min-height: 0;"
        )
        browse_btn.clicked.connect(self._browse_db)
        db_row.addWidget(browse_btn)
        db_layout.addLayout(db_row)

        main_layout.addWidget(db_frame)

    def _make_logo(self) -> QLabel:
        lbl = QLabel()
        assets = get_assets_dir()
        logo_path = assets / "logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                pix = pix.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(pix)
                lbl.setFixedHeight(pix.height())
                return lbl
        lbl.setText("")
        lbl.setFixedHeight(4)
        return lbl

    def _build_login_tab(self):
        layout = QVBoxLayout(self._login_tab)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(10)

        # Username
        layout.addWidget(QLabel("Username"))
        self._login_username = QLineEdit()
        self._login_username.setPlaceholderText("Enter username")
        layout.addWidget(self._login_username)

        # Password
        layout.addWidget(QLabel("Password"))
        self._login_password = QLineEdit()
        self._login_password.setPlaceholderText("Enter password")
        self._login_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self._login_password)

        # Error label
        self._login_error = QLabel("")
        self._login_error.setProperty("error", True)
        self._login_error.setWordWrap(True)
        self._login_error.hide()
        layout.addWidget(self._login_error)

        layout.addStretch()

        # Login button
        login_btn = QPushButton("Sign In")
        login_btn.setMinimumHeight(38)
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)

        # Enter key support
        self._login_password.returnPressed.connect(self._do_login)
        self._login_username.returnPressed.connect(self._login_password.setFocus)

    def _build_register_tab(self):
        layout = QVBoxLayout(self._register_tab)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Display Name"))
        self._reg_display = QLineEdit()
        self._reg_display.setPlaceholderText("Your full name")
        layout.addWidget(self._reg_display)

        layout.addWidget(QLabel("Username"))
        self._reg_username = QLineEdit()
        self._reg_username.setPlaceholderText("Choose a username")
        layout.addWidget(self._reg_username)

        layout.addWidget(QLabel("Password"))
        self._reg_password = QLineEdit()
        self._reg_password.setPlaceholderText("Choose a password")
        self._reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self._reg_password)

        layout.addWidget(QLabel("Confirm Password"))
        self._reg_confirm = QLineEdit()
        self._reg_confirm.setPlaceholderText("Confirm password")
        self._reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self._reg_confirm)

        self._reg_error = QLabel("")
        self._reg_error.setProperty("error", True)
        self._reg_error.setWordWrap(True)
        self._reg_error.hide()
        layout.addWidget(self._reg_error)

        layout.addStretch()

        reg_btn = QPushButton("Create Account")
        reg_btn.setMinimumHeight(38)
        reg_btn.clicked.connect(self._do_register)
        layout.addWidget(reg_btn)

        self._reg_confirm.returnPressed.connect(self._do_register)

    def _browse_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Select or Create Database File",
            self._db_path,
            "SQLite Database (*.db);;All Files (*)"
        )
        if path:
            if not path.endswith('.db'):
                path += '.db'
            self._db_path = path
            self._db_path_edit.setText(path)
            self._db_path_edit.setToolTip(path)
            self._init_db()
            save_config({'db_path': path})

    def _show_login_error(self, msg: str):
        self._login_error.setText(msg)
        self._login_error.show()

    def _show_reg_error(self, msg: str):
        self._reg_error.setText(msg)
        self._reg_error.show()

    def _do_login(self):
        self._login_error.hide()
        username = self._login_username.text().strip()
        password = self._login_password.text()

        if not username:
            self._show_login_error("Please enter your username.")
            return
        if not password:
            self._show_login_error("Please enter your password.")
            return
        if self._db is None:
            self._show_login_error("Database is not accessible. Check the path above.")
            return

        user = authenticate(self._db, username, password)
        if user is None:
            self._show_login_error("Invalid username or password.")
            return

        save_config({'db_path': self._db_path})
        self.login_success.emit(user, self._db_path)

    def _do_register(self):
        self._reg_error.hide()
        display = self._reg_display.text().strip()
        username = self._reg_username.text().strip()
        password = self._reg_password.text()
        confirm = self._reg_confirm.text()

        if not display:
            self._show_reg_error("Please enter your display name.")
            return
        if not username:
            self._show_reg_error("Please enter a username.")
            return
        if len(username) < 3:
            self._show_reg_error("Username must be at least 3 characters.")
            return
        if not password:
            self._show_reg_error("Please enter a password.")
            return
        if len(password) < 6:
            self._show_reg_error("Password must be at least 6 characters.")
            return
        if password != confirm:
            self._show_reg_error("Passwords do not match.")
            return
        if self._db is None:
            self._show_reg_error("Database is not accessible. Check the path above.")
            return

        try:
            user_id = create_user(self._db, username, password, display)
            user = self._db.get_user_by_id(user_id)
            save_config({'db_path': self._db_path})
            self.login_success.emit(dict(user), self._db_path)
        except ValueError as e:
            self._show_reg_error(str(e))
        except Exception as e:
            self._show_reg_error(f"Error: {e}")
