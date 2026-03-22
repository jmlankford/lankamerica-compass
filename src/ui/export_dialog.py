"""
export_dialog.py — Full-featured export dialog
"""
import csv
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QRadioButton, QButtonGroup, QDateEdit,
    QComboBox, QScrollArea, QWidget, QFileDialog, QGridLayout,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate

from src.database import Database
from src.utils import format_currency
from src.ui.styles import COLOR_NAVY, COLOR_WHITE, COLOR_BORDER

from datetime import date as _date


EXPORT_COLUMNS = [
    ("date",         "Date"),
    ("type",         "Type"),
    ("check_number", "Check #"),
    ("description",  "Description"),
    ("memo",         "Memo"),
    ("category_name","Category"),
    ("cleared",      "Cleared"),
    ("debit",        "Debit"),
    ("credit",       "Credit"),
    ("balance",      "Balance"),
    ("account_name", "Account Name"),
    ("user_name",    "User"),
]

SORT_OPTIONS = [
    ("date_asc",       "Date Ascending"),
    ("date_desc",      "Date Descending"),
    ("description_az", "Description A-Z"),
    ("amount",         "Amount"),
]


class ExportDialog(QDialog):
    def __init__(self, parent=None, db: Database = None, user_id: int = None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.setWindowTitle("Export Transactions")
        self.resize(700, 640)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 14, 16, 14)
        main.setSpacing(10)

        title = QLabel("Export Transactions")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 18px; font-weight: 700;")
        main.addWidget(title)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 8, 0)
        content_lay.setSpacing(10)

        # 1. Accounts
        acct_group = QGroupBox("Accounts")
        acct_lay = QGridLayout(acct_group)
        accounts = self.db.get_accounts_for_user(self.user_id)
        self._account_checks = {}
        all_acct_cb = QCheckBox("All Accounts")
        all_acct_cb.setChecked(True)
        acct_lay.addWidget(all_acct_cb, 0, 0)
        self._all_accts_cb = all_acct_cb
        for i, acc in enumerate(accounts):
            cb = QCheckBox(acc['name'])
            cb.setChecked(True)
            acct_lay.addWidget(cb, (i + 1) // 3 + 1, (i + 1) % 3)
            self._account_checks[acc['id']] = cb
        all_acct_cb.toggled.connect(lambda checked: [cb.setChecked(checked) for cb in self._account_checks.values()])
        content_lay.addWidget(acct_group)

        # 2. Date Range
        date_group = QGroupBox("Date Range")
        date_lay = QVBoxLayout(date_group)
        self._date_all = QRadioButton("All Time")
        self._date_this_month = QRadioButton("This Month")
        self._date_this_year = QRadioButton("This Year")
        self._date_last_year = QRadioButton("Last Year")
        self._date_custom = QRadioButton("Custom Range")
        self._date_all.setChecked(True)

        date_grp = QButtonGroup(self)
        for rb in [self._date_all, self._date_this_month, self._date_this_year,
                   self._date_last_year, self._date_custom]:
            date_grp.addButton(rb)
            date_lay.addWidget(rb)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("  From:"))
        self._custom_from = QDateEdit()
        self._custom_from.setCalendarPopup(True)
        self._custom_from.setDisplayFormat("MM/dd/yyyy")
        self._custom_from.setDate(QDate(QDate.currentDate().year(), 1, 1))
        self._custom_from.setEnabled(False)
        custom_row.addWidget(self._custom_from)
        custom_row.addWidget(QLabel("To:"))
        self._custom_to = QDateEdit()
        self._custom_to.setCalendarPopup(True)
        self._custom_to.setDisplayFormat("MM/dd/yyyy")
        self._custom_to.setDate(QDate.currentDate())
        self._custom_to.setEnabled(False)
        custom_row.addWidget(self._custom_to)
        custom_row.addStretch()
        date_lay.addLayout(custom_row)
        self._date_custom.toggled.connect(lambda c: (self._custom_from.setEnabled(c), self._custom_to.setEnabled(c)))
        content_lay.addWidget(date_group)

        # 3. Transaction Types
        type_group = QGroupBox("Transaction Types")
        type_lay = QGridLayout(type_group)
        from src.ui.transaction_dialog import TRANSACTION_TYPES
        self._type_checks = {}
        all_type_cb = QCheckBox("All Types")
        all_type_cb.setChecked(True)
        type_lay.addWidget(all_type_cb, 0, 0)
        for i, t in enumerate(TRANSACTION_TYPES):
            cb = QCheckBox(t)
            cb.setChecked(True)
            type_lay.addWidget(cb, (i + 1) // 3 + 1, (i + 1) % 3)
            self._type_checks[t] = cb
        all_type_cb.toggled.connect(lambda checked: [cb.setChecked(checked) for cb in self._type_checks.values()])
        content_lay.addWidget(type_group)

        # 4. Categories
        cat_group = QGroupBox("Categories")
        cat_lay = QGridLayout(cat_group)
        cats = self.db.get_all_categories()
        self._cat_checks = {}
        all_cat_cb = QCheckBox("All Categories")
        all_cat_cb.setChecked(True)
        cat_lay.addWidget(all_cat_cb, 0, 0)
        for i, cat in enumerate(cats):
            cb = QCheckBox(cat['name'])
            cb.setChecked(True)
            cat_lay.addWidget(cb, (i + 1) // 3 + 1, (i + 1) % 3)
            self._cat_checks[cat['id']] = cb
        all_cat_cb.toggled.connect(lambda checked: [cb.setChecked(checked) for cb in self._cat_checks.values()])
        content_lay.addWidget(cat_group)

        # 5. Cleared Status
        rec_group = QGroupBox("Cleared Status")
        rec_lay = QHBoxLayout(rec_group)
        self._rec_all = QRadioButton("All")
        self._rec_only = QRadioButton("Cleared Only")
        self._rec_unrec = QRadioButton("Uncleared Only")
        self._rec_all.setChecked(True)
        for rb in [self._rec_all, self._rec_only, self._rec_unrec]:
            rec_lay.addWidget(rb)
        rec_lay.addStretch()
        content_lay.addWidget(rec_group)

        # 6. Columns
        col_group = QGroupBox("Columns to Include")
        col_lay = QGridLayout(col_group)
        self._col_checks = {}
        for i, (key, label) in enumerate(EXPORT_COLUMNS):
            cb = QCheckBox(label)
            cb.setChecked(True)
            col_lay.addWidget(cb, i // 4, i % 4)
            self._col_checks[key] = cb
        content_lay.addWidget(col_group)

        # 7. Sort
        sort_group = QGroupBox("Sort Order")
        sort_lay = QHBoxLayout(sort_group)
        sort_lay.addWidget(QLabel("Sort by:"))
        self._sort_combo = QComboBox()
        for key, label in SORT_OPTIONS:
            self._sort_combo.addItem(label, key)
        sort_lay.addWidget(self._sort_combo)
        sort_lay.addStretch()
        content_lay.addWidget(sort_group)

        scroll.setWidget(content)
        main.addWidget(scroll)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        export_btn = QPushButton("Export CSV")
        export_btn.setProperty("accent", True)
        export_btn.clicked.connect(self._do_export)
        btn_row.addWidget(export_btn)
        main.addLayout(btn_row)

    def _get_date_range(self):
        import calendar as _cal
        today = _date.today()
        if self._date_all.isChecked():
            return "2000-01-01", "2099-12-31"
        elif self._date_this_month.isChecked():
            last_day = _cal.monthrange(today.year, today.month)[1]
            return (f"{today.year}-{today.month:02d}-01",
                    f"{today.year}-{today.month:02d}-{last_day:02d}")
        elif self._date_this_year.isChecked():
            return f"{today.year}-01-01", f"{today.year}-12-31"
        elif self._date_last_year.isChecked():
            y = today.year - 1
            return f"{y}-01-01", f"{y}-12-31"
        else:
            return (self._custom_from.date().toString("yyyy-MM-dd"),
                    self._custom_to.date().toString("yyyy-MM-dd"))

    def _do_export(self):
        # Gather selections
        account_ids = [aid for aid, cb in self._account_checks.items() if cb.isChecked()]
        if not account_ids:
            account_ids = list(self._account_checks.keys())

        start, end = self._get_date_range()

        type_filter = [t for t, cb in self._type_checks.items() if cb.isChecked()]
        if len(type_filter) == len(self._type_checks):
            type_filter = None

        cat_ids = [cid for cid, cb in self._cat_checks.items() if cb.isChecked()]
        if len(cat_ids) == len(self._cat_checks):
            cat_ids = None

        if self._rec_all.isChecked():
            rec_filter = 'all'
        elif self._rec_only.isChecked():
            rec_filter = 'cleared'
        else:
            rec_filter = 'uncleared'

        sort_order = self._sort_combo.currentData()

        cols = [(key, label) for (key, label), cb in
                zip(EXPORT_COLUMNS, self._col_checks.values()) if cb.isChecked()]
        col_keys = [k for k, _ in cols]
        col_labels = [l for _, l in cols]

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Export",
            f"transactions_export.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        # Need running balances per account
        balances_by_account = {}
        for aid in account_ids:
            balances_by_account[aid] = self.db.get_running_balance(aid)

        rows = self.db.get_transactions_for_export(
            account_ids, start, end, type_filter, cat_ids,
            cleared_filter=rec_filter, sort_order=sort_order
        )

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(col_labels)
                for row in rows:
                    aid = row['account_id']
                    tx_id = row['id']
                    bal = balances_by_account.get(aid, {}).get(tx_id, 0.0)
                    row_dict = dict(row)
                    row_dict['balance'] = bal
                    # Format currency fields
                    for k in ('debit', 'credit', 'balance'):
                        if k in row_dict and row_dict[k] is not None:
                            row_dict[k] = f"{row_dict[k]:.2f}"
                    # Format date
                    if 'date' in row_dict and row_dict['date']:
                        try:
                            parts = row_dict['date'].split('-')
                            row_dict['date'] = f"{parts[1]}/{parts[2]}/{parts[0]}"
                        except Exception:
                            pass
                    # Reconciled
                    if 'cleared' in row_dict:
                        row_dict['cleared'] = "Yes" if row_dict['cleared'] else "No"
                    csv_row = [row_dict.get(k, '') for k in col_keys]
                    writer.writerow(csv_row)
            self.accept()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", str(e))
