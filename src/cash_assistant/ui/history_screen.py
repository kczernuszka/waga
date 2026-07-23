"""PySide6 sales history screen."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cash_assistant.controller.app_controller import AppController
from cash_assistant.controller.labels import (
    HISTORY_BACK_BUTTON_TEXT,
    HISTORY_CHANGE_COLUMN,
    HISTORY_CHANGE_LABEL,
    HISTORY_CREATED_AT_COLUMN,
    HISTORY_CREATED_AT_LABEL,
    HISTORY_DETAILS_GROUP_TITLE,
    HISTORY_ITEM_CODE_COLUMN,
    HISTORY_ITEMS_COUNT_COLUMN,
    HISTORY_ITEMS_GROUP_TITLE,
    HISTORY_LIST_GROUP_TITLE,
    HISTORY_NO_SALES_TEXT,
    HISTORY_PAID_COLUMN,
    HISTORY_PAID_LABEL,
    HISTORY_RAW_TOTAL_LABEL,
    HISTORY_REFRESH_BUTTON_TEXT,
    HISTORY_ROUNDED_TOTAL_COLUMN,
    HISTORY_ROUNDED_TOTAL_LABEL,
    HISTORY_SALE_ID_COLUMN,
    HISTORY_SALE_ID_LABEL,
    HISTORY_SCREEN_TITLE,
    SALES_CART_LINE_TOTAL_COLUMN,
    SALES_CART_PRODUCT_COLUMN,
    SALES_CART_QUANTITY_COLUMN,
    SALES_CART_UNIT_PRICE_COLUMN,
)
from cash_assistant.controller.view_state import (
    SaleDetailsViewState,
    SaleSummaryViewState,
)


class HistoryScreen(QWidget):
    def __init__(
        self,
        controller: AppController,
        *,
        on_back_to_sales: Callable[[], None],
    ) -> None:
        super().__init__()
        self._controller = controller
        self._on_back_to_sales = on_back_to_sales
        self._sales: list[SaleSummaryViewState] = []
        self._selected_sale_id: int | None = None
        self._is_refreshing = False

        self._title_label = QLabel(HISTORY_SCREEN_TITLE)
        self._no_sales_label = QLabel(HISTORY_NO_SALES_TEXT)
        self._sales_table = self._create_sales_table()
        self._sale_id_value = QLabel()
        self._created_at_value = QLabel()
        self._raw_total_value = QLabel()
        self._rounded_total_value = QLabel()
        self._paid_value = QLabel()
        self._change_value = QLabel()
        self._items_table = self._create_items_table()
        self._refresh_button = QPushButton(HISTORY_REFRESH_BUTTON_TEXT)
        self._back_button = QPushButton(HISTORY_BACK_BUTTON_TEXT)

        self._build_layout()
        self._connect_signals()
        self.refresh()

    def refresh(self) -> None:
        self._sales = self._controller.list_sales_for_history()
        self._refresh_sales_table()

        if not self._sales:
            self._selected_sale_id = None
            self._clear_details()
            return

        sale_id = self._selected_sale_id
        if sale_id not in {sale.sale_id for sale in self._sales}:
            sale_id = self._sales[0].sale_id
        self._select_sale_row(sale_id)
        self._load_sale_details(sale_id)

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self._title_label)

        content_layout = QHBoxLayout()
        content_layout.addWidget(self._build_sales_list_group(), stretch=2)
        content_layout.addWidget(self._build_details_group(), stretch=3)
        root_layout.addLayout(content_layout)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self._refresh_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self._back_button)
        root_layout.addLayout(actions_layout)

    def _build_sales_list_group(self) -> QGroupBox:
        group = QGroupBox(HISTORY_LIST_GROUP_TITLE)
        layout = QVBoxLayout(group)
        layout.addWidget(self._no_sales_label)
        layout.addWidget(self._sales_table)
        return group

    def _build_details_group(self) -> QGroupBox:
        group = QGroupBox(HISTORY_DETAILS_GROUP_TITLE)
        layout = QVBoxLayout(group)

        summary_layout = QFormLayout()
        summary_layout.addRow(HISTORY_SALE_ID_LABEL, self._sale_id_value)
        summary_layout.addRow(HISTORY_CREATED_AT_LABEL, self._created_at_value)
        summary_layout.addRow(HISTORY_RAW_TOTAL_LABEL, self._raw_total_value)
        summary_layout.addRow(HISTORY_ROUNDED_TOTAL_LABEL, self._rounded_total_value)
        summary_layout.addRow(HISTORY_PAID_LABEL, self._paid_value)
        summary_layout.addRow(HISTORY_CHANGE_LABEL, self._change_value)
        layout.addLayout(summary_layout)

        layout.addWidget(QLabel(HISTORY_ITEMS_GROUP_TITLE))
        layout.addWidget(self._items_table)
        return group

    def _connect_signals(self) -> None:
        self._refresh_button.clicked.connect(self.refresh)
        self._back_button.clicked.connect(self._on_back_to_sales)
        self._sales_table.itemSelectionChanged.connect(self._load_selected_sale_details)

    def _refresh_sales_table(self) -> None:
        self._is_refreshing = True
        self._sales_table.blockSignals(True)
        try:
            self._no_sales_label.setVisible(not self._sales)
            self._sales_table.setRowCount(len(self._sales))
            for row, sale in enumerate(self._sales):
                self._set_sale_table_item(row, 0, str(sale.sale_id), sale.sale_id)
                self._set_sale_table_item(row, 1, sale.created_at_text, sale.sale_id)
                self._set_sale_table_item(row, 2, sale.rounded_total_text, sale.sale_id)
                self._set_sale_table_item(row, 3, sale.paid_text, sale.sale_id)
                self._set_sale_table_item(row, 4, sale.change_text, sale.sale_id)
                self._set_sale_table_item(row, 5, str(sale.items_count), sale.sale_id)
            self._sales_table.resizeColumnsToContents()
        finally:
            self._sales_table.blockSignals(False)
            self._is_refreshing = False

    def _set_sale_table_item(self, row: int, column: int, text: str, sale_id: int) -> None:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, sale_id)
        self._sales_table.setItem(row, column, item)

    def _select_sale_row(self, sale_id: int) -> None:
        for row in range(self._sales_table.rowCount()):
            item = self._sales_table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == sale_id:
                self._sales_table.selectRow(row)
                return

    def _load_selected_sale_details(self) -> None:
        if self._is_refreshing:
            return
        sale_id = self._selected_table_sale_id()
        if sale_id is None:
            self._clear_details()
            return
        self._load_sale_details(sale_id)

    def _selected_table_sale_id(self) -> int | None:
        row = self._sales_table.currentRow()
        if row < 0:
            return None
        item = self._sales_table.item(row, 0)
        if item is None:
            return None
        sale_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(sale_id, int):
            return sale_id
        return None

    def _load_sale_details(self, sale_id: int) -> None:
        details = self._controller.read_sale_details(sale_id)
        if details is None:
            self._selected_sale_id = None
            self._clear_details()
            return

        self._selected_sale_id = sale_id
        self._fill_details(details)

    def _fill_details(self, details: SaleDetailsViewState) -> None:
        self._sale_id_value.setText(str(details.sale_id))
        self._created_at_value.setText(details.created_at_text)
        self._raw_total_value.setText(details.raw_total_text)
        self._rounded_total_value.setText(details.rounded_total_text)
        self._paid_value.setText(details.paid_text)
        self._change_value.setText(details.change_text)

        self._items_table.setRowCount(len(details.items))
        for row, item in enumerate(details.items):
            self._items_table.setItem(row, 0, QTableWidgetItem(item.product_code))
            self._items_table.setItem(row, 1, QTableWidgetItem(item.product_name))
            self._items_table.setItem(row, 2, QTableWidgetItem(item.quantity_text))
            self._items_table.setItem(row, 3, QTableWidgetItem(item.unit_price_text))
            self._items_table.setItem(row, 4, QTableWidgetItem(item.line_total_text))
        self._items_table.resizeColumnsToContents()

    def _clear_details(self) -> None:
        self._sale_id_value.setText("")
        self._created_at_value.setText("")
        self._raw_total_value.setText("")
        self._rounded_total_value.setText("")
        self._paid_value.setText("")
        self._change_value.setText("")
        self._items_table.setRowCount(0)

    def _create_sales_table(self) -> QTableWidget:
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            [
                HISTORY_SALE_ID_COLUMN,
                HISTORY_CREATED_AT_COLUMN,
                HISTORY_ROUNDED_TOTAL_COLUMN,
                HISTORY_PAID_COLUMN,
                HISTORY_CHANGE_COLUMN,
                HISTORY_ITEMS_COUNT_COLUMN,
            ]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        return table

    def _create_items_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            [
                HISTORY_ITEM_CODE_COLUMN,
                SALES_CART_PRODUCT_COLUMN,
                SALES_CART_QUANTITY_COLUMN,
                SALES_CART_UNIT_PRICE_COLUMN,
                SALES_CART_LINE_TOTAL_COLUMN,
            ]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        return table
