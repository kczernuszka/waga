"""Product settings screen."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cash_assistant.controller.app_controller import AppController
from cash_assistant.controller.labels import (
    CURRENCY_TEXT,
    ERROR_DIALOG_TITLE,
    SETTINGS_ACTIVE_LABEL,
    SETTINGS_ADD_BUTTON_TEXT,
    SETTINGS_BACK_TO_SALES_BUTTON_TEXT,
    SETTINGS_CANCEL_BUTTON_TEXT,
    SETTINGS_EDIT_BUTTON_TEXT,
    SETTINGS_FORM_GROUP_TITLE,
    SETTINGS_LIST_GROUP_TITLE,
    SETTINGS_NAME_LABEL,
    SETTINGS_PRICE_LABEL,
    SETTINGS_PRODUCT_NAME_COLUMN,
    SETTINGS_PRODUCT_PRICE_COLUMN,
    SETTINGS_PRODUCT_SORT_ORDER_COLUMN,
    SETTINGS_PRODUCT_STATUS_COLUMN,
    SETTINGS_PRODUCT_UNIT_COLUMN,
    SETTINGS_SAVE_BUTTON_TEXT,
    SETTINGS_SCREEN_TITLE,
    SETTINGS_SORT_ORDER_LABEL,
    SETTINGS_UNIT_LABEL,
)
from cash_assistant.controller.view_state import (
    ProductEditInput,
    ProductEditViewState,
    ProductListItemViewState,
)


class SettingsScreen(QWidget):
    def __init__(
        self,
        controller: AppController,
        *,
        on_back_to_sales: Callable[[], None],
        on_products_changed: Callable[[], None],
    ) -> None:
        super().__init__()
        self._controller = controller
        self._on_back_to_sales = on_back_to_sales
        self._on_products_changed = on_products_changed
        self._products: list[ProductListItemViewState] = []
        self._edit_view_state: ProductEditViewState | None = None
        self._is_refreshing = False

        self._title_label = QLabel(SETTINGS_SCREEN_TITLE)
        self._products_table = self._create_products_table()
        self._name_input = QLineEdit()
        self._unit_input = QComboBox()
        self._price_input = QLineEdit()
        self._active_input = QCheckBox(SETTINGS_ACTIVE_LABEL)
        self._sort_order_input = QSpinBox()
        self._sort_order_input.setRange(0, 999_999)

        self._add_button = QPushButton(SETTINGS_ADD_BUTTON_TEXT)
        self._edit_button = QPushButton(SETTINGS_EDIT_BUTTON_TEXT)
        self._save_button = QPushButton(SETTINGS_SAVE_BUTTON_TEXT)
        self._cancel_button = QPushButton(SETTINGS_CANCEL_BUTTON_TEXT)
        self._back_button = QPushButton(SETTINGS_BACK_TO_SALES_BUTTON_TEXT)

        self._build_layout()
        self._connect_signals()
        self.refresh()
        self._load_form(product_id=None)

    def refresh(self) -> None:
        self._products = self._controller.list_products_for_settings()
        self._refresh_products_table()

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self._title_label)

        content_layout = QHBoxLayout()
        content_layout.addWidget(self._build_list_group(), stretch=2)
        content_layout.addWidget(self._build_form_group(), stretch=1)
        root_layout.addLayout(content_layout)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self._add_button)
        actions_layout.addWidget(self._edit_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self._back_button)
        root_layout.addLayout(actions_layout)

    def _build_list_group(self) -> QGroupBox:
        group = QGroupBox(SETTINGS_LIST_GROUP_TITLE)
        layout = QVBoxLayout(group)
        layout.addWidget(self._products_table)
        return group

    def _build_form_group(self) -> QGroupBox:
        group = QGroupBox(SETTINGS_FORM_GROUP_TITLE)
        layout = QVBoxLayout(group)

        form_layout = QFormLayout()
        form_layout.addRow(SETTINGS_NAME_LABEL, self._name_input)
        form_layout.addRow(SETTINGS_UNIT_LABEL, self._unit_input)
        form_layout.addRow(SETTINGS_PRICE_LABEL, self._price_input)
        form_layout.addRow("", self._active_input)
        form_layout.addRow(SETTINGS_SORT_ORDER_LABEL, self._sort_order_input)
        layout.addLayout(form_layout)

        form_actions_layout = QHBoxLayout()
        form_actions_layout.addWidget(self._save_button)
        form_actions_layout.addWidget(self._cancel_button)
        layout.addLayout(form_actions_layout)
        layout.addStretch()
        return group

    def _connect_signals(self) -> None:
        self._add_button.clicked.connect(lambda: self._load_form(product_id=None))
        self._edit_button.clicked.connect(self._edit_selected_product)
        self._save_button.clicked.connect(self._save_product)
        self._cancel_button.clicked.connect(lambda: self._load_form(product_id=None))
        self._back_button.clicked.connect(self._on_back_to_sales)
        self._products_table.itemDoubleClicked.connect(lambda _item: self._edit_selected_product())

    def _refresh_products_table(self) -> None:
        self._products_table.setRowCount(len(self._products))
        for row, product in enumerate(self._products):
            self._set_table_item(row, 0, product.name, product.product_id)
            self._set_table_item(row, 1, product.unit_text, product.product_id)
            self._set_table_item(row, 2, product.price_text, product.product_id)
            self._set_table_item(row, 3, product.active_text, product.product_id)
            self._set_table_item(row, 4, str(product.sort_order), product.product_id)
        self._products_table.resizeColumnsToContents()

    def _set_table_item(self, row: int, column: int, text: str, product_id: int) -> None:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, product_id)
        self._products_table.setItem(row, column, item)

    def _load_form(self, product_id: int | None) -> None:
        try:
            view_state = self._controller.prepare_product_edit_view_state(product_id)
        except ValueError as error:
            self._show_error(str(error))
            return
        self._edit_view_state = view_state
        self._fill_form(view_state)

    def _fill_form(self, view_state: ProductEditViewState) -> None:
        self._is_refreshing = True
        try:
            self._name_input.setText(view_state.name)
            self._unit_input.clear()
            for option in view_state.unit_options:
                self._unit_input.addItem(option.label, option.unit_code)
            self._select_unit(view_state.unit_code)
            self._price_input.setText(_format_price_input(view_state.price_grosze))
            self._active_input.setChecked(view_state.active)
            self._sort_order_input.setValue(view_state.sort_order)
        finally:
            self._is_refreshing = False

    def _select_unit(self, unit_code: str) -> None:
        index = self._unit_input.findData(unit_code)
        if index >= 0:
            self._unit_input.setCurrentIndex(index)

    def _edit_selected_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            self._show_error("select a product first")
            return
        self._load_form(product_id)

    def _selected_product_id(self) -> int | None:
        row = self._products_table.currentRow()
        if row < 0:
            return None
        item = self._products_table.item(row, 0)
        if item is None:
            return None
        product_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(product_id, int):
            return product_id
        return None

    def _save_product(self) -> None:
        if self._edit_view_state is None:
            self._load_form(product_id=None)

        try:
            product_input = self._product_input_from_form()
            saved_product = self._controller.save_product_from_input(product_input)
        except ValueError as error:
            self._show_error(str(error))
            return

        self.refresh()
        self._on_products_changed()
        self._load_form(saved_product.product_id)

    def _product_input_from_form(self) -> ProductEditInput:
        if self._edit_view_state is None:
            raise ValueError("product form is not initialized")

        unit_code = self._unit_input.currentData()
        if not isinstance(unit_code, str):
            raise ValueError("unit is required")

        return ProductEditInput(
            product_id=self._edit_view_state.product_id,
            name=self._name_input.text().strip(),
            unit_code=unit_code,
            price_grosze=_parse_price_grosze(self._price_input.text()),
            active=self._active_input.isChecked(),
            sort_order=self._sort_order_input.value(),
        )

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, ERROR_DIALOG_TITLE, message)

    def _create_products_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            [
                SETTINGS_PRODUCT_NAME_COLUMN,
                SETTINGS_PRODUCT_UNIT_COLUMN,
                SETTINGS_PRODUCT_PRICE_COLUMN,
                SETTINGS_PRODUCT_STATUS_COLUMN,
                SETTINGS_PRODUCT_SORT_ORDER_COLUMN,
            ]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        return table


def _format_price_input(price_grosze: int) -> str:
    if price_grosze < 0:
        raise ValueError("price_grosze cannot be negative")
    zloty = price_grosze // 100
    grosze = price_grosze % 100
    return f"{zloty},{grosze:02d}"


def _parse_price_grosze(text: str) -> int:
    normalized = text.strip().replace(" ", "")
    if normalized.endswith(CURRENCY_TEXT):
        normalized = normalized.removesuffix(CURRENCY_TEXT)
    if normalized == "":
        raise ValueError("price is required")
    if normalized.startswith("-"):
        raise ValueError("price cannot be negative")
    if normalized.count(",") > 1:
        raise ValueError("price must contain at most one comma")
    if "," not in normalized:
        if not normalized.isdecimal():
            raise ValueError("price must contain only digits and comma")
        return int(normalized) * 100

    zloty_text, grosze_text = normalized.split(",", maxsplit=1)
    if zloty_text == "":
        zloty_text = "0"
    if grosze_text == "":
        grosze_text = "0"
    if not zloty_text.isdecimal() or not grosze_text.isdecimal():
        raise ValueError("price must contain only digits and comma")
    if len(grosze_text) > 2:
        raise ValueError("price can contain at most two decimal places")
    return int(zloty_text) * 100 + int((grosze_text + "00")[:2])
