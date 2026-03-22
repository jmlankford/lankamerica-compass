"""
settings_widget.py — Settings panel
"""
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFormLayout, QFileDialog, QMessageBox,
    QColorDialog, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from src.database import Database
from src.auth import hash_password, verify_password
from src.utils import get_sync_provider, format_currency, save_config
from src.ui.styles import COLOR_NAVY, COLOR_WHITE, COLOR_BORDER, COLOR_ORANGE


class SettingsWidget(QWidget):
    database_changed = pyqtSignal(str)   # new db path
    user_updated = pyqtSignal()

    def __init__(self, db: Database, user: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(0)

        title = QLabel("Settings")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 10, 8, 10)
        layout.setSpacing(14)

        # ── Database Location ──
        db_group = QGroupBox("Database Location")
        db_lay = QVBoxLayout(db_group)
        db_lay.setSpacing(8)

        self._db_path_lbl = QLineEdit(self.db.db_path)
        self._db_path_lbl.setReadOnly(True)
        db_lay.addWidget(self._db_path_lbl)

        db_btn_row = QHBoxLayout()
        browse_btn = QPushButton("Browse / Move Database…")
        browse_btn.setProperty("secondary", True)
        browse_btn.clicked.connect(self._browse_db)
        db_btn_row.addWidget(browse_btn)
        db_btn_row.addStretch()
        db_lay.addLayout(db_btn_row)

        sync_provider = get_sync_provider(self.db.db_path)
        sync_lbl = QLabel(f"Sync Provider: {sync_provider}")
        if sync_provider == "Local":
            sync_lbl.setStyleSheet("color: #888; font-size: 11px; border: none;")
        else:
            sync_lbl.setStyleSheet(f"color: #2E7D32; font-size: 11px; font-weight: 600; border: none;")
        db_lay.addWidget(sync_lbl)
        self._sync_lbl = sync_lbl

        hint = QLabel(
            "For cloud sync, place your .db file in your OneDrive, Google Drive, "
            "Dropbox, or Nextcloud folder."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px; font-style: italic; border: none;")
        db_lay.addWidget(hint)
        layout.addWidget(db_group)

        # ── Profile ──
        profile_group = QGroupBox("Profile")
        profile_lay = QFormLayout(profile_group)
        profile_lay.setSpacing(10)

        self._display_name_edit = QLineEdit(self.user.get('display_name', ''))
        profile_lay.addRow("Display Name:", self._display_name_edit)

        username_lbl = QLineEdit(self.user.get('username', ''))
        username_lbl.setReadOnly(True)
        profile_lay.addRow("Username:", username_lbl)

        # Color picker
        color_row = QHBoxLayout()
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 32)
        user_color = self.user.get('color', '#1565C0')
        self._color_btn.setStyleSheet(
            f"background-color: {user_color}; border-radius: 16px; border: 2px solid #C5D5E8;"
        )
        self._color_btn.clicked.connect(self._pick_color)
        self._current_color = user_color
        color_row.addWidget(self._color_btn)
        color_row.addWidget(QLabel("Click to change your color"))
        color_row.addStretch()
        profile_lay.addRow("User Color:", color_row)

        save_profile_btn = QPushButton("Save Profile")
        save_profile_btn.clicked.connect(self._save_profile)
        profile_lay.addRow("", save_profile_btn)

        self._profile_msg = QLabel("")
        self._profile_msg.setWordWrap(True)
        profile_lay.addRow("", self._profile_msg)

        # Change password
        pw_frame = QFrame()
        pw_frame.setStyleSheet(
            f"background-color: #f8fafd; border: 1px solid {COLOR_BORDER}; border-radius: 6px;"
        )
        pw_lay = QFormLayout(pw_frame)
        pw_lay.setContentsMargins(12, 10, 12, 10)
        pw_lay.setSpacing(8)

        pw_title = QLabel("Change Password")
        pw_title.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 600; border: none;")
        pw_lay.addRow(pw_title)

        self._cur_pw = QLineEdit()
        self._cur_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._cur_pw.setPlaceholderText("Current password")
        pw_lay.addRow("Current:", self._cur_pw)

        self._new_pw = QLineEdit()
        self._new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw.setPlaceholderText("New password (min 6 chars)")
        pw_lay.addRow("New:", self._new_pw)

        self._confirm_pw = QLineEdit()
        self._confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_pw.setPlaceholderText("Confirm new password")
        pw_lay.addRow("Confirm:", self._confirm_pw)

        change_pw_btn = QPushButton("Change Password")
        change_pw_btn.clicked.connect(self._change_password)
        pw_lay.addRow("", change_pw_btn)

        self._pw_msg = QLabel("")
        self._pw_msg.setWordWrap(True)
        pw_lay.addRow("", self._pw_msg)

        profile_lay.addRow(pw_frame)
        layout.addWidget(profile_group)

        # ── Appearance ──
        appear_group = QGroupBox("Appearance")
        appear_lay = QVBoxLayout(appear_group)
        soon_lbl = QLabel("More themes coming soon…")
        soon_lbl.setStyleSheet("color: #aaa; font-style: italic; border: none;")
        appear_lay.addWidget(soon_lbl)
        layout.addWidget(appear_group)

        # ── Data ──
        data_group = QGroupBox("Data")
        data_lay = QHBoxLayout(data_group)
        data_lay.setSpacing(10)

        export_btn = QPushButton("Export All Data to CSV")
        export_btn.setProperty("accent", True)
        export_btn.clicked.connect(self._export_all)
        data_lay.addWidget(export_btn)

        backup_btn = QPushButton("Backup Database")
        backup_btn.setProperty("secondary", True)
        backup_btn.clicked.connect(self._backup_db)
        data_lay.addWidget(backup_btn)

        data_lay.addStretch()
        layout.addWidget(data_group)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def refresh(self, user: dict = None):
        if user:
            self.user = user
        self._display_name_edit.setText(self.user.get('display_name', ''))
        color = self.user.get('color', '#1565C0')
        self._current_color = color
        self._color_btn.setStyleSheet(
            f"background-color: {color}; border-radius: 16px; border: 2px solid #C5D5E8;"
        )
        self._db_path_lbl.setText(self.db.db_path)
        provider = get_sync_provider(self.db.db_path)
        self._sync_lbl.setText(f"Sync Provider: {provider}")
        if provider == "Local":
            self._sync_lbl.setStyleSheet("color: #888; font-size: 11px; border: none;")
        else:
            self._sync_lbl.setStyleSheet("color: #2E7D32; font-size: 11px; font-weight: 600; border: none;")

    def _browse_db(self):
        current = self.db.db_path
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Database Location",
            current,
            "SQLite Database (*.db);;All Files (*)"
        )
        if not path:
            return
        if not path.endswith('.db'):
            path += '.db'
        if path == current:
            return

        reply = QMessageBox.question(
            self, "Move Database",
            f"Copy database to new location?\n\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            shutil.copy2(current, path)
            self._db_path_lbl.setText(path)
            save_config({'db_path': path})
            provider = get_sync_provider(path)
            self._sync_lbl.setText(f"Sync Provider: {provider}")
            self.database_changed.emit(path)
            QMessageBox.information(
                self, "Database Moved",
                f"Database copied to:\n{path}\n\nRestart the app to use the new location."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to copy database:\n{e}")

    def _pick_color(self):
        from PyQt6.QtWidgets import QDialog
        dlg = QColorDialog(QColor(self._current_color), self)
        dlg.setWindowTitle("Choose User Color")
        dlg.setStyleSheet(
            "QPushButton { background-color: #0D2B5C; color: #FFFFFF; border: none; "
            "border-radius: 4px; padding: 6px 16px; font-size: 12px; font-weight: 600; min-height: 28px; }"
            "QPushButton:hover { background-color: #1565C0; }"
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            color = dlg.selectedColor()
            if color.isValid():
                self._current_color = color.name()
                self._color_btn.setStyleSheet(
                    f"background-color: {self._current_color}; border-radius: 16px; border: 2px solid #C5D5E8;"
                )

    def _save_profile(self):
        self._profile_msg.setText("")
        name = self._display_name_edit.text().strip()
        if not name:
            self._profile_msg.setStyleSheet("color: #C62828;")
            self._profile_msg.setText("Display name cannot be empty.")
            return
        try:
            self.db.update_user(self.user['id'], display_name=name, color=self._current_color)
            updated = self.db.get_user_by_id(self.user['id'])
            if updated:
                self.user = dict(updated)
            self._profile_msg.setStyleSheet("color: #2E7D32; font-size: 11px; border: none;")
            self._profile_msg.setText("Profile saved.")
            self.user_updated.emit()
        except Exception as e:
            self._profile_msg.setStyleSheet("color: #C62828; border: none;")
            self._profile_msg.setText(f"Error: {e}")

    def _change_password(self):
        self._pw_msg.setText("")
        cur = self._cur_pw.text()
        new = self._new_pw.text()
        confirm = self._confirm_pw.text()

        if not cur or not new or not confirm:
            self._pw_msg.setStyleSheet("color: #C62828; border: none;")
            self._pw_msg.setText("All password fields are required.")
            return
        if len(new) < 6:
            self._pw_msg.setStyleSheet("color: #C62828; border: none;")
            self._pw_msg.setText("New password must be at least 6 characters.")
            return
        if new != confirm:
            self._pw_msg.setStyleSheet("color: #C62828; border: none;")
            self._pw_msg.setText("New passwords do not match.")
            return

        user_data = self.db.get_user_by_id(self.user['id'])
        if not user_data or not verify_password(cur, user_data['password_hash']):
            self._pw_msg.setStyleSheet("color: #C62828; border: none;")
            self._pw_msg.setText("Current password is incorrect.")
            return

        try:
            new_hash = hash_password(new)
            self.db.update_user_password(self.user['id'], new_hash)
            self._cur_pw.clear()
            self._new_pw.clear()
            self._confirm_pw.clear()
            self._pw_msg.setStyleSheet("color: #2E7D32; font-size: 11px; border: none;")
            self._pw_msg.setText("Password changed successfully.")
        except Exception as e:
            self._pw_msg.setStyleSheet("color: #C62828; border: none;")
            self._pw_msg.setText(f"Error: {e}")

    def _export_all(self):
        from src.ui.export_dialog import ExportDialog
        dlg = ExportDialog(self, db=self.db, user_id=self.user['id'])
        dlg.exec()

    def _backup_db(self):
        src = self.db.db_path
        dest, _ = QFileDialog.getSaveFileName(
            self, "Backup Database",
            str(Path(src).parent / (Path(src).stem + "_backup.db")),
            "SQLite Database (*.db);;All Files (*)"
        )
        if not dest:
            return
        try:
            shutil.copy2(src, dest)
            QMessageBox.information(self, "Backup Complete", f"Database backed up to:\n{dest}")
        except Exception as e:
            QMessageBox.warning(self, "Backup Error", f"Failed to backup:\n{e}")
