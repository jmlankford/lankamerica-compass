"""
transaction_dialog.py — Add/Edit transaction modal dialog
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QCheckBox,
    QPushButton, QButtonGroup, QRadioButton, QFrame
)
from PyQt6.QtCore import Qt, QDate
from src.database import Database


TRANSACTION_TYPES = [
    "CHECK", "DEBIT CARD", "ATM", "ACH/ELECTRONIC", "DIRECT DEPOSIT",
    "ONLINE TRANSFER", "WIRE TRANSFER", "FEE/CHARGE", "INTEREST",
    "DEPOSIT", "MOBILE DEPOSIT", "ZELLE/VENMO/P2P", "OTHER"
]


class TransactionDialog(QDialog):
    def __init__(self, parent=None, db: Database = None,
                 account_id: int = None, user_id: int = None,
                 transaction: dict = None):
        super().__init__(parent)
        self.db = db
        self.account_id = account_id
        self.user_id = user_id
        self.transaction = transaction
        self._result = None

        title = "Edit Transaction" if transaction else "Add Transaction"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMaximumWidth(560)
        self.setModal(True)

        self._build_ui()
        if transaction:
            self._populate(transaction)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_lbl = QLabel("Edit Transaction" if self.transaction else "New Transaction")
        title_lbl.setStyleSheet("color: #0D2B5C; font-size: 18px; font-weight: 700;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        # Date
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.currentDate())
        self._date_edit.setDisplayFormat("MM/dd/yyyy")
        form.addRow("Date *", self._date_edit)

        # Type
        self._type_combo = QComboBox()
        self._type_combo.addItems(TRANSACTION_TYPES)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type *", self._type_combo)

        # Check number
        self._check_edit = QLineEdit()
        self._check_edit.setPlaceholderText("Check number")
        form.addRow("Check #", self._check_edit)
        # Apply initial enabled state based on default type selection
        self._on_type_changed(self._type_combo.currentText())

        # Description
        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText("Payee / description")
        form.addRow("Description", self._desc_edit)

        # Memo
        self._memo_edit = QLineEdit()
        self._memo_edit.setPlaceholderText("Optional note")
        form.addRow("Memo", self._memo_edit)

        # Category
        self._cat_combo = QComboBox()
        self._populate_categories()
        form.addRow("Category", self._cat_combo)

        layout.addLayout(form)

        # Amount direction
        dir_frame = QFrame()
        dir_frame.setStyleSheet(
            "background-color: #EEF4FB; border: 1px solid #C5D5E8; border-radius: 6px;"
        )
        dir_layout = QHBoxLayout(dir_frame)
        dir_layout.setContentsMargins(12, 8, 12, 8)

        self._debit_radio = QRadioButton("Debit (Money Out)")
        self._debit_radio.setChecked(True)
        self._debit_radio.setStyleSheet("color: #C62828; font-weight: 600;")
        self._credit_radio = QRadioButton("Credit (Money In)")
        self._credit_radio.setStyleSheet("color: #2E7D32; font-weight: 600;")

        self._dir_group = QButtonGroup(self)
        self._dir_group.addButton(self._debit_radio, 0)
        self._dir_group.addButton(self._credit_radio, 1)

        dir_layout.addWidget(QLabel("Direction:"))
        dir_layout.addWidget(self._debit_radio)
        dir_layout.addWidget(self._credit_radio)
        dir_layout.addStretch()
        layout.addWidget(dir_frame)

        # Amount
        form2 = QFormLayout()
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setPrefix("$ ")
        self._amount_spin.setRange(0.01, 9_999_999.99)
        self._amount_spin.setDecimals(2)
        self._amount_spin.setValue(0.00)
        self._amount_spin.setGroupSeparatorShown(True)
        form2.addRow("Amount *", self._amount_spin)
        layout.addLayout(form2)

        # Reconciled
        self._reconciled_cb = QCheckBox("Mark as Reconciled")
        layout.addWidget(self._reconciled_cb)

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
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #0D2B5C; "
            "border: 2px solid #0D2B5C; border-radius: 5px; padding: 7px 18px; "
            "font-size: 13px; font-weight: 600; min-height: 32px; }"
            "QPushButton:hover { background-color: #EEF4FB; border-color: #1565C0; color: #1565C0; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Transaction")
        save_btn.setStyleSheet(
            "QPushButton { background-color: #0D2B5C; color: #FFFFFF; "
            "border: none; border-radius: 5px; padding: 7px 18px; "
            "font-size: 13px; font-weight: 600; min-height: 32px; }"
            "QPushButton:hover { background-color: #1565C0; }"
            "QPushButton:pressed { background-color: #0a2048; }"
        )
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _populate_categories(self):
        self._cat_combo.clear()
        self._cat_id_map = {}  # index -> category_id (None for separators)

        if not self.db:
            return

        cats = self.db.get_all_categories()
        income_cats = [c for c in cats if c['category_type'] == 'income']
        expense_cats = [c for c in cats if c['category_type'] == 'expense']

        # Blank option
        self._cat_combo.addItem("— No Category —")
        self._cat_id_map[0] = None

        # Income separator
        sep_idx = self._cat_combo.count()
        self._cat_combo.addItem("── INCOME ──")
        item_model = self._cat_combo.model()
        item_model.item(sep_idx).setEnabled(False)
        self._cat_id_map[sep_idx] = None

        for cat in income_cats:
            idx = self._cat_combo.count()
            self._cat_combo.addItem("  " + cat['name'])
            self._cat_id_map[idx] = cat['id']

        # Expense separator
        sep_idx2 = self._cat_combo.count()
        self._cat_combo.addItem("── EXPENSE ──")
        item_model.item(sep_idx2).setEnabled(False)
        self._cat_id_map[sep_idx2] = None

        for cat in expense_cats:
            idx = self._cat_combo.count()
            self._cat_combo.addItem("  " + cat['name'])
            self._cat_id_map[idx] = cat['id']

    def get_selected_category_id(self) -> int:
        idx = self._cat_combo.currentIndex()
        return self._cat_id_map.get(idx, None)

    def set_category_by_id(self, cat_id: int):
        for idx, cid in self._cat_id_map.items():
            if cid == cat_id:
                self._cat_combo.setCurrentIndex(idx)
                return

    def _on_type_changed(self, text: str):
        self._check_edit.setEnabled(text == "CHECK")
        if text != "CHECK":
            self._check_edit.clear()

    def _populate(self, t: dict):
        if t.get('date'):
            parts = t['date'].split('-')
            if len(parts) == 3:
                self._date_edit.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))

        idx = TRANSACTION_TYPES.index(t['type']) if t.get('type') in TRANSACTION_TYPES else 0
        self._type_combo.setCurrentIndex(idx)
        self._check_edit.setText(t.get('check_number') or '')
        self._desc_edit.setText(t.get('description') or '')
        self._memo_edit.setText(t.get('memo') or '')

        if t.get('category_id'):
            self.set_category_by_id(t['category_id'])

        if t.get('credit', 0) > 0:
            self._credit_radio.setChecked(True)
            self._amount_spin.setValue(t['credit'])
        else:
            self._debit_radio.setChecked(True)
            self._amount_spin.setValue(t.get('debit', 0.0))

        self._reconciled_cb.setChecked(bool(t.get('reconciled', 0)))

    def _save(self):
        self._error_label.hide()

        date = self._date_edit.date().toString("yyyy-MM-dd")
        amount = self._amount_spin.value()

        if amount <= 0:
            self._error_label.setText("Amount must be greater than $0.00")
            self._error_label.show()
            return

        is_debit = self._debit_radio.isChecked()
        debit = amount if is_debit else 0.0
        credit = amount if not is_debit else 0.0

        self._result = {
            'date': date,
            'type': self._type_combo.currentText(),
            'check_number': self._check_edit.text().strip() or None,
            'description': self._desc_edit.text().strip(),
            'memo': self._memo_edit.text().strip(),
            'category_id': self.get_selected_category_id(),
            'reconciled': 1 if self._reconciled_cb.isChecked() else 0,
            'debit': debit,
            'credit': credit,
        }
        self.accept()

    def get_result(self) -> dict:
        return self._result
