"""
budget_widget.py — Budget management widget
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QFormLayout, QDoubleSpinBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush, QFont

from src.database import Database
from src.utils import format_currency
from src.ui.styles import (
    COLOR_NAVY, COLOR_WHITE, COLOR_BORDER, COLOR_RED, COLOR_GREEN,
    COLOR_LIGHT_BG
)

import calendar
from datetime import date as _date

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


class BudgetWidget(QWidget):
    def __init__(self, db: Database, user_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self._current_year = _date.today().year
        self._current_month = _date.today().month
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title = QLabel("Budgets")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        # Controls
        ctrl_frame = QFrame()
        ctrl_frame.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;"
        )
        ctrl_row = QHBoxLayout(ctrl_frame)
        ctrl_row.setContentsMargins(12, 8, 12, 8)
        ctrl_row.setSpacing(10)

        ctrl_row.addWidget(QLabel("Month:"))
        self._month_combo = QComboBox()
        self._month_combo.addItems(MONTH_NAMES)
        self._month_combo.setCurrentIndex(self._current_month - 1)
        self._month_combo.currentIndexChanged.connect(self._on_month_changed)
        ctrl_row.addWidget(self._month_combo)

        ctrl_row.addWidget(QLabel("Year:"))
        self._year_combo = QComboBox()
        today_year = _date.today().year
        for y in range(today_year - 5, today_year + 3):
            self._year_combo.addItem(str(y))
        self._year_combo.setCurrentText(str(today_year))
        self._year_combo.currentTextChanged.connect(self._on_year_changed)
        ctrl_row.addWidget(self._year_combo)

        ctrl_row.addStretch()

        hint = QLabel("Double-click a row to set or edit a budget amount.")
        hint.setStyleSheet("color: #888; font-size: 11px; border: none;")
        ctrl_row.addWidget(hint)

        layout.addWidget(ctrl_frame)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Category", "Type", "Monthly Budget",
            "This Month Actual", "Difference", "Status"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._edit_budget)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(1, 90)
        self._table.setColumnWidth(2, 130)
        self._table.setColumnWidth(3, 140)
        self._table.setColumnWidth(4, 110)
        self._table.setColumnWidth(5, 150)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

    def _on_month_changed(self, idx: int):
        self._current_month = idx + 1
        self.refresh()

    def _on_year_changed(self, text: str):
        try:
            self._current_year = int(text)
        except ValueError:
            pass
        self.refresh()

    def refresh(self):
        cats = self.db.get_all_categories()
        accounts = self.db.get_accounts_for_user(self.user_id)
        account_ids = [a['id'] for a in accounts]
        actuals = self.db.get_monthly_actual_by_category(
            account_ids, self._current_year, self._current_month
        )
        budgets_list = self.db.get_budgets_for_user(self.user_id)
        budget_map = {b['category_id']: b['monthly_amount'] for b in budgets_list}

        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        self._table.setUpdatesEnabled(False)
        self._table.setRowCount(len(cats))

        for row_idx, cat in enumerate(cats):
            cat_id = cat['id']
            cat_type = cat['category_type']

            debit_actual, credit_actual = actuals.get(cat_id, (0.0, 0.0))
            # For expenses: actual = debits; for income: actual = credits
            if cat_type == 'expense':
                actual = debit_actual
            else:
                actual = credit_actual

            budget_amt = budget_map.get(cat_id, None)

            def make_item(text, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(int(align))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return item

            self._table.setItem(row_idx, 0, make_item(cat['name']))
            type_item = make_item(cat_type.capitalize(), Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if cat_type == 'income':
                type_item.setForeground(QBrush(QColor(COLOR_GREEN)))
            else:
                type_item.setForeground(QBrush(QColor(COLOR_RED)))
            self._table.setItem(row_idx, 1, type_item)

            if budget_amt is not None:
                self._table.setItem(row_idx, 2, make_item(format_currency(budget_amt), right))
            else:
                no_item = make_item("— Not set", Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                no_item.setForeground(QBrush(QColor("#aaa")))
                self._table.setItem(row_idx, 2, no_item)

            actual_item = make_item(format_currency(actual), right)
            self._table.setItem(row_idx, 3, actual_item)

            # Difference and status
            if budget_amt is not None:
                diff = budget_amt - actual
                diff_item = make_item(format_currency(diff), right)

                if cat_type == 'expense':
                    if diff >= 0:
                        status_text = "✓ Under Budget"
                        status_color = "#1A1A2E"
                        diff_item.setForeground(QBrush(QColor(COLOR_GREEN)))
                    else:
                        status_text = "⚠ Over Budget"
                        status_color = COLOR_RED
                        diff_item.setForeground(QBrush(QColor(COLOR_RED)))
                else:
                    if actual >= budget_amt:
                        status_text = "✓ Above Target"
                        status_color = COLOR_GREEN
                        diff_item.setForeground(QBrush(QColor(COLOR_GREEN)))
                    else:
                        status_text = "✓ On Track"
                        status_color = "#1A1A2E"
                        diff_item.setForeground(QBrush(QColor("#555")))

                self._table.setItem(row_idx, 4, diff_item)
                status_item = make_item(status_text, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                status_item.setForeground(QBrush(QColor(status_color)))
                self._table.setItem(row_idx, 5, status_item)
            else:
                self._table.setItem(row_idx, 4, make_item(""))
                no_bud = make_item("— No Budget", Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                no_bud.setForeground(QBrush(QColor("#aaa")))
                font = no_bud.font()
                font.setItalic(True)
                no_bud.setFont(font)
                self._table.setItem(row_idx, 5, no_bud)

            # Store category id in row
            self._table.item(row_idx, 0).setData(Qt.ItemDataRole.UserRole, cat_id)

        self._table.setUpdatesEnabled(True)

    def _edit_budget(self):
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if not item:
            return
        cat_id = item.data(Qt.ItemDataRole.UserRole)
        cat_name = item.text()

        existing = self.db.get_budget(cat_id, self.user_id)
        current_amount = existing['monthly_amount'] if existing else 0.0

        dlg = BudgetEditDialog(self, cat_name, current_amount)
        result = dlg.exec()

        if result == QDialog.DialogCode.Accepted:
            action = dlg.get_action()
            if action == 'save':
                self.db.set_budget(cat_id, self.user_id, dlg.get_amount())
            elif action == 'clear':
                self.db.delete_budget(cat_id, self.user_id)
            self.refresh()


class BudgetEditDialog(QDialog):
    def __init__(self, parent, cat_name: str, current_amount: float):
        super().__init__(parent)
        self.setWindowTitle("Set Budget")
        self.setFixedSize(360, 220)
        self._action = None
        self._amount = 0.0
        self._build_ui(cat_name, current_amount)

    def _build_ui(self, cat_name: str, current: float):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        lbl = QLabel(f"Category: {cat_name}")
        lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 700; font-size: 14px;")
        layout.addWidget(lbl)

        form = QFormLayout()
        self._spin = QDoubleSpinBox()
        self._spin.setPrefix("$ ")
        self._spin.setRange(0.0, 9_999_999.99)
        self._spin.setDecimals(2)
        self._spin.setValue(current)
        self._spin.setGroupSeparatorShown(True)
        form.addRow("Monthly Budget:", self._spin)
        layout.addLayout(form)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        clear_btn = QPushButton("Clear Budget")
        clear_btn.setProperty("secondary", True)
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _save(self):
        self._action = 'save'
        self._amount = self._spin.value()
        self.accept()

    def _clear(self):
        self._action = 'clear'
        self.accept()

    def get_action(self) -> str:
        return self._action

    def get_amount(self) -> float:
        return self._amount
