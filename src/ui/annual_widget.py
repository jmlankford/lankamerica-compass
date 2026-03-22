"""
annual_widget.py — Annual totals breakdown widget
"""
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QSpinBox, QFrame, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont

from src.database import Database
from src.utils import format_currency
from src.ui.styles import (
    COLOR_NAVY, COLOR_WHITE, COLOR_BORDER, COLOR_RED, COLOR_GREEN,
    COLOR_TABLE_HEADER_BG, COLOR_TABLE_HEADER_TEXT
)

from datetime import date as _date

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class AnnualWidget(QWidget):
    # Signal to navigate to an account register
    # emitted with (account_id, month_int, year)
    navigate_to_register = None  # will be connected by main_window

    def __init__(self, db: Database, user_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self._year = _date.today().year
        self._accounts = []
        self._data = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title = QLabel("Annual Totals")
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

        ctrl_row.addWidget(QLabel("Year:"))
        self._year_spin = QSpinBox()
        self._year_spin.setRange(2000, 2100)
        self._year_spin.setValue(self._year)
        self._year_spin.setFixedWidth(80)
        self._year_spin.valueChanged.connect(self._on_year_changed)
        ctrl_row.addWidget(self._year_spin)

        ctrl_row.addWidget(QLabel("Account:"))
        self._account_filter = QComboBox()
        self._account_filter.setFixedWidth(200)
        self._account_filter.addItem("All Accounts", None)
        self._account_filter.currentIndexChanged.connect(self._refresh_table)
        ctrl_row.addWidget(self._account_filter)

        ctrl_row.addStretch()

        export_btn = QPushButton("Export CSV")
        export_btn.setProperty("secondary", True)
        export_btn.clicked.connect(self._export_csv)
        ctrl_row.addWidget(export_btn)

        layout.addWidget(ctrl_frame)

        # Table
        self._table = QTableWidget()
        # Columns: Account | Jan...Dec | YTD Total = 14 columns
        headers = ["Account"] + MONTH_ABBR + ["YTD Total"]
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 14):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(i, 82)

        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(28)
        layout.addWidget(self._table)

    def _on_year_changed(self, value: int):
        self._year = value
        self.refresh()

    def refresh(self):
        self._accounts = self.db.get_accounts_for_user(self.user_id)
        # Refresh account filter combo
        current_data = self._account_filter.currentData()
        self._account_filter.blockSignals(True)
        self._account_filter.clear()
        self._account_filter.addItem("All Accounts", None)
        for acc in self._accounts:
            self._account_filter.addItem(acc['name'], acc['id'])
        # Restore selection
        for i in range(self._account_filter.count()):
            if self._account_filter.itemData(i) == current_data:
                self._account_filter.setCurrentIndex(i)
                break
        self._account_filter.blockSignals(False)

        self._data = self.db.get_annual_monthly_breakdown(self._year, self.user_id)
        self._refresh_table()

    def _refresh_table(self):
        filter_acc_id = self._account_filter.currentData()

        if filter_acc_id is not None:
            accounts = [a for a in self._accounts if a['id'] == filter_acc_id]
        else:
            accounts = self._accounts

        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        # Rows: each account + 1 totals row
        self._table.setUpdatesEnabled(False)
        self._table.setRowCount(len(accounts) + 1)

        # Track column totals
        col_totals = [0.0] * 12
        ytd_col_total = 0.0

        for row_idx, acc in enumerate(accounts):
            acc_id = acc['id']
            month_data = self._data.get(acc_id, {})

            name_item = QTableWidgetItem(acc['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row_idx, 0, name_item)

            ytd = 0.0
            for col_idx, m in enumerate(range(1, 13)):
                net = month_data.get(m, 0.0)
                ytd += net
                col_totals[col_idx] += net

                item = QTableWidgetItem(format_currency(net) if net != 0 else "")
                item.setTextAlignment(int(right))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Store account_id and month for drill-down
                item.setData(Qt.ItemDataRole.UserRole, (acc_id, m))
                if net > 0:
                    item.setForeground(QBrush(QColor(COLOR_GREEN)))
                elif net < 0:
                    item.setForeground(QBrush(QColor(COLOR_RED)))
                self._table.setItem(row_idx, col_idx + 1, item)

            ytd_col_total += ytd
            ytd_item = QTableWidgetItem(format_currency(ytd))
            ytd_item.setTextAlignment(int(right))
            ytd_item.setFlags(ytd_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if ytd > 0:
                ytd_item.setForeground(QBrush(QColor(COLOR_GREEN)))
            elif ytd < 0:
                ytd_item.setForeground(QBrush(QColor(COLOR_RED)))
            self._table.setItem(row_idx, 13, ytd_item)

        # Totals row
        total_row = len(accounts)
        total_name = QTableWidgetItem("TOTAL")
        total_name.setBackground(QBrush(QColor(COLOR_TABLE_HEADER_BG)))
        total_name.setForeground(QBrush(QColor(COLOR_TABLE_HEADER_TEXT)))
        font = QFont()
        font.setBold(True)
        total_name.setFont(font)
        total_name.setFlags(total_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(total_row, 0, total_name)

        for col_idx, val in enumerate(col_totals):
            item = QTableWidgetItem(format_currency(val))
            item.setTextAlignment(int(right))
            item.setBackground(QBrush(QColor(COLOR_TABLE_HEADER_BG)))
            item.setForeground(QBrush(QColor(COLOR_TABLE_HEADER_TEXT)))
            item.setFont(font)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(total_row, col_idx + 1, item)

        ytd_total_item = QTableWidgetItem(format_currency(ytd_col_total))
        ytd_total_item.setTextAlignment(int(right))
        ytd_total_item.setBackground(QBrush(QColor(COLOR_TABLE_HEADER_BG)))
        ytd_total_item.setForeground(QBrush(QColor(COLOR_TABLE_HEADER_TEXT)))
        ytd_total_item.setFont(font)
        ytd_total_item.setFlags(ytd_total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(total_row, 13, ytd_total_item)

        self._table.setUpdatesEnabled(True)
        self._accounts_displayed = accounts

    def _on_cell_double_clicked(self, row: int, col: int):
        """Drill down: navigate to that account's register filtered to that month."""
        if col == 0 or col == 13:
            return
        item = self._table.item(row, col)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        account_id, month = data
        # Find parent main window and navigate
        w = self.parent()
        while w:
            if hasattr(w, 'open_account_month'):
                w.open_account_month(account_id, month, self._year)
                return
            w = w.parent()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Annual Totals",
            f"annual_totals_{self._year}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        filter_acc_id = self._account_filter.currentData()
        if filter_acc_id is not None:
            accounts = [a for a in self._accounts if a['id'] == filter_acc_id]
        else:
            accounts = self._accounts

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Account"] + MONTH_ABBR + ["YTD Total"])
                col_totals = [0.0] * 12
                ytd_total = 0.0
                for acc in accounts:
                    month_data = self._data.get(acc['id'], {})
                    row = [acc['name']]
                    ytd = 0.0
                    for i, m in enumerate(range(1, 13)):
                        net = month_data.get(m, 0.0)
                        ytd += net
                        col_totals[i] += net
                        row.append(f"{net:.2f}")
                    ytd_total += ytd
                    row.append(f"{ytd:.2f}")
                    writer.writerow(row)
                totals_row = ["TOTAL"] + [f"{v:.2f}" for v in col_totals] + [f"{ytd_total:.2f}"]
                writer.writerow(totals_row)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", str(e))
