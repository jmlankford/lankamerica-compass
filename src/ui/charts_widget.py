"""
charts_widget.py — Charts (Pie and Bar) using matplotlib
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QTabWidget, QFrame, QGroupBox,
    QListWidget, QListWidgetItem, QSizePolicy, QFileDialog,
    QRadioButton, QButtonGroup, QSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as mticker

from src.database import Database
from src.utils import format_currency
from src.ui.styles import COLOR_NAVY, COLOR_ORANGE, COLOR_WHITE, COLOR_BORDER

from datetime import date as _date

CHART_COLORS = [
    "#1565C0", "#E07B39", "#26A69A", "#7E57C2", "#EF5350",
    "#66BB6A", "#0D2B5C", "#FFA726", "#29B6F6", "#EC407A",
    "#AB47BC", "#26C6DA", "#D4E157", "#FF7043", "#8D6E63",
]

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class ChartsWidget(QWidget):
    def __init__(self, db: Database, user_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self._accounts = []
        self._build_ui()
        self._load_accounts()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel("Charts")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        self._tabs = QTabWidget()
        self._pie_tab = self._build_pie_tab()
        self._bar_tab = self._build_bar_tab()
        self._tabs.addTab(self._pie_tab, "Pie Chart")
        self._tabs.addTab(self._bar_tab, "Bar Chart")
        layout.addWidget(self._tabs)

    # -------------------------------------------------------------------------
    # Pie tab
    # -------------------------------------------------------------------------

    def _build_pie_tab(self) -> QWidget:
        w = QWidget()
        vlay = QVBoxLayout(w)
        vlay.setContentsMargins(8, 8, 8, 8)
        vlay.setSpacing(8)

        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;"
        )
        ctrl_inner = QWidget()
        ctrl_lay = QHBoxLayout(ctrl_inner)
        ctrl_lay.setContentsMargins(12, 8, 12, 8)
        ctrl_lay.setSpacing(12)

        ctrl_lay.addWidget(QLabel("Breakdown by:"))
        self._pie_breakdown = QComboBox()
        self._pie_breakdown.addItems(["Category", "Account Type", "Transaction Type"])
        self._pie_breakdown.setFixedWidth(160)
        ctrl_lay.addWidget(self._pie_breakdown)

        ctrl_lay.addWidget(QLabel("Show:"))
        self._pie_show_debits = QRadioButton("Debits")
        self._pie_show_debits.setChecked(True)
        self._pie_show_credits = QRadioButton("Credits")
        self._pie_show_net = QRadioButton("Net")
        grp = QButtonGroup(self)
        grp.addButton(self._pie_show_debits)
        grp.addButton(self._pie_show_credits)
        grp.addButton(self._pie_show_net)
        ctrl_lay.addWidget(self._pie_show_debits)
        ctrl_lay.addWidget(self._pie_show_credits)
        ctrl_lay.addWidget(self._pie_show_net)

        ctrl_lay.addWidget(QLabel("Account:"))
        self._pie_account = QComboBox()
        self._pie_account.setFixedWidth(160)
        ctrl_lay.addWidget(self._pie_account)

        ctrl_lay.addWidget(QLabel("From:"))
        self._pie_from = QDateEdit()
        self._pie_from.setCalendarPopup(True)
        self._pie_from.setDisplayFormat("MM/dd/yyyy")
        today = _date.today()
        self._pie_from.setDate(QDate(today.year, today.month, 1))
        self._pie_from.setFixedWidth(110)
        ctrl_lay.addWidget(self._pie_from)

        ctrl_lay.addWidget(QLabel("To:"))
        self._pie_to = QDateEdit()
        self._pie_to.setCalendarPopup(True)
        self._pie_to.setDisplayFormat("MM/dd/yyyy")
        self._pie_to.setDate(QDate.currentDate())
        self._pie_to.setFixedWidth(110)
        ctrl_lay.addWidget(self._pie_to)

        for label, slot in [("This Month", self._pie_this_month),
                             ("This Year", self._pie_this_year),
                             ("Last Year", self._pie_last_year)]:
            b = QPushButton(label)
            b.setStyleSheet(
                "QPushButton { background: transparent; color: #1565C0; border: 1px solid #C5D5E8; "
                "border-radius: 4px; padding: 3px 8px; font-size: 11px; min-height: 0; }"
                "QPushButton:hover { background: #EEF4FB; }"
            )
            b.clicked.connect(slot)
            ctrl_lay.addWidget(b)

        ctrl_lay.addStretch()

        gen_btn = QPushButton("Generate Chart")
        gen_btn.setProperty("accent", True)
        gen_btn.clicked.connect(self._generate_pie)
        ctrl_lay.addWidget(gen_btn)

        png_btn = QPushButton("Export PNG")
        png_btn.setProperty("secondary", True)
        png_btn.clicked.connect(lambda: self._export_chart('png', 'pie'))
        ctrl_lay.addWidget(png_btn)

        pdf_btn = QPushButton("Export PDF")
        pdf_btn.setProperty("secondary", True)
        pdf_btn.clicked.connect(lambda: self._export_chart('pdf', 'pie'))
        ctrl_lay.addWidget(pdf_btn)

        ctrl_scroll = QScrollArea()
        ctrl_scroll.setWidget(ctrl_inner)
        ctrl_scroll.setWidgetResizable(False)
        ctrl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        ctrl_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ctrl_scroll.setFixedHeight(ctrl_inner.sizeHint().height() + 18)
        ctrl_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        ctrl_lay2 = QVBoxLayout(ctrl)
        ctrl_lay2.setContentsMargins(0, 0, 0, 0)
        ctrl_lay2.addWidget(ctrl_scroll)

        vlay.addWidget(ctrl)

        # Canvas
        self._pie_fig = Figure(figsize=(9, 6), dpi=100)
        self._pie_canvas = FigureCanvas(self._pie_fig)
        self._pie_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay.addWidget(self._pie_canvas)

        return w

    # -------------------------------------------------------------------------
    # Bar tab
    # -------------------------------------------------------------------------

    def _build_bar_tab(self) -> QWidget:
        w = QWidget()
        vlay = QVBoxLayout(w)
        vlay.setContentsMargins(8, 8, 8, 8)
        vlay.setSpacing(8)

        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; border-radius: 6px;"
        )
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(12, 8, 12, 8)
        ctrl_lay.setSpacing(12)

        ctrl_lay.addWidget(QLabel("Year:"))
        self._bar_year = QSpinBox()
        self._bar_year.setRange(2000, 2100)
        self._bar_year.setValue(_date.today().year)
        self._bar_year.setFixedWidth(70)
        ctrl_lay.addWidget(self._bar_year)

        ctrl_lay.addWidget(QLabel("Account:"))
        self._bar_account = QComboBox()
        self._bar_account.setFixedWidth(160)
        ctrl_lay.addWidget(self._bar_account)

        ctrl_lay.addStretch()

        gen_btn = QPushButton("Generate Chart")
        gen_btn.setProperty("accent", True)
        gen_btn.clicked.connect(self._generate_bar)
        ctrl_lay.addWidget(gen_btn)

        png_btn = QPushButton("Export PNG")
        png_btn.setProperty("secondary", True)
        png_btn.clicked.connect(lambda: self._export_chart('png', 'bar'))
        ctrl_lay.addWidget(png_btn)

        pdf_btn = QPushButton("Export PDF")
        pdf_btn.setProperty("secondary", True)
        pdf_btn.clicked.connect(lambda: self._export_chart('pdf', 'bar'))
        ctrl_lay.addWidget(pdf_btn)

        vlay.addWidget(ctrl)

        # Canvas
        self._bar_fig = Figure(figsize=(11, 6), dpi=100)
        self._bar_canvas = FigureCanvas(self._bar_fig)
        self._bar_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vlay.addWidget(self._bar_canvas)

        return w

    # -------------------------------------------------------------------------
    # Account loading
    # -------------------------------------------------------------------------

    def _load_accounts(self):
        self._accounts = self.db.get_accounts_for_user(self.user_id)
        for combo in [self._pie_account, self._bar_account]:
            combo.clear()
            combo.addItem("All Accounts", None)
            for acc in self._accounts:
                combo.addItem(acc['name'], acc['id'])

    def refresh(self):
        self._load_accounts()

    # -------------------------------------------------------------------------
    # Pie date helpers
    # -------------------------------------------------------------------------

    def _pie_this_month(self):
        today = _date.today()
        self._pie_from.setDate(QDate(today.year, today.month, 1))
        self._pie_to.setDate(QDate.currentDate())

    def _pie_this_year(self):
        today = _date.today()
        self._pie_from.setDate(QDate(today.year, 1, 1))
        self._pie_to.setDate(QDate(today.year, 12, 31))

    def _pie_last_year(self):
        today = _date.today()
        y = today.year - 1
        self._pie_from.setDate(QDate(y, 1, 1))
        self._pie_to.setDate(QDate(y, 12, 31))

    # -------------------------------------------------------------------------
    # Generate Pie
    # -------------------------------------------------------------------------

    def _generate_pie(self):
        start = self._pie_from.date().toString("yyyy-MM-dd")
        end = self._pie_to.date().toString("yyyy-MM-dd")
        account_id = self._pie_account.currentData()
        breakdown = self._pie_breakdown.currentText()

        if self._pie_show_debits.isChecked():
            direction = 'debit'
            show_label = "Debits"
        elif self._pie_show_credits.isChecked():
            direction = 'credit'
            show_label = "Credits"
        else:
            direction = 'debit'
            show_label = "Net"

        if breakdown == "Category":
            data = self.db.get_category_totals(
                account_id, start, end, direction, user_id=self.user_id
            )
            labels = [d['category_name'] for d in data]
            values = [d['total'] for d in data]
        elif breakdown == "Account Type":
            data = self._get_by_account_type(start, end, direction, account_id)
            labels = list(data.keys())
            values = list(data.values())
        else:  # Transaction Type
            data = self._get_by_transaction_type(start, end, direction, account_id)
            labels = list(data.keys())
            values = list(data.values())

        # Filter zero values
        filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
        if not filtered:
            self._pie_fig.clear()
            ax = self._pie_fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data for selected range",
                    ha='center', va='center', fontsize=14, color='#888')
            ax.axis('off')
            self._pie_canvas.draw()
            return

        labels, values = zip(*filtered)
        total = sum(values)

        self._pie_fig.clear()
        ax = self._pie_fig.add_subplot(111)

        colors = (CHART_COLORS * 10)[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%\n{format_currency(pct/100*total)}",
            pctdistance=0.75,
            wedgeprops=dict(width=0.55),  # donut
            startangle=90
        )
        for at in autotexts:
            at.set_fontsize(8)

        ax.legend(
            wedges, [f"{l}  {format_currency(v)}" for l, v in zip(labels, values)],
            loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        title_text = f"{breakdown} {show_label}"
        if account_id:
            acc_name = next((a['name'] for a in self._accounts if a['id'] == account_id), "")
            title_text += f" — {acc_name}"
        title_text += f"\n{start} to {end}"

        ax.set_title(title_text, fontsize=12, fontweight='bold', color='#0D2B5C', pad=16)

        # Center total
        ax.text(0, 0, format_currency(total), ha='center', va='center',
                fontsize=13, fontweight='bold', color='#0D2B5C')

        self._pie_fig.tight_layout()
        self._pie_canvas.draw()

    def _get_by_account_type(self, start, end, direction, account_id):
        if account_id:
            accounts = [a for a in self._accounts if a['id'] == account_id]
        else:
            accounts = self._accounts
        result = {}
        for acc in accounts:
            data = self.db.get_category_totals(acc['id'], start, end, direction)
            atype = acc['type']
            total = sum(d['total'] for d in data)
            result[atype] = result.get(atype, 0) + total
        return result

    def _get_by_transaction_type(self, start, end, direction, account_id):
        if account_id:
            account_ids = [account_id]
        else:
            account_ids = [a['id'] for a in self._accounts]

        col = 'debit' if direction == 'debit' else 'credit'
        result = {}
        for aid in account_ids:
            rows = self.db._fetchall(
                f"""SELECT type, SUM({col}) as total FROM transactions
                    WHERE account_id=? AND date>=? AND date<=? AND {col}>0
                    GROUP BY type""",
                (aid, start, end)
            )
            for r in rows:
                t = r['type'] or 'OTHER'
                result[t] = result.get(t, 0) + (r['total'] or 0)
        return result

    # -------------------------------------------------------------------------
    # Generate Bar
    # -------------------------------------------------------------------------

    def _generate_bar(self):
        year = self._bar_year.value()
        account_id = self._bar_account.currentData()

        if account_id:
            monthly = self.db.get_monthly_totals(account_id, year)
        else:
            monthly = self.db.get_monthly_totals_all_accounts(year, self.user_id)

        # Build full 12-month data
        income_data = [0.0] * 12
        expense_data = [0.0] * 12
        for m, debits, credits in monthly:
            if 1 <= m <= 12:
                income_data[m - 1] = credits
                expense_data[m - 1] = debits

        net_data = [income_data[i] - expense_data[i] for i in range(12)]

        self._bar_fig.clear()
        ax = self._bar_fig.add_subplot(111)

        x = range(12)
        bar_width = 0.35
        offset = bar_width / 2

        # Income bars (up)
        x_pos = [i - offset for i in x]
        ax.bar(x_pos, income_data, width=bar_width,
               color="#1565C0", label="Income", zorder=3)

        # Expense bars (down, negative)
        x_pos2 = [i + offset for i in x]
        ax.bar(x_pos2, [-e for e in expense_data], width=bar_width,
               color="#0D2B5C", hatch='/////', label="Expenses", zorder=3,
               edgecolor='white', linewidth=0.5)

        # Net line
        ax.plot(list(x), net_data, color="#E07B39", linewidth=2.5,
                marker='o', markersize=6, label="Net", zorder=4)
        for i, v in enumerate(net_data):
            if v != 0:
                ax.annotate(
                    format_currency(v),
                    (i, v),
                    textcoords="offset points",
                    xytext=(0, 10 if v >= 0 else -18),
                    ha='center', fontsize=7, color='#E07B39', fontweight='bold'
                )

        # Zero line
        ax.axhline(0, color='black', linewidth=1.5, zorder=5)

        ax.set_xticks(list(x))
        ax.set_xticklabels(MONTH_ABBR, fontsize=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda val, _: format_currency(val) if val >= 0 else f"-{format_currency(-val)}"
        ))

        ax.grid(axis='y', color='#e0e8f0', linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)

        title = f"Monthly Income vs. Expenses — {year}"
        if account_id:
            acc_name = next((a['name'] for a in self._accounts if a['id'] == account_id), "")
            title += f"  ({acc_name})"
        ax.set_title(title, fontsize=12, fontweight='bold', color='#0D2B5C', pad=12)
        ax.legend(loc='upper right', fontsize=10)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        self._bar_fig.tight_layout()
        self._bar_canvas.draw()

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def _export_chart(self, fmt: str, chart: str):
        ext = fmt.upper()
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export {ext}", f"chart.{fmt}",
            f"{ext} Files (*.{fmt});;All Files (*)"
        )
        if not path:
            return
        fig = self._pie_fig if chart == 'pie' else self._bar_fig
        try:
            fig.savefig(path, dpi=150, bbox_inches='tight', format=fmt)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", str(e))
