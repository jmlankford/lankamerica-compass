"""
categories_widget.py — Category management widget
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QDialog, QComboBox, QFormLayout, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from src.database import Database
from src.utils import format_currency
from src.ui.styles import COLOR_NAVY, COLOR_WHITE, COLOR_BORDER, COLOR_RED, COLOR_GREEN


class CategoriesWidget(QWidget):
    def __init__(self, db: Database, user_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title = QLabel("Categories")
        title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Manage your income and expense categories.")
        subtitle.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(subtitle)

        # Two panels
        panels = QHBoxLayout()
        panels.setSpacing(16)

        self._expense_panel = self._build_panel("Expense Categories", "expense")
        self._income_panel = self._build_panel("Income Categories", "income")

        panels.addWidget(self._expense_panel)
        panels.addWidget(self._income_panel)
        layout.addLayout(panels)

    def _build_panel(self, title: str, cat_type: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_WHITE}; border: 1px solid {COLOR_BORDER}; border-radius: 8px;"
        )
        vlay = QVBoxLayout(frame)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 14px; font-weight: 700; border: none;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        vlay.addLayout(hdr)

        # List
        list_widget = QListWidget()
        list_widget.setObjectName(f"cat_list_{cat_type}")
        list_widget.setAlternatingRowColors(True)
        list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        list_widget.setMinimumHeight(350)
        vlay.addWidget(list_widget)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        add_btn = QPushButton("+ Add")
        add_btn.setStyleSheet(self._small_btn_style(COLOR_NAVY))
        add_btn.clicked.connect(lambda: self._add_category(cat_type, list_widget))
        btn_row.addWidget(add_btn)

        rename_btn = QPushButton("✏ Rename")
        rename_btn.setStyleSheet(self._small_btn_style("#546E7A"))
        rename_btn.clicked.connect(lambda: self._rename_category(list_widget))
        btn_row.addWidget(rename_btn)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setStyleSheet(self._small_btn_style(COLOR_RED))
        del_btn.clicked.connect(lambda: self._delete_category(list_widget, cat_type))
        btn_row.addWidget(del_btn)

        up_btn = QPushButton("↑")
        up_btn.setFixedWidth(32)
        up_btn.setStyleSheet(self._small_btn_style("#1565C0"))
        up_btn.clicked.connect(lambda: self._move_category(list_widget, cat_type, -1))
        btn_row.addWidget(up_btn)

        down_btn = QPushButton("↓")
        down_btn.setFixedWidth(32)
        down_btn.setStyleSheet(self._small_btn_style("#1565C0"))
        down_btn.clicked.connect(lambda: self._move_category(list_widget, cat_type, 1))
        btn_row.addWidget(down_btn)

        vlay.addLayout(btn_row)

        if cat_type == "expense":
            self._expense_list = list_widget
        else:
            self._income_list = list_widget

        return frame

    def _small_btn_style(self, bg: str) -> str:
        return (
            f"QPushButton {{ background-color: {bg}; color: white; border: none; "
            f"border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 600; "
            f"min-height: 0; }}"
            f"QPushButton:hover {{ opacity: 0.85; }}"
        )

    def refresh(self):
        self._load_list(self._expense_list, "expense")
        self._load_list(self._income_list, "income")

    def _load_list(self, list_widget: QListWidget, cat_type: str):
        list_widget.clear()
        cats = self.db.get_categories_by_type(cat_type)
        for cat in cats:
            count = self.db.get_category_transaction_count(cat['id'])
            total = self.db.get_category_total(cat['id'])
            label = f"{cat['name']}  ({count} tx, {format_currency(total)})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, cat)
            list_widget.addItem(item)

    def _get_selected(self, list_widget: QListWidget):
        item = list_widget.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _add_category(self, cat_type: str, list_widget: QListWidget):
        name, ok = QInputDialog.getText(
            self, "Add Category", f"New {cat_type.capitalize()} Category Name:"
        )
        if ok and name.strip():
            try:
                self.db.create_category(name.strip(), cat_type)
                self._load_list(list_widget, cat_type)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _rename_category(self, list_widget: QListWidget):
        cat = self._get_selected(list_widget)
        if not cat:
            QMessageBox.information(self, "Rename", "Please select a category first.")
            return
        name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:", text=cat['name']
        )
        if ok and name.strip():
            try:
                self.db.rename_category(cat['id'], name.strip())
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_category(self, list_widget: QListWidget, cat_type: str):
        cat = self._get_selected(list_widget)
        if not cat:
            QMessageBox.information(self, "Delete", "Please select a category first.")
            return

        count = self.db.get_category_transaction_count(cat['id'])
        reassign_to = None

        if count > 0:
            dlg = ReassignDialog(self, self.db, cat['id'], cat_type)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            reassign_to = dlg.get_reassign_id()

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete category '{cat['name']}'?" +
            (f" {count} transactions will be reassigned." if count > 0 else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_category(cat['id'], reassign_to)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _move_category(self, list_widget: QListWidget, cat_type: str, direction: int):
        current_row = list_widget.currentRow()
        if current_row < 0:
            return
        new_row = current_row + direction
        if new_row < 0 or new_row >= list_widget.count():
            return

        cats = self.db.get_categories_by_type(cat_type)
        if current_row >= len(cats) or new_row >= len(cats):
            return

        cat_a = cats[current_row]
        cat_b = cats[new_row]

        # Swap sort orders
        self.db.reorder_category(cat_a['id'], cat_b['sort_order'])
        self.db.reorder_category(cat_b['id'], cat_a['sort_order'])
        self._load_list(list_widget, cat_type)
        list_widget.setCurrentRow(new_row)


class ReassignDialog(QDialog):
    def __init__(self, parent, db: Database, exclude_id: int, cat_type: str):
        super().__init__(parent)
        self.setWindowTitle("Reassign Transactions")
        self.setFixedSize(380, 180)
        self.db = db
        self._result_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "This category has transactions. Choose a category to reassign them to:"
        ))

        self._combo = QComboBox()
        cats = db.get_categories_by_type(cat_type)
        self._id_map = {}
        for c in cats:
            if c['id'] != exclude_id:
                self._combo.addItem(c['name'])
                self._id_map[c['name']] = c['id']
        layout.addWidget(self._combo)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setProperty("secondary", True)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        ok = QPushButton("Reassign & Delete")
        ok.setProperty("danger", True)
        ok.clicked.connect(self._accept)
        btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _accept(self):
        name = self._combo.currentText()
        self._result_id = self._id_map.get(name)
        self.accept()

    def get_reassign_id(self):
        return self._result_id
