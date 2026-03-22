"""
accounts_widget.py — Account add/edit dialog
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDoubleSpinBox, QTextEdit, QPushButton,
    QCheckBox, QGroupBox, QFormLayout, QFrame, QScrollArea,
    QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.database import Database


ACCOUNT_TYPES = ["Checking", "Savings", "Credit Card", "Cash", "Investment", "Other"]


class AccountDialog(QDialog):
    def __init__(self, parent=None, db: Database = None, current_user_id: int = None,
                 account: dict = None):
        super().__init__(parent)
        self.db = db
        self.current_user_id = current_user_id
        self.account = account  # None for new account
        self._result = None

        title = "Edit Account" if account else "Add New Account"
        self.setWindowTitle(title)
        self.setFixedSize(460, 520)
        self.setModal(True)

        self._build_ui()
        if account:
            self._populate(account)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Account" if self.account else "New Account")
        title.setProperty("heading", True)
        title.setStyleSheet("color: #0D2B5C; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        # Name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Chase Checking")
        form.addRow("Account Name *", self._name_edit)

        # Type
        self._type_combo = QComboBox()
        self._type_combo.addItems(ACCOUNT_TYPES)
        form.addRow("Account Type *", self._type_combo)

        # Opening balance
        self._balance_spin = QDoubleSpinBox()
        self._balance_spin.setPrefix("$ ")
        self._balance_spin.setRange(-9_999_999.99, 9_999_999.99)
        self._balance_spin.setDecimals(2)
        self._balance_spin.setValue(0.0)
        self._balance_spin.setGroupSeparatorShown(True)
        form.addRow("Opening Balance", self._balance_spin)

        # Notes
        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("Optional notes…")
        self._notes_edit.setMaximumHeight(80)
        form.addRow("Notes", self._notes_edit)

        layout.addLayout(form)

        # Share with users
        if self.db:
            all_users = self.db.get_all_users()
            other_users = [u for u in all_users if u['id'] != self.current_user_id]
            if other_users:
                share_group = QGroupBox("Share with Users")
                share_layout = QVBoxLayout(share_group)
                self._share_checks = {}
                for u in other_users:
                    cb = QCheckBox(u['display_name'] + f"  ({u['username']})")
                    share_layout.addWidget(cb)
                    self._share_checks[u['id']] = cb

                # Pre-check already shared users
                if self.account:
                    shared = self.db.get_account_shared_users(self.account['id'])
                    for uid, cb in self._share_checks.items():
                        cb.setChecked(uid in shared)

                layout.addWidget(share_group)
            else:
                self._share_checks = {}
        else:
            self._share_checks = {}

        # Error
        self._error_label = QLabel("")
        self._error_label.setProperty("error", True)
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._error_label)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Account")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _populate(self, account: dict):
        self._name_edit.setText(account.get('name', ''))
        idx = ACCOUNT_TYPES.index(account.get('type', 'Checking')) if account.get('type') in ACCOUNT_TYPES else 0
        self._type_combo.setCurrentIndex(idx)
        self._balance_spin.setValue(account.get('opening_balance', 0.0))
        self._notes_edit.setPlainText(account.get('notes', '') or '')

    def _save(self):
        name = self._name_edit.text().strip()
        if not name:
            self._error_label.setText("Account name is required.")
            self._error_label.show()
            return

        self._result = {
            'name': name,
            'type': self._type_combo.currentText(),
            'opening_balance': self._balance_spin.value(),
            'notes': self._notes_edit.toPlainText().strip(),
            'shared_user_ids': [uid for uid, cb in self._share_checks.items() if cb.isChecked()]
        }
        self.accept()

    def get_result(self) -> dict:
        return self._result
