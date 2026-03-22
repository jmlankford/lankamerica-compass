"""
csv_import_dialog.py — Three-step CSV transaction import wizard
"""
import csv
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QRadioButton, QButtonGroup, QTableWidget,
    QTableWidgetItem, QComboBox, QStackedWidget, QFrame,
    QScrollArea, QWidget, QHeaderView, QMessageBox, QLineEdit,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from src.database import Database
from src.utils import format_currency
from src.ui.styles import (
    COLOR_NAVY, COLOR_WHITE, COLOR_BORDER, COLOR_ORANGE,
    COLOR_RED, COLOR_GREEN, COLOR_MEDIUM_BLUE
)

# ── Constants ──────────────────────────────────────────────────────────────

TRANSACTION_TYPES = [
    "CHECK", "DEBIT CARD", "ATM", "ACH/ELECTRONIC", "DIRECT DEPOSIT",
    "ONLINE TRANSFER", "WIRE TRANSFER", "FEE/CHARGE", "INTEREST",
    "DEPOSIT", "MOBILE DEPOSIT", "ZELLE/VENMO/P2P", "OTHER"
]

FIELD_OPTIONS_SINGLE = [
    ("ignore",       "— Ignore —"),
    ("date",         "Date"),
    ("type",         "Type"),
    ("check_number", "Check #"),
    ("description",  "Description"),
    ("memo",         "Memo"),
    ("category",     "Category"),
    ("amount",       "Amount  (+credit / −debit)"),
    ("cleared",      "Cleared"),
]

FIELD_OPTIONS_TWO = [
    ("ignore",       "— Ignore —"),
    ("date",         "Date"),
    ("type",         "Type"),
    ("check_number", "Check #"),
    ("description",  "Description"),
    ("memo",         "Memo"),
    ("category",     "Category"),
    ("debit",        "Debit (money out)"),
    ("credit",       "Credit (money in)"),
    ("cleared",      "Cleared"),
]

DATE_FORMATS: List[Tuple[str, str]] = [
    ("MM/DD/YYYY",  "%m/%d/%Y"),
    ("M/D/YYYY",    "%m/%d/%Y"),
    ("YYYY-MM-DD",  "%Y-%m-%d"),
    ("MM-DD-YYYY",  "%m-%d-%Y"),
    ("M/D/YY",      "%m/%d/%y"),
    ("DD/MM/YYYY",  "%d/%m/%Y"),
    ("MM/DD/YY",    "%m/%d/%y"),
]

# ── Helpers ────────────────────────────────────────────────────────────────

def _try_parse_amount(s: str) -> Optional[float]:
    """Parse a currency string: handles $, commas, parens (negatives)."""
    s = s.strip().replace(',', '').replace('$', '').replace(' ', '')
    if not s:
        return None
    negative = s.startswith('(') and s.endswith(')')
    if negative:
        s = s[1:-1]
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def _parse_date(val: str, fmt: str) -> Optional[str]:
    """Try primary fmt then auto-detect all formats. Returns ISO YYYY-MM-DD or None."""
    val = val.strip()
    for pattern in ([fmt] + [p for _, p in DATE_FORMATS if p != fmt]):
        try:
            return datetime.strptime(val, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _auto_suggest(header: str, field_keys: List[str]) -> str:
    """Guess field mapping from column header text."""
    if not header:
        return 'ignore'
    h = header.lower().strip()
    if any(k in h for k in ('date', 'dt', 'posted', 'trans date', 'tran')):
        return 'date'
    if 'memo' in h:
        return 'memo'
    if any(k in h for k in ('desc', 'payee', 'merchant', 'narration', 'detail', 'name')):
        return 'description'
    if any(k in h for k in ('check', 'chk', 'ck#', 'cheque')):
        return 'check_number'
    if 'category' in h or h == 'cat':
        return 'category' if 'category' in field_keys else 'ignore'
    if 'type' in h:
        return 'type'
    if h in ('amount', 'amt', 'sum', 'value', 'transaction amount'):
        return 'amount' if 'amount' in field_keys else 'ignore'
    if any(k in h for k in ('debit', 'dr', 'withdrawal', 'withdraw', 'out')):
        return 'debit' if 'debit' in field_keys else 'ignore'
    if any(k in h for k in ('credit', 'cr', 'deposit', 'in')):
        return 'credit' if 'credit' in field_keys else 'ignore'
    if any(k in h for k in ('reconcil', 'cleared', 'clr')):
        return 'cleared'
    return 'ignore'


# ── Dialog ─────────────────────────────────────────────────────────────────

class CsvImportDialog(QDialog):
    def __init__(self, parent=None, db: Database = None,
                 account_id: int = None, user_id: int = None):
        super().__init__(parent)
        self.db = db
        self.account_id = account_id
        self.user_id = user_id

        self.setWindowTitle("Import Transactions from CSV")
        self.resize(840, 640)
        self.setModal(True)

        self._csv_rows: List[List[str]] = []
        self._headers: List[str] = []
        self._format = 'single'
        self._col_combos: List[QComboBox] = []
        self._parsed_rows: List[Dict] = []
        self._imported_count = 0

        self._build_ui()

    # ── Shell ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_step_header())

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_page1())
        self._stack.addWidget(self._build_page2())
        self._stack.addWidget(self._build_page3())
        root.addWidget(self._stack, 1)

        root.addWidget(self._build_nav_bar())

    def _build_step_header(self) -> QFrame:
        f = QFrame()
        f.setFixedHeight(52)
        f.setStyleSheet(f"background-color: {COLOR_NAVY};")
        hlay = QHBoxLayout(f)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(0)

        self._step_labels = []
        steps = ["  1  Select File  ", "  2  Map Columns  ", "  3  Preview & Import  "]
        for i, s in enumerate(steps):
            lbl = QLabel(s)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(52)
            self._step_labels.append(lbl)
            hlay.addWidget(lbl)
            if i < len(steps) - 1:
                sep = QLabel("›")
                sep.setStyleSheet(
                    "color: rgba(255,255,255,0.3); font-size: 20px; "
                    "background-color: transparent; padding: 0;"
                )
                sep.setFixedWidth(20)
                hlay.addWidget(sep)
        self._set_step(0)
        return f

    def _set_step(self, idx: int):
        for i, lbl in enumerate(self._step_labels):
            if i == idx:
                lbl.setStyleSheet(
                    "color: white; font-size: 12px; font-weight: 700; "
                    "background-color: transparent; border-bottom: 3px solid #E07B39;"
                )
            elif i < idx:
                lbl.setStyleSheet(
                    "color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; "
                    "background-color: transparent; border-bottom: none;"
                )
            else:
                lbl.setStyleSheet(
                    "color: rgba(255,255,255,0.3); font-size: 12px; font-weight: 500; "
                    "background-color: transparent; border-bottom: none;"
                )

    def _build_nav_bar(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border-top: 1px solid {COLOR_BORDER};"
        )
        hlay = QHBoxLayout(f)
        hlay.setContentsMargins(16, 10, 16, 10)
        hlay.setSpacing(10)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setProperty("secondary", True)
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._go_back)
        hlay.addWidget(self._back_btn)

        hlay.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setProperty("secondary", True)
        cancel.clicked.connect(self.reject)
        hlay.addWidget(cancel)

        self._next_btn = QPushButton("Next →")
        self._next_btn.clicked.connect(self._go_next)
        hlay.addWidget(self._next_btn)

        self._import_btn = QPushButton("Import Transactions")
        self._import_btn.setProperty("accent", True)
        self._import_btn.clicked.connect(self._do_import)
        self._import_btn.hide()
        hlay.addWidget(self._import_btn)

        return f

    # ── Page 1: File + Format ──────────────────────────────────────────────

    def _build_page1(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {COLOR_WHITE};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(20)

        title = QLabel("Step 1 — Select File & Format")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 17px; font-weight: 700;")
        lay.addWidget(title)

        # File picker
        fframe = QFrame()
        fframe.setStyleSheet(
            f"background-color: #f8fafd; border: 1.5px solid {COLOR_BORDER}; border-radius: 6px;"
        )
        flay = QVBoxLayout(fframe)
        flay.setContentsMargins(16, 14, 16, 14)
        flay.setSpacing(8)
        flay.addWidget(QLabel("CSV File:"))
        frow = QHBoxLayout()
        self._file_edit = QLineEdit()
        self._file_edit.setReadOnly(True)
        self._file_edit.setPlaceholderText("No file selected…")
        frow.addWidget(self._file_edit)
        browse = QPushButton("Browse…")
        browse.setFixedWidth(90)
        browse.clicked.connect(self._browse)
        frow.addWidget(browse)
        flay.addLayout(frow)
        lay.addWidget(fframe)

        # Format chooser
        fmtframe = QFrame()
        fmtframe.setStyleSheet(
            f"background-color: #f8fafd; border: 1.5px solid {COLOR_BORDER}; border-radius: 6px;"
        )
        fmtlay = QVBoxLayout(fmtframe)
        fmtlay.setContentsMargins(16, 14, 16, 14)
        fmtlay.setSpacing(10)
        fmtlay.addWidget(QLabel("<b>Column Format:</b>"))

        self._fmt_single = QRadioButton(
            "Single amount column — one 'Amount' column, positive = credit, negative = debit"
        )
        self._fmt_single.setChecked(True)
        self._fmt_two = QRadioButton(
            "Two amount columns — separate 'Debit' and 'Credit' columns"
        )
        grp = QButtonGroup(self)
        grp.addButton(self._fmt_single)
        grp.addButton(self._fmt_two)
        fmtlay.addWidget(self._fmt_single)

        ex1 = QLabel(
            "    Example:  Date, Description, Amount\n"
            "               03/01/2026, Walmart, -45.00\n"
            "               03/05/2026, Paycheck, 1500.00"
        )
        ex1.setStyleSheet(
            "color: #888; font-size: 11px; font-family: Consolas, monospace; border: none;"
        )
        fmtlay.addWidget(ex1)

        fmtlay.addWidget(self._fmt_two)

        ex2 = QLabel(
            "    Example:  Date, Description, Debit, Credit\n"
            "               03/01/2026, Walmart, 45.00,\n"
            "               03/05/2026, Paycheck, , 1500.00"
        )
        ex2.setStyleSheet(
            "color: #888; font-size: 11px; font-family: Consolas, monospace; border: none;"
        )
        ex2.hide()
        fmtlay.addWidget(ex2)

        self._fmt_single.toggled.connect(lambda c: ex1.setVisible(c))
        self._fmt_two.toggled.connect(lambda c: ex2.setVisible(c))
        lay.addWidget(fmtframe)

        lay.addStretch()

        self._p1_err = QLabel("")
        self._p1_err.setStyleSheet(f"color: {COLOR_RED}; font-size: 12px;")
        self._p1_err.hide()
        lay.addWidget(self._p1_err)

        return w

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        if path:
            self._file_edit.setText(path)
            self._p1_err.hide()

    # ── Page 2: Column Mapping ─────────────────────────────────────────────

    def _build_page2(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {COLOR_WHITE};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 12)
        lay.setSpacing(10)

        title = QLabel("Step 2 — Map Columns")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 17px; font-weight: 700;")
        lay.addWidget(title)

        hint = QLabel(
            "Assign each CSV column to a transaction field. "
            "Set unneeded columns to '— Ignore —'."
        )
        hint.setStyleSheet("color: #555; font-size: 12px;")
        lay.addWidget(hint)

        # Date format row
        dfrow = QHBoxLayout()
        dfrow.addWidget(QLabel("Date format in file:"))
        self._date_fmt_combo = QComboBox()
        for label, _ in DATE_FORMATS:
            self._date_fmt_combo.addItem(label)
        self._date_fmt_combo.setFixedWidth(160)
        dfrow.addWidget(self._date_fmt_combo)
        dfrow.addStretch()
        lay.addLayout(dfrow)

        # Scroll area containing the per-column mapping rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid " + COLOR_BORDER + "; border-radius: 4px; }")
        self._map_container = QWidget()
        self._map_layout = QVBoxLayout(self._map_container)
        self._map_layout.setContentsMargins(0, 0, 0, 0)
        self._map_layout.setSpacing(0)
        scroll.setWidget(self._map_container)
        lay.addWidget(scroll)

        self._p2_err = QLabel("")
        self._p2_err.setStyleSheet(f"color: {COLOR_RED}; font-size: 12px;")
        self._p2_err.hide()
        lay.addWidget(self._p2_err)

        return w

    def _populate_mapping(self):
        """Rebuild mapping rows from current CSV headers."""
        while self._map_layout.count():
            item = self._map_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._col_combos.clear()

        field_opts = (
            FIELD_OPTIONS_SINGLE if self._format == 'single' else FIELD_OPTIONS_TWO
        )
        field_keys = [k for k, _ in field_opts]

        # Header bar
        hbar = QFrame()
        hbar.setStyleSheet(f"background-color: {COLOR_NAVY};")
        hlay = QHBoxLayout(hbar)
        hlay.setContentsMargins(10, 6, 10, 6)
        hlay.setSpacing(8)
        for text, w in [("CSV Column", 170), ("Maps to →", 210), ("Sample values (first 3 rows)", -1)]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: white; font-weight: 700; font-size: 11px;")
            if w > 0:
                lbl.setFixedWidth(w)
            hlay.addWidget(lbl)
        self._map_layout.addWidget(hbar)

        for col_idx, header in enumerate(self._headers):
            row = QFrame()
            bg = "white" if col_idx % 2 == 0 else "#f4f8fd"
            row.setStyleSheet(
                f"background-color: {bg}; border-bottom: 1px solid {COLOR_BORDER};"
            )
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(10, 5, 10, 5)
            rlay.setSpacing(8)

            name_lbl = QLabel(header or f"Column {col_idx + 1}")
            name_lbl.setStyleSheet(
                f"color: {COLOR_NAVY}; font-weight: 600; font-size: 12px;"
            )
            name_lbl.setFixedWidth(170)
            rlay.addWidget(name_lbl)

            combo = QComboBox()
            combo.setFixedWidth(210)
            for key, label in field_opts:
                combo.addItem(label, key)
            suggested = _auto_suggest(header, field_keys)
            if suggested in field_keys:
                combo.setCurrentIndex(field_keys.index(suggested))
            self._col_combos.append(combo)
            rlay.addWidget(combo)

            samples = [
                self._csv_rows[i][col_idx]
                for i in range(min(3, len(self._csv_rows)))
                if col_idx < len(self._csv_rows[i])
            ]
            sample_lbl = QLabel("  |  ".join(samples))
            sample_lbl.setStyleSheet(
                "color: #555; font-size: 11px; font-family: Consolas, monospace;"
            )
            rlay.addWidget(sample_lbl, 1)

            self._map_layout.addWidget(row)

        self._map_layout.addStretch()

    # ── Page 3: Preview ────────────────────────────────────────────────────

    def _build_page3(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {COLOR_WHITE};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 16)
        lay.setSpacing(10)

        title = QLabel("Step 3 — Preview & Import")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 17px; font-weight: 700;")
        lay.addWidget(title)

        self._p3_summary = QLabel("")
        self._p3_summary.setStyleSheet("color: #444; font-size: 12px;")
        lay.addWidget(self._p3_summary)

        self._preview_tbl = QTableWidget()
        self._preview_tbl.setAlternatingRowColors(True)
        self._preview_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_tbl.verticalHeader().setVisible(False)
        self._preview_tbl.horizontalHeader().setStretchLastSection(True)
        self._preview_tbl.verticalHeader().setDefaultSectionSize(26)
        lay.addWidget(self._preview_tbl)

        self._p3_err = QLabel("")
        self._p3_err.setStyleSheet(f"color: {COLOR_RED}; font-size: 12px;")
        self._p3_err.setWordWrap(True)
        self._p3_err.hide()
        lay.addWidget(self._p3_err)

        return w

    def _populate_preview(self):
        cols_keys = [
            'date', 'type', 'check_number', 'description',
            'memo', 'category', 'debit', 'credit', 'cleared'
        ]
        cols_labels = [
            "Date", "Type", "Check #", "Description",
            "Memo", "Category", "Debit", "Credit", "Reconciled"
        ]
        self._preview_tbl.setColumnCount(len(cols_keys))
        self._preview_tbl.setHorizontalHeaderLabels(cols_labels)
        preview = self._parsed_rows[:25]
        self._preview_tbl.setRowCount(len(preview))

        for r, row in enumerate(preview):
            for c, key in enumerate(cols_keys):
                val = row.get(key, '')
                if key in ('debit', 'credit') and val:
                    try:
                        val = f"${float(val):.2f}"
                    except (ValueError, TypeError):
                        pass
                elif key == 'cleared':
                    val = "Yes" if val else "No"
                item = QTableWidgetItem(str(val) if val else '')
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._preview_tbl.setItem(r, c, item)

        self._preview_tbl.resizeColumnsToContents()

        total_d = sum(float(r.get('debit', 0) or 0) for r in self._parsed_rows)
        total_c = sum(float(r.get('credit', 0) or 0) for r in self._parsed_rows)
        skipped = len(self._csv_rows) - len(self._parsed_rows)
        self._p3_summary.setText(
            f"{len(self._parsed_rows)} transactions ready to import  ·  "
            f"Total Debits: {format_currency(total_d)}  ·  "
            f"Total Credits: {format_currency(total_c)}"
            + (f"  ·  {skipped} rows skipped (unreadable)" if skipped else "")
        )

    # ── Navigation logic ───────────────────────────────────────────────────

    def _go_next(self):
        page = self._stack.currentIndex()

        if page == 0:
            path = self._file_edit.text().strip()
            if not path:
                self._p1_err.setText("Please select a CSV file first.")
                self._p1_err.show()
                return
            try:
                rows, headers = self._read_csv(path)
            except Exception as e:
                self._p1_err.setText(f"Could not read file: {e}")
                self._p1_err.show()
                return
            if not rows:
                self._p1_err.setText("The CSV file appears to be empty or has only a header row.")
                self._p1_err.show()
                return
            self._csv_rows = rows
            self._headers = headers
            self._format = 'single' if self._fmt_single.isChecked() else 'two'
            self._populate_mapping()
            self._p1_err.hide()
            self._stack.setCurrentIndex(1)
            self._set_step(1)
            self._back_btn.setEnabled(True)

        elif page == 1:
            mapping = {i: cb.currentData() for i, cb in enumerate(self._col_combos)}
            err = self._validate_mapping(mapping)
            if err:
                self._p2_err.setText(err)
                self._p2_err.show()
                return
            fmt_label = self._date_fmt_combo.currentText()
            fmt_pattern = next(
                (p for lbl, p in DATE_FORMATS if lbl == fmt_label), "%m/%d/%Y"
            )
            parsed = self._parse_rows(mapping, fmt_pattern)
            if not parsed:
                self._p2_err.setText(
                    "No valid rows could be parsed. "
                    "Check your column mapping and date format, then try again."
                )
                self._p2_err.show()
                return
            self._parsed_rows = parsed
            self._p2_err.hide()
            self._populate_preview()
            self._stack.setCurrentIndex(2)
            self._set_step(2)
            self._next_btn.hide()
            self._import_btn.show()

    def _go_back(self):
        page = self._stack.currentIndex()
        if page == 1:
            self._stack.setCurrentIndex(0)
            self._set_step(0)
            self._back_btn.setEnabled(False)
        elif page == 2:
            self._stack.setCurrentIndex(1)
            self._set_step(1)
            self._next_btn.show()
            self._import_btn.hide()

    # ── CSV reading ────────────────────────────────────────────────────────

    def _read_csv(self, path: str) -> Tuple[List[List[str]], List[str]]:
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            all_rows = list(reader)
        if not all_rows:
            return [], []
        headers = [h.strip() for h in all_rows[0]]
        data = [row for row in all_rows[1:] if any(c.strip() for c in row)]
        return data, headers

    def _validate_mapping(self, mapping: Dict[int, str]) -> Optional[str]:
        keys = list(mapping.values())
        if 'date' not in keys:
            return "You must map at least one column to 'Date'."
        if self._format == 'single' and 'amount' not in keys:
            return "Single-amount format requires mapping a column to 'Amount'."
        if self._format == 'two' and 'debit' not in keys and 'credit' not in keys:
            return "Two-column format requires mapping at least one column to 'Debit' or 'Credit'."
        return None

    def _parse_rows(self, mapping: Dict[int, str], date_fmt: str) -> List[Dict]:
        """Convert raw CSV rows to transaction dicts using the mapping."""
        categories = {
            c['name'].lower(): c['id']
            for c in self.db.get_all_categories()
        }
        parsed = []

        for raw in self._csv_rows:
            tx: Dict = {}
            for col_idx, field_key in mapping.items():
                if field_key == 'ignore' or col_idx >= len(raw):
                    continue
                val = raw[col_idx].strip()
                if not val:
                    continue

                if field_key == 'date':
                    iso = _parse_date(val, date_fmt)
                    if iso:
                        tx['date'] = iso

                elif field_key == 'amount':
                    amt = _try_parse_amount(val)
                    if amt is not None:
                        if amt < 0:
                            tx['debit'] = abs(amt)
                            tx['credit'] = 0.0
                        else:
                            tx['credit'] = amt
                            tx['debit'] = 0.0

                elif field_key == 'debit':
                    amt = _try_parse_amount(val)
                    if amt is not None and abs(amt) > 0:
                        tx['debit'] = abs(amt)

                elif field_key == 'credit':
                    amt = _try_parse_amount(val)
                    if amt is not None and abs(amt) > 0:
                        tx['credit'] = abs(amt)

                elif field_key == 'type':
                    upper = val.upper()
                    matched = next(
                        (t for t in TRANSACTION_TYPES if t in upper), None
                    )
                    tx['type'] = matched or 'OTHER'

                elif field_key == 'category':
                    cat_id = categories.get(val.lower())
                    if cat_id:
                        tx['category_id'] = cat_id
                    tx['category'] = val  # display only

                elif field_key == 'cleared':
                    v = val.lower()
                    tx['cleared'] = 1 if v in ('true', 'yes', 'y', '1', 'r', 'x', 'cleared') else 0

                else:
                    tx[field_key] = val

            # Only keep rows with a parseable date
            if 'date' not in tx:
                continue

            # Defaults
            tx.setdefault('type', 'OTHER')
            tx.setdefault('debit', 0.0)
            tx.setdefault('credit', 0.0)
            tx.setdefault('cleared', 0)
            tx.setdefault('description', '')
            tx.setdefault('memo', '')
            tx.setdefault('check_number', None)
            tx.setdefault('category_id', None)
            tx.setdefault('category', '')

            parsed.append(tx)

        return parsed

    # ── Import ─────────────────────────────────────────────────────────────

    def _do_import(self):
        self._p3_err.hide()
        count = 0
        errors = 0
        for tx in self._parsed_rows:
            try:
                self.db.create_transaction(
                    account_id=self.account_id,
                    date=tx['date'],
                    type=tx['type'],
                    check_number=tx.get('check_number'),
                    description=tx.get('description', ''),
                    memo=tx.get('memo', ''),
                    category_id=tx.get('category_id'),
                    cleared=tx.get('cleared', 0),
                    debit=tx.get('debit', 0.0),
                    credit=tx.get('credit', 0.0),
                    created_by_user_id=self.user_id
                )
                count += 1
            except Exception:
                errors += 1

        self._imported_count = count
        if errors:
            self._p3_err.setText(
                f"Imported {count} transactions successfully. "
                f"{errors} rows could not be saved."
            )
            self._p3_err.show()
        else:
            self.accept()

    def get_imported_count(self) -> int:
        return self._imported_count
