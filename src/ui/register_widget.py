"""
register_widget.py — Transaction register (main account view)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QComboBox, QDateEdit, QAbstractItemView,
    QMenu, QSizePolicy, QApplication, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QColor, QBrush, QAction

from src.database import Database
from src.utils import format_currency
from src.ui.transaction_dialog import TransactionDialog
from src.ui.csv_import_dialog import CsvImportDialog
from src.ui.styles import (
    COLOR_NAVY, COLOR_ORANGE, COLOR_GREEN, COLOR_RED,
    COLOR_WHITE, COLOR_ALT_ROW, COLOR_RECONCILED_BG,
    COLOR_RECONCILED_TEXT, COLOR_MEDIUM_BLUE, COLOR_BORDER,
    ACCOUNT_TYPE_COLORS
)

import calendar
from datetime import date as _date

COL_DATE = 0
COL_TYPE = 1
COL_CHECK = 2
COL_DESC = 3
COL_MEMO = 4
COL_CAT = 5
COL_REC = 6
COL_DEBIT = 7
COL_CREDIT = 8
COL_BAL = 9

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class RegisterWidget(QWidget):
    navigate_to_account = pyqtSignal(int, str, int)  # account_id, month_filter, year

    def __init__(self, db: Database, account_id: int, user_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.account_id = account_id
        self.user_id = user_id
        self._account = None
        self._all_balances = {}   # transaction_id -> running balance
        self._transactions = []   # current filtered list
        self._month_filter = None  # None = all; int 1-12
        self._sort_col = COL_DATE
        self._sort_order = Qt.SortOrder.DescendingOrder
        self._build_ui()
        self.load_account()
        self.refresh()

    # -------------------------------------------------------------------------
    # Build UI
    # -------------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(8)

        # ── Header ──
        layout.addWidget(self._build_header())

        # ── Filter toolbar ──
        layout.addWidget(self._build_toolbar())

        # ── Month pills (hidden by default) ──
        self._month_bar = self._build_month_bar()
        layout.addWidget(self._month_bar)
        self._month_bar.hide()

        # ── Statement reconciliation panel (hidden by default) ──
        self._rec_panel = self._build_rec_panel()
        layout.addWidget(self._rec_panel)
        self._rec_panel.hide()
        self._rec_target: float = None   # None = no target set
        self._rec_target_date: str = None

        # ── Table ──
        self._table = QTableWidget()
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            "Date", "Type", "Check #", "Description", "Memo",
            "Category", "✓", "Debit", "Credit", "Balance"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._edit_selected)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._table.horizontalHeader().setSortIndicatorShown(True)
        self._table.setShowGrid(True)

        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(COL_DATE, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_DESC, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_MEMO, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_CAT, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_REC, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_DEBIT, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_CREDIT, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_BAL, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(COL_DATE, 96)
        self._table.setColumnWidth(COL_TYPE, 130)
        self._table.setColumnWidth(COL_CHECK, 68)
        self._table.setColumnWidth(COL_CAT, 150)
        self._table.setColumnWidth(COL_REC, 30)
        self._table.setColumnWidth(COL_DEBIT, 100)
        self._table.setColumnWidth(COL_CREDIT, 100)
        self._table.setColumnWidth(COL_BAL, 110)

        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # ── Footer summary ──
        layout.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 8px;"
        )
        hlay = QHBoxLayout(frame)
        hlay.setContentsMargins(16, 12, 16, 12)
        hlay.setSpacing(16)

        # Left: name + type badge
        left = QVBoxLayout()
        left.setSpacing(4)
        self._acct_name_lbl = QLabel("Account")
        self._acct_name_lbl.setStyleSheet(
            f"color: {COLOR_NAVY}; font-size: 22px; font-weight: 700; border: none;"
        )
        left.addWidget(self._acct_name_lbl)
        self._acct_type_badge = QLabel("")
        self._acct_type_badge.setStyleSheet(
            f"border-radius: 10px; padding: 2px 12px; font-size: 11px; "
            f"font-weight: 600; background-color: {COLOR_MEDIUM_BLUE}; "
            f"color: white; border: none;"
        )
        self._acct_type_badge.setFixedHeight(22)
        left.addWidget(self._acct_type_badge, 0, Qt.AlignmentFlag.AlignLeft)
        hlay.addLayout(left)
        hlay.addStretch()

        # Stat cards
        self._balance_card = self._make_stat_card("Current Balance", "$0.00", "neutral")
        self._ytd_debit_card = self._make_stat_card("YTD Debits", "$0.00", "red")
        self._ytd_credit_card = self._make_stat_card("YTD Credits", "$0.00", "green")
        for card in [self._balance_card, self._ytd_debit_card, self._ytd_credit_card]:
            hlay.addWidget(card)

        # Reconcile badge
        self._rec_badge = QLabel("— Loading")
        self._rec_badge.setStyleSheet(
            "border-radius: 10px; padding: 3px 12px; font-size: 11px; "
            "font-weight: 600; background-color: #E0F2F1; color: #2E7D32; border: none;"
        )
        hlay.addWidget(self._rec_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        return frame

    def _make_stat_card(self, label: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 8px; padding: 4px;"
        )
        card.setFixedWidth(150)
        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(10, 8, 10, 8)
        vlay.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            "font-size: 10px; color: #666; font-weight: 500; border: none;"
        )
        lbl.setObjectName(f"card_label_{label.replace(' ','_')}")
        vlay.addWidget(lbl)

        val_lbl = QLabel(value)
        color_map = {"red": COLOR_RED, "green": COLOR_GREEN, "neutral": COLOR_NAVY}
        c = color_map.get(color, COLOR_NAVY)
        val_lbl.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {c}; border: none;"
        )
        val_lbl.setObjectName(f"card_value_{label.replace(' ','_')}")
        vlay.addWidget(val_lbl)
        card._val_lbl = val_lbl
        card._color = color
        return card

    def _update_stat_card(self, card: QFrame, value: float):
        text = format_currency(value)
        color = card._color
        if color == "neutral":
            c = COLOR_GREEN if value >= 0 else COLOR_RED
        elif color == "red":
            c = COLOR_RED
        else:
            c = COLOR_GREEN
        card._val_lbl.setText(text)
        card._val_lbl.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {c}; border: none;"
        )

    def _build_toolbar(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 6px;"
        )
        main = QVBoxLayout(frame)
        main.setContentsMargins(10, 8, 10, 8)
        main.setSpacing(6)

        # Row 1: date range
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(QLabel("From:"))
        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDisplayFormat("MM/dd/yyyy")
        first = QDate(QDate.currentDate().year(), 1, 1)
        self._from_date.setDate(first)
        self._from_date.setFixedWidth(110)
        row1.addWidget(self._from_date)

        row1.addWidget(QLabel("To:"))
        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDisplayFormat("MM/dd/yyyy")
        self._to_date.setDate(QDate.currentDate())
        self._to_date.setFixedWidth(110)
        row1.addWidget(self._to_date)

        for label, slot in [("This Month", self._filter_this_month),
                             ("This Year", self._filter_this_year),
                             ("Last Year", self._filter_last_year),
                             ("All", self._filter_all)]:
            btn = QPushButton(label)
            btn.setProperty("flat", True)
            btn.setStyleSheet(
                "QPushButton { background: transparent; color: #1565C0; border: 1px solid #C5D5E8; "
                "border-radius: 4px; padding: 3px 9px; font-size: 11px; min-height: 0; }"
                "QPushButton:hover { background: #EEF4FB; }"
            )
            btn.clicked.connect(slot)
            row1.addWidget(btn)

        row1.addStretch()
        main.addLayout(row1)

        # Row 2: search + filters + buttons
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search description or memo…")
        self._search_edit.setFixedWidth(210)
        self._search_edit.textChanged.connect(self._on_filter_changed)
        row2.addWidget(self._search_edit)

        self._type_filter = QComboBox()
        self._type_filter.setFixedWidth(130)
        self._type_filter.addItem("All Types")
        from src.ui.transaction_dialog import TRANSACTION_TYPES
        self._type_filter.addItems(TRANSACTION_TYPES)
        self._type_filter.currentTextChanged.connect(self._on_filter_changed)
        row2.addWidget(self._type_filter)

        self._cat_filter = QComboBox()
        self._cat_filter.setFixedWidth(150)
        self._cat_filter.addItem("All Categories")
        self._cat_filter.currentTextChanged.connect(self._on_filter_changed)
        row2.addWidget(self._cat_filter)

        self._rec_filter = QComboBox()
        self._rec_filter.setFixedWidth(130)
        self._rec_filter.addItems(["All", "Reconciled", "Unreconciled"])
        self._rec_filter.currentTextChanged.connect(self._on_filter_changed)
        row2.addWidget(self._rec_filter)

        find_btn = QPushButton("Find Next Unreconciled")
        find_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #E07B39; border: 1px solid #E07B39; "
            "border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: 600; min-height: 0; }"
            "QPushButton:hover { background: #FFF3E0; }"
        )
        find_btn.clicked.connect(self._find_next_unreconciled)
        row2.addWidget(find_btn)

        import_btn = QPushButton("⬆ Import CSV")
        import_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #1565C0; border: 1px solid #1565C0; "
            "border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: 600; min-height: 0; }"
            "QPushButton:hover { background: #EEF4FB; }"
        )
        import_btn.clicked.connect(self._import_csv)
        row2.addWidget(import_btn)

        self._stmt_btn = QPushButton("⚖ Statement Balance")
        self._stmt_btn.setCheckable(True)
        self._stmt_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #2E7D32; border: 1px solid #2E7D32; "
            "border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: 600; min-height: 0; }"
            "QPushButton:hover { background: #E8F5E9; }"
            "QPushButton:checked { background: #2E7D32; color: white; }"
        )
        self._stmt_btn.clicked.connect(self._toggle_rec_panel)
        row2.addWidget(self._stmt_btn)

        row2.addStretch()

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #0D2B5C; "
            "border: 2px solid #0D2B5C; border-radius: 5px; padding: 7px 14px; "
            "font-size: 13px; font-weight: 600; min-height: 32px; min-width: 90px; }"
            "QPushButton:hover { background-color: #EEF4FB; border-color: #1565C0; color: #1565C0; }"
        )
        refresh_btn.clicked.connect(self.refresh)
        row2.addWidget(refresh_btn)

        add_btn = QPushButton("+ Add Transaction")
        add_btn.setStyleSheet(
            "QPushButton { background-color: #E07B39; color: #FFFFFF; "
            "border: none; border-radius: 5px; padding: 7px 18px; "
            "font-size: 13px; font-weight: 600; min-height: 32px; }"
            "QPushButton:hover { background-color: #c9692a; }"
        )
        add_btn.clicked.connect(self._add_transaction)
        row2.addWidget(add_btn)

        main.addLayout(row2)
        return frame

    def _build_month_bar(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        hlay = QHBoxLayout(frame)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(4)
        self._month_btns = []

        all_btn = QPushButton("All")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.setStyleSheet(self._month_pill_style(True))
        all_btn.clicked.connect(lambda: self._select_month(None, all_btn))
        hlay.addWidget(all_btn)
        self._month_btns.append((None, all_btn))

        for i, m in enumerate(MONTHS):
            btn = QPushButton(m)
            btn.setCheckable(True)
            btn.setChecked(False)
            btn.setStyleSheet(self._month_pill_style(False))
            btn.clicked.connect(lambda _, idx=i+1, b=btn: self._select_month(idx, b))
            hlay.addWidget(btn)
            self._month_btns.append((i+1, btn))

        hlay.addStretch()
        return frame

    def _month_pill_style(self, active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: {COLOR_NAVY}; color: white; border-radius: 12px; "
                f"padding: 3px 12px; font-size: 11px; font-weight: 600; border: none; min-height: 0; }}"
            )
        return (
            "QPushButton { background: #dde8f5; color: #0D2B5C; border-radius: 12px; "
            "padding: 3px 12px; font-size: 11px; border: none; min-height: 0; }"
            "QPushButton:hover { background: #bfd4ec; }"
        )

    def _select_month(self, month: int, btn: QPushButton):
        self._month_filter = month
        for _, b in self._month_btns:
            b.setChecked(False)
            b.setStyleSheet(self._month_pill_style(False))
        btn.setChecked(True)
        btn.setStyleSheet(self._month_pill_style(True))
        self.refresh()

    def _build_footer(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: 6px;"
        )
        hlay = QHBoxLayout(frame)
        hlay.setContentsMargins(12, 6, 12, 6)
        hlay.setSpacing(20)

        self._footer_rows = QLabel("0 transactions")
        self._footer_rows.setStyleSheet("color: #666; font-size: 11px; border: none;")
        hlay.addWidget(self._footer_rows)

        self._footer_debits = QLabel("Total Debits: $0.00")
        self._footer_debits.setStyleSheet(f"color: {COLOR_RED}; font-size: 11px; font-weight: 600; border: none;")
        hlay.addWidget(self._footer_debits)

        self._footer_credits = QLabel("Total Credits: $0.00")
        self._footer_credits.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 11px; font-weight: 600; border: none;")
        hlay.addWidget(self._footer_credits)

        self._footer_net = QLabel("Net: $0.00")
        self._footer_net.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 11px; font-weight: 700; border: none;")
        hlay.addWidget(self._footer_net)

        hlay.addStretch()
        note = QLabel("Balance shown is the true account balance, not filtered total.")
        note.setStyleSheet("color: #aaa; font-size: 10px; font-style: italic; border: none;")
        hlay.addWidget(note)

        return frame

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def load_account(self):
        self._account = self.db.get_account_by_id(self.account_id)
        if not self._account:
            return
        self._acct_name_lbl.setText(self._account['name'])
        atype = self._account.get('type', 'Other')
        colors = ACCOUNT_TYPE_COLORS.get(atype, ("#546E7A", "#FFFFFF"))
        self._acct_type_badge.setText(atype)
        self._acct_type_badge.setStyleSheet(
            f"border-radius: 10px; padding: 2px 12px; font-size: 11px; "
            f"font-weight: 600; background-color: {colors[0]}; "
            f"color: {colors[1]}; border: none;"
        )

        # Populate category filter
        self._cat_filter.clear()
        self._cat_filter.addItem("All Categories")
        cats = self.db.get_all_categories()
        self._cat_filter_map = {'All Categories': None}
        for c in cats:
            self._cat_filter.addItem(c['name'])
            self._cat_filter_map[c['name']] = c['id']

    def refresh(self):
        """Reload balances and transactions, repopulate table."""
        # Compute running balances for ALL transactions (unfiltered)
        self._all_balances = self.db.get_running_balance(self.account_id)

        # Stat cards
        balance = self.db.get_account_balance(self.account_id)
        ytd = self.db.get_ytd_totals(self.account_id, self.user_id)
        self._update_stat_card(self._balance_card, balance)
        self._update_stat_card(self._ytd_debit_card, -ytd['ytd_debits'])
        self._update_stat_card(self._ytd_credit_card, ytd['ytd_credits'])

        # Reconcile badge
        unrec = self.db.get_unreconciled_count(self.account_id)
        if unrec == 0:
            self._rec_badge.setText("✓ All Reconciled")
            self._rec_badge.setStyleSheet(
                "border-radius: 10px; padding: 3px 12px; font-size: 11px; "
                "font-weight: 600; background-color: #E0F2F1; color: #2E7D32; border: none;"
            )
        else:
            self._rec_badge.setText(f"⚠ {unrec} Unreconciled")
            self._rec_badge.setStyleSheet(
                "border-radius: 10px; padding: 3px 12px; font-size: 11px; "
                "font-weight: 600; background-color: #FFF3E0; color: #E65100; border: none;"
            )

        self._populate_table()
        self._update_rec_panel()

    def _get_filters(self):
        from_d = self._from_date.date().toString("yyyy-MM-dd")
        to_d = self._to_date.date().toString("yyyy-MM-dd")
        search = self._search_edit.text().strip() or None
        type_f = self._type_filter.currentText()
        if type_f == "All Types":
            type_f = None
        cat_name = self._cat_filter.currentText()
        cat_id = getattr(self, '_cat_filter_map', {}).get(cat_name, None)
        rec_f = self._rec_filter.currentText().lower()
        if rec_f == "all":
            rec_f = "all"
        elif rec_f == "reconciled":
            rec_f = "reconciled"
        else:
            rec_f = "unreconciled"
        return from_d, to_d, search, type_f, cat_id, rec_f

    def _populate_table(self):
        from_d, to_d, search, type_f, cat_id, rec_f = self._get_filters()

        # If month filter active, override date range
        if self._month_filter is not None:
            year = self._from_date.date().year()
            m = self._month_filter
            last = calendar.monthrange(year, m)[1]
            from_d = f"{year:04d}-{m:02d}-01"
            to_d = f"{year:04d}-{m:02d}-{last:02d}"

        rows = self.db.get_transactions(
            self.account_id,
            start_date=from_d if self._has_date_filter() else None,
            end_date=to_d if self._has_date_filter() else None,
            search=search,
            type_filter=type_f,
            category_id=cat_id,
            reconciled_filter=rec_f
        )

        # Sort
        reverse = (self._sort_order == Qt.SortOrder.DescendingOrder)
        col_key_map = {
            COL_DATE: lambda r: r['date'],
            COL_TYPE: lambda r: r.get('type', ''),
            COL_CHECK: lambda r: r.get('check_number') or '',
            COL_DESC: lambda r: (r.get('description') or '').lower(),
            COL_MEMO: lambda r: (r.get('memo') or '').lower(),
            COL_CAT: lambda r: (r.get('category_name') or '').lower(),
            COL_REC: lambda r: r.get('reconciled', 0),
            COL_DEBIT: lambda r: r.get('debit', 0),
            COL_CREDIT: lambda r: r.get('credit', 0),
            COL_BAL: lambda r: self._all_balances.get(r['id'], 0),
        }
        sort_fn = col_key_map.get(self._sort_col, lambda r: r['date'])
        rows.sort(key=sort_fn, reverse=reverse)

        self._transactions = rows
        self._table.setUpdatesEnabled(False)
        self._table.setRowCount(len(rows))

        total_debit = 0.0
        total_credit = 0.0

        for row_idx, tx in enumerate(rows):
            is_rec = bool(tx.get('reconciled', 0))

            def make_item(text, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
                item = QTableWidgetItem(str(text) if text is not None else "")
                item.setTextAlignment(int(align))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if is_rec:
                    item.setBackground(QBrush(QColor(COLOR_RECONCILED_BG)))
                    item.setForeground(QBrush(QColor(COLOR_RECONCILED_TEXT)))
                return item

            right_align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

            # Date
            date_str = tx.get('date', '')
            if date_str:
                try:
                    parts = date_str.split('-')
                    date_str = f"{parts[1]}/{parts[2]}/{parts[0]}"
                except Exception:
                    pass
            self._table.setItem(row_idx, COL_DATE, make_item(date_str))

            self._table.setItem(row_idx, COL_TYPE, make_item(tx.get('type', '')))
            self._table.setItem(row_idx, COL_CHECK, make_item(tx.get('check_number', '') or ''))
            self._table.setItem(row_idx, COL_DESC, make_item(tx.get('description', '') or ''))
            self._table.setItem(row_idx, COL_MEMO, make_item(tx.get('memo', '') or ''))
            self._table.setItem(row_idx, COL_CAT, make_item(tx.get('category_name', '') or ''))

            # Reconciled checkbox indicator
            rec_item = make_item("✓" if is_rec else "", Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if is_rec:
                rec_item.setForeground(QBrush(QColor(COLOR_RECONCILED_TEXT)))
            self._table.setItem(row_idx, COL_REC, rec_item)

            # Debit
            debit = tx.get('debit', 0)
            d_item = make_item(format_currency(debit) if debit else "", right_align)
            if debit and not is_rec:
                d_item.setForeground(QBrush(QColor(COLOR_RED)))
            self._table.setItem(row_idx, COL_DEBIT, d_item)

            # Credit
            credit = tx.get('credit', 0)
            c_item = make_item(format_currency(credit) if credit else "", right_align)
            if credit and not is_rec:
                c_item.setForeground(QBrush(QColor(COLOR_GREEN)))
            self._table.setItem(row_idx, COL_CREDIT, c_item)

            # Balance (true running balance)
            bal = self._all_balances.get(tx['id'], 0.0)
            bal_item = make_item(format_currency(bal), right_align)
            if not is_rec:
                bal_item.setForeground(QBrush(QColor(COLOR_GREEN if bal >= 0 else COLOR_RED)))
            self._table.setItem(row_idx, COL_BAL, bal_item)

            # Store transaction id in row
            self._table.item(row_idx, COL_DATE).setData(Qt.ItemDataRole.UserRole, tx['id'])

            total_debit += debit
            total_credit += credit

        self._table.setUpdatesEnabled(True)

        # Update footer
        net = total_credit - total_debit
        self._footer_rows.setText(f"{len(rows)} transaction{'s' if len(rows) != 1 else ''}")
        self._footer_debits.setText(f"Total Debits: {format_currency(total_debit)}")
        self._footer_credits.setText(f"Total Credits: {format_currency(total_credit)}")
        net_text = f"Net: {format_currency(net)}"
        net_color = COLOR_GREEN if net >= 0 else COLOR_RED
        self._footer_net.setText(net_text)
        self._footer_net.setStyleSheet(
            f"color: {net_color}; font-size: 11px; font-weight: 700; border: none;"
        )

    def _has_date_filter(self) -> bool:
        """Returns True if date range is not the absolute all-time range."""
        # Always apply date filter since we have from/to pickers
        return True

    # -------------------------------------------------------------------------
    # Filter helpers
    # -------------------------------------------------------------------------

    def _filter_this_month(self):
        today = QDate.currentDate()
        first = QDate(today.year(), today.month(), 1)
        last = QDate(today.year(), today.month(), today.daysInMonth())
        self._from_date.setDate(first)
        self._to_date.setDate(last)
        self._month_bar.show()
        self._set_month_pill(today.month())
        self.refresh()

    def _filter_this_year(self):
        today = QDate.currentDate()
        self._from_date.setDate(QDate(today.year(), 1, 1))
        self._to_date.setDate(QDate(today.year(), 12, 31))
        self._month_bar.show()
        self._set_month_pill(None)
        self.refresh()

    def _filter_last_year(self):
        today = QDate.currentDate()
        y = today.year() - 1
        self._from_date.setDate(QDate(y, 1, 1))
        self._to_date.setDate(QDate(y, 12, 31))
        self._month_bar.show()
        self._set_month_pill(None)
        self.refresh()

    def _filter_all(self):
        self._from_date.setDate(QDate(2000, 1, 1))
        self._to_date.setDate(QDate(2099, 12, 31))
        self._month_bar.hide()
        self._month_filter = None
        self.refresh()

    def _set_month_pill(self, month: int):
        self._month_filter = month
        for m, btn in self._month_btns:
            active = (m == month)
            btn.setChecked(active)
            btn.setStyleSheet(self._month_pill_style(active))

    def _on_filter_changed(self):
        self._populate_table()

    def _on_header_clicked(self, col: int):
        if self._sort_col == col:
            self._sort_order = (Qt.SortOrder.AscendingOrder
                                if self._sort_order == Qt.SortOrder.DescendingOrder
                                else Qt.SortOrder.DescendingOrder)
        else:
            self._sort_col = col
            self._sort_order = Qt.SortOrder.DescendingOrder
        self._table.horizontalHeader().setSortIndicator(self._sort_col, self._sort_order)
        self._populate_table()

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _get_selected_tx_id(self) -> int:
        rows = self._table.selectedItems()
        if not rows:
            return None
        row = self._table.currentRow()
        item = self._table.item(row, COL_DATE)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _add_transaction(self):
        dlg = TransactionDialog(
            parent=self, db=self.db,
            account_id=self.account_id,
            user_id=self.user_id
        )
        if dlg.exec() == TransactionDialog.DialogCode.Accepted:
            data = dlg.get_result()
            try:
                self.db.create_transaction(
                    account_id=self.account_id,
                    date=data['date'],
                    type=data['type'],
                    check_number=data.get('check_number'),
                    description=data.get('description', ''),
                    memo=data.get('memo', ''),
                    category_id=data.get('category_id'),
                    reconciled=data.get('reconciled', 0),
                    debit=data.get('debit', 0.0),
                    credit=data.get('credit', 0.0),
                    created_by_user_id=self.user_id
                )
                self.refresh()
            except Exception as e:
                self._show_status_error(str(e))

    def _edit_selected(self):
        tx_id = self._get_selected_tx_id()
        if not tx_id:
            return
        tx = self.db.get_transaction_by_id(tx_id)
        if not tx:
            return
        dlg = TransactionDialog(
            parent=self, db=self.db,
            account_id=self.account_id,
            user_id=self.user_id,
            transaction=dict(tx)
        )
        if dlg.exec() == TransactionDialog.DialogCode.Accepted:
            data = dlg.get_result()
            try:
                self.db.update_transaction(
                    transaction_id=tx_id,
                    date=data['date'],
                    type=data['type'],
                    check_number=data.get('check_number'),
                    description=data.get('description', ''),
                    memo=data.get('memo', ''),
                    category_id=data.get('category_id'),
                    reconciled=data.get('reconciled', 0),
                    debit=data.get('debit', 0.0),
                    credit=data.get('credit', 0.0)
                )
                self.refresh()
            except Exception as e:
                self._show_status_error(str(e))

    def _delete_selected(self):
        tx_id = self._get_selected_tx_id()
        if not tx_id:
            return
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout as _HBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Delete Transaction")
        dlg.setFixedWidth(400)
        dlg.setModal(True)
        vlay = QVBoxLayout(dlg)
        vlay.setContentsMargins(24, 20, 24, 20)
        vlay.setSpacing(16)
        lbl = QLabel("Are you sure you want to delete this transaction?\nThis cannot be undone.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #1A1A2E; font-size: 13px;")
        vlay.addWidget(lbl)
        btn_row = _HBox()
        btn_row.setSpacing(10)
        cancel_b = QPushButton("Cancel")
        cancel_b.setStyleSheet(
            "QPushButton { background-color: transparent; color: #0D2B5C; "
            "border: 2px solid #0D2B5C; border-radius: 5px; padding: 7px 18px; "
            "font-size: 13px; font-weight: 600; min-height: 32px; }"
            "QPushButton:hover { background-color: #EEF4FB; }"
        )
        cancel_b.clicked.connect(dlg.reject)
        delete_b = QPushButton("Delete")
        delete_b.setStyleSheet(
            "QPushButton { background-color: #C62828; color: #FFFFFF; "
            "border: none; border-radius: 5px; padding: 7px 18px; "
            "font-size: 13px; font-weight: 600; min-height: 32px; }"
            "QPushButton:hover { background-color: #b71c1c; }"
        )
        delete_b.clicked.connect(dlg.accept)
        btn_row.addStretch()
        btn_row.addWidget(cancel_b)
        btn_row.addWidget(delete_b)
        vlay.addLayout(btn_row)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.db.delete_transaction(tx_id)
                self.refresh()
            except Exception as e:
                self._show_status_error(str(e))

    def _mark_reconciled(self, reconciled: int):
        tx_id = self._get_selected_tx_id()
        if not tx_id:
            return
        try:
            self.db.mark_reconciled(tx_id, reconciled)
            self.refresh()
        except Exception as e:
            self._show_status_error(str(e))

    def _find_next_unreconciled(self):
        for row in range(self._table.rowCount()):
            item = self._table.item(row, COL_DATE)
            if item:
                tx_id = item.data(Qt.ItemDataRole.UserRole)
                tx = next((t for t in self._transactions if t['id'] == tx_id), None)
                if tx and not tx.get('reconciled', 0):
                    self._table.scrollToItem(item)
                    self._table.selectRow(row)
                    return

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        edit_act = QAction("Edit", self)
        edit_act.triggered.connect(self._edit_selected)
        menu.addAction(edit_act)

        del_act = QAction("Delete", self)
        del_act.triggered.connect(self._delete_selected)
        menu.addAction(del_act)

        menu.addSeparator()

        rec_act = QAction("Mark Reconciled", self)
        rec_act.triggered.connect(lambda: self._mark_reconciled(1))
        menu.addAction(rec_act)

        unrec_act = QAction("Mark Unreconciled", self)
        unrec_act.triggered.connect(lambda: self._mark_reconciled(0))
        menu.addAction(unrec_act)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    # -------------------------------------------------------------------------
    # Statement reconciliation panel
    # -------------------------------------------------------------------------

    def _build_rec_panel(self) -> QFrame:
        from PyQt6.QtWidgets import QDoubleSpinBox, QDateEdit as _QDE
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background-color: #F0FAF1; border: 1.5px solid #81C784; border-radius: 8px; }"
        )
        outer = QHBoxLayout(panel)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(24)

        # ── Left: inputs ──
        left = QVBoxLayout()
        left.setSpacing(8)

        title_row = QHBoxLayout()
        t = QLabel("⚖  Reconcile with Bank Statement")
        t.setStyleSheet(
            "color: #1B5E20; font-size: 13px; font-weight: 700; border: none; background: transparent;"
        )
        title_row.addWidget(t)
        title_row.addStretch()
        close_btn = QPushButton("✕ Hide")
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #555; border: none; "
            "font-size: 11px; padding: 2px 6px; min-height: 0; }"
            "QPushButton:hover { color: #C62828; }"
        )
        close_btn.clicked.connect(lambda: (
            self._rec_panel.hide(),
            self._stmt_btn.setChecked(False)
        ))
        title_row.addWidget(close_btn)
        left.addLayout(title_row)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(12)

        fields_row.addWidget(QLabel("Ending Balance from Statement:"))
        self._rec_target_spin = QDoubleSpinBox()
        self._rec_target_spin.setPrefix("$ ")
        self._rec_target_spin.setRange(-9_999_999.99, 9_999_999.99)
        self._rec_target_spin.setDecimals(2)
        self._rec_target_spin.setGroupSeparatorShown(True)
        self._rec_target_spin.setFixedWidth(150)
        self._rec_target_spin.setStyleSheet(
            "background-color: white; border: 1.5px solid #81C784; border-radius: 4px; padding: 4px 8px;"
        )
        fields_row.addWidget(self._rec_target_spin)

        fields_row.addWidget(QLabel("Statement Date:"))
        self._rec_date_edit = _QDE()
        self._rec_date_edit.setCalendarPopup(True)
        self._rec_date_edit.setDisplayFormat("MM/dd/yyyy")
        self._rec_date_edit.setDate(QDate.currentDate())
        self._rec_date_edit.setFixedWidth(120)
        self._rec_date_edit.setStyleSheet(
            "background-color: white; border: 1.5px solid #81C784; border-radius: 4px; padding: 4px 8px;"
        )
        fields_row.addWidget(self._rec_date_edit)

        set_btn = QPushButton("Set / Update Target")
        set_btn.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; border-radius: 4px; "
            "padding: 5px 14px; font-size: 12px; font-weight: 600; min-height: 0; border: none; }"
            "QPushButton:hover { background-color: #1B5E20; }"
        )
        set_btn.clicked.connect(self._set_rec_target)
        fields_row.addWidget(set_btn)

        clear_btn = QPushButton("✕ Clear")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #C62828; border: 1px solid #C62828; "
            "border-radius: 4px; padding: 5px 10px; font-size: 12px; font-weight: 600; min-height: 0; }"
            "QPushButton:hover { background-color: #FFEBEE; }"
        )
        clear_btn.clicked.connect(self._clear_rec_target)
        fields_row.addWidget(clear_btn)

        fields_row.addStretch()
        left.addLayout(fields_row)

        # Active target status line
        self._rec_active_lbl = QLabel("")
        self._rec_active_lbl.setStyleSheet(
            "color: #1B5E20; font-size: 11px; font-weight: 600; border: none; background: transparent;"
        )
        self._rec_active_lbl.hide()
        left.addWidget(self._rec_active_lbl)

        hint = QLabel(
            "Mark transactions as reconciled (✓) in the register. "
            "The panel updates in real time as you check them."
        )
        hint.setStyleSheet("color: #555; font-size: 11px; font-style: italic; border: none; background: transparent;")
        left.addWidget(hint)

        outer.addLayout(left, 1)

        # ── Right: live status display ──
        self._rec_status_frame = QFrame()
        self._rec_status_frame.setStyleSheet(
            "QFrame { background-color: white; border: 1.5px solid #A5D6A7; "
            "border-radius: 8px; min-width: 230px; max-width: 280px; }"
        )
        self._rec_status_frame.hide()
        status_lay = QVBoxLayout(self._rec_status_frame)
        status_lay.setContentsMargins(16, 12, 16, 12)
        status_lay.setSpacing(4)

        self._rec_target_lbl = QLabel("$0.00")
        self._rec_target_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rec_target_lbl.setStyleSheet(
            "color: #0D2B5C; font-size: 28px; font-weight: 700; border: none;"
        )
        status_lay.addWidget(self._rec_target_lbl)

        self._rec_target_sub = QLabel("Target Ending Balance")
        self._rec_target_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rec_target_sub.setStyleSheet(
            "color: #888; font-size: 10px; letter-spacing: 0.5px; border: none;"
        )
        status_lay.addWidget(self._rec_target_sub)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("border: none; background-color: #E8F5E9; max-height: 1px; margin: 6px 0;")
        status_lay.addWidget(div)

        self._rec_diff_lbl = QLabel("")
        self._rec_diff_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rec_diff_lbl.setStyleSheet(
            "color: #1B5E20; font-size: 16px; font-weight: 700; border: none;"
        )
        self._rec_diff_lbl.setWordWrap(True)
        status_lay.addWidget(self._rec_diff_lbl)

        self._rec_progress_lbl = QLabel("")
        self._rec_progress_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rec_progress_lbl.setStyleSheet(
            "color: #555; font-size: 10px; border: none;"
        )
        status_lay.addWidget(self._rec_progress_lbl)

        outer.addWidget(self._rec_status_frame)
        return panel

    def _toggle_rec_panel(self):
        if self._rec_panel.isVisible():
            self._rec_panel.hide()
            self._stmt_btn.setChecked(False)
        else:
            self._rec_panel.show()
            self._stmt_btn.setChecked(True)
            self._update_rec_panel()

    def _set_rec_target(self):
        self._rec_target = self._rec_target_spin.value()
        self._rec_target_date = self._rec_date_edit.date().toString("yyyy-MM-dd")
        self._rec_status_frame.show()
        # Show active target info line
        display_date = self._rec_date_edit.date().toString("MM/dd/yyyy")
        self._rec_active_lbl.setText(
            f"Active target: {format_currency(self._rec_target)} through {display_date}"
        )
        self._rec_active_lbl.show()
        self._update_rec_panel()

    def _clear_rec_target(self):
        self._rec_target = None
        self._rec_target_date = None
        self._rec_status_frame.hide()
        self._rec_active_lbl.hide()
        self._rec_active_lbl.setText("")

    def _update_rec_panel(self):
        """Recompute reconciled balance vs target and update status display."""
        if self._rec_target is None or not self._rec_panel.isVisible():
            return

        # Sum reconciled transactions on or before the statement date
        account = self.db.get_account_by_id(self.account_id)
        opening = account['opening_balance'] if account else 0.0
        all_txs = self.db.get_all_transactions_for_account(self.account_id)

        rec_net = 0.0
        for tx in all_txs:
            if tx.get('reconciled') and tx.get('date', '') <= self._rec_target_date:
                rec_net += tx.get('credit', 0.0) - tx.get('debit', 0.0)

        reconciled_balance = opening + rec_net
        diff = self._rec_target - reconciled_balance

        self._rec_target_lbl.setText(format_currency(self._rec_target))
        # Show statement date in sub-label
        try:
            from PyQt6.QtCore import QDate as _QD
            d = _QD.fromString(self._rec_target_date, "yyyy-MM-dd")
            self._rec_target_sub.setText(f"Target Balance · {d.toString('MM/dd/yyyy')}")
        except Exception:
            self._rec_target_sub.setText("Target Ending Balance")

        if abs(diff) < 0.005:
            self._rec_diff_lbl.setText("✓  Reconciled")
            self._rec_diff_lbl.setStyleSheet(
                f"color: {COLOR_GREEN}; font-size: 16px; font-weight: 700; border: none;"
            )
        elif diff > 0:
            self._rec_diff_lbl.setText(f"{format_currency(diff)}\nleft to reconcile")
            self._rec_diff_lbl.setStyleSheet(
                "color: #1B5E20; font-size: 16px; font-weight: 700; border: none;"
            )
        else:
            self._rec_diff_lbl.setText(
                f"{format_currency(abs(diff))} over ending balance\n— verify transactions"
            )
            self._rec_diff_lbl.setStyleSheet(
                f"color: {COLOR_RED}; font-size: 15px; font-weight: 700; border: none;"
            )

        self._rec_progress_lbl.setText(
            f"Reconciled balance: {format_currency(reconciled_balance)}  of  {format_currency(self._rec_target)} target"
        )

    # -------------------------------------------------------------------------
    # CSV Import
    # -------------------------------------------------------------------------

    def _import_csv(self):
        dlg = CsvImportDialog(
            parent=self, db=self.db,
            account_id=self.account_id,
            user_id=self.user_id
        )
        if dlg.exec() == CsvImportDialog.DialogCode.Accepted:
            count = dlg.get_imported_count()
            self.refresh()
            self._show_status_message(f"Imported {count} transaction{'s' if count != 1 else ''} successfully.")

    def _show_status_message(self, msg: str):
        w = self.parent()
        while w:
            if hasattr(w, 'show_status_message'):
                w.show_status_message(msg)
                return
            w = w.parent()

    def _show_status_error(self, msg: str):
        # Try to bubble up to main window status bar
        w = self.parent()
        while w:
            if hasattr(w, 'show_status_message'):
                w.show_status_message(f"Error: {msg}")
                return
            w = w.parent()
