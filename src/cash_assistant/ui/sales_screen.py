"""Minimal PySide6 sales screen."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayoutItem,
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
from cash_assistant.controller.keyboard_controller import Command, KeyboardController
from cash_assistant.controller.labels import (
    ERROR_DIALOG_TITLE,
    INFORMATION_DIALOG_TITLE,
    NO_CART_ITEMS_TEXT,
    SALE_SAVED_TEXT,
    SALES_CANCEL_BUTTON_TEXT,
    SALES_CART_GROUP_TITLE,
    SALES_CART_LINE_TOTAL_COLUMN,
    SALES_CART_PRODUCT_COLUMN,
    SALES_CART_QUANTITY_COLUMN,
    SALES_CART_UNIT_PRICE_COLUMN,
    SALES_CHANGE_LABEL,
    SALES_CLEAR_CART_BUTTON_TEXT,
    SALES_CONFIRM_BUTTON_TEXT,
    SALES_PAID_INPUT_LABEL,
    SALES_PAID_LABEL,
    SALES_PAYMENT_STATUS_ENTER_AMOUNT_TEXT,
    SALES_PAYMENT_STATUS_TOO_LOW_TEXT,
    SALES_PRODUCTS_GROUP_TITLE,
    SALES_QUANTITY_LABEL,
    SALES_REMOVE_LAST_BUTTON_TEXT,
    SALES_ROUNDED_TOTAL_LABEL,
    SALES_SAVE_BUTTON_TEXT,
    SALES_SCREEN_TITLE,
    SALES_SELECTED_PRODUCT_LABEL,
    SALES_START_PAYMENT_BUTTON_TEXT,
    SALES_WEIGHT_LABEL,
)
from cash_assistant.controller.view_state import AppState, ProductViewState, ViewState

PRODUCTS_ASSETS_PATH = Path(__file__).resolve().parents[3] / "assets" / "products"
FALLBACK_ICON_FILENAME = "fallback.png"


class SalesScreen(QWidget):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._controller = controller
        self._keyboard_controller = KeyboardController(controller)
        self._view_state = controller.prepare_view_state()
        self._product_buttons: list[QPushButton] = []
        self._quantity_digits = ""
        self._is_refreshing = False

        self._title_label = QLabel(SALES_SCREEN_TITLE)
        self._products_layout = QGridLayout()
        self._cart_table = self._create_cart_table()
        self._quantity_input = self._create_quantity_input()
        self._payment_input = self._create_payment_input()
        self._rounded_total_value = QLabel()
        self._selected_product_value = QLabel()
        self._weight_value = QLabel()
        self._payment_paid_value = QLabel()
        self._payment_change_value = QLabel()
        self._payment_status_value = QLabel()

        self._remove_last_button = QPushButton(SALES_REMOVE_LAST_BUTTON_TEXT)
        self._clear_cart_button = QPushButton(SALES_CLEAR_CART_BUTTON_TEXT)
        self._start_payment_button = QPushButton(SALES_START_PAYMENT_BUTTON_TEXT)
        self._confirm_selection_button = QPushButton(SALES_CONFIRM_BUTTON_TEXT)
        self._cancel_selection_button = QPushButton(SALES_CANCEL_BUTTON_TEXT)
        self._save_sale_button = QPushButton(SALES_SAVE_BUTTON_TEXT)

        self._build_layout()
        self._connect_signals()
        self.refresh()

    def refresh(self) -> None:
        self._view_state = self._controller.prepare_view_state()
        self._is_refreshing = True
        try:
            self._refresh_products_panel(self._view_state)
            self._refresh_cart(self._view_state)
            self._refresh_controls(self._view_state)
        finally:
            self._is_refreshing = False

    def handle_global_key_event(self, event: QKeyEvent) -> bool:
        command = _command_from_key_event(event)
        if command is None:
            return False

        self._run_keyboard_command(command[0], command[1])
        return True

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.handle_global_key_event(event):
            return
        super().keyPressEvent(event)

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self._title_label)

        content_layout = QHBoxLayout()
        content_layout.addWidget(self._build_cart_group(), stretch=2)
        content_layout.addWidget(self._build_products_group(), stretch=2)
        root_layout.addLayout(content_layout)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self._remove_last_button)
        actions_layout.addWidget(self._clear_cart_button)
        actions_layout.addWidget(self._start_payment_button)
        root_layout.addLayout(actions_layout)

    def _build_products_group(self) -> QGroupBox:
        group = QGroupBox(SALES_PRODUCTS_GROUP_TITLE)
        group.setLayout(self._products_layout)
        return group

    def _build_cart_group(self) -> QGroupBox:
        group = QGroupBox(SALES_CART_GROUP_TITLE)
        layout = QVBoxLayout(group)
        layout.addWidget(self._cart_table)
        layout.addLayout(_summary_row(SALES_ROUNDED_TOTAL_LABEL, self._rounded_total_value))
        return group

    def _connect_signals(self) -> None:
        self._quantity_input.valueChanged.connect(self._quantity_value_changed)
        self._payment_input.textEdited.connect(self._payment_value_changed)
        self._remove_last_button.clicked.connect(
            lambda: self._run_controller_action(self._controller.remove_last_item)
        )
        self._clear_cart_button.clicked.connect(
            lambda: self._run_controller_action(self._controller.clear_cart)
        )
        self._start_payment_button.clicked.connect(
            lambda: self._run_controller_action(self._controller.start_payment)
        )
        self._confirm_selection_button.clicked.connect(self._confirm_current_action)
        self._cancel_selection_button.clicked.connect(
            lambda: self._run_keyboard_command(Command.CANCEL)
        )
        self._save_sale_button.clicked.connect(self._save_sale)

    def _refresh_products_panel(self, view_state: ViewState) -> None:
        self._clear_products_layout()
        self._product_buttons.clear()

        if view_state.app_state is AppState.ENTERING_QUANTITY:
            self._refresh_piece_quantity_panel(view_state)
            return

        if view_state.app_state is AppState.READING_WEIGHT:
            self._refresh_weight_panel(view_state)
            return

        if view_state.app_state is AppState.PAYMENT:
            self._refresh_payment_panel(view_state)
            return

        self._refresh_product_buttons(view_state.products)

    def _refresh_product_buttons(self, products: tuple[ProductViewState, ...]) -> None:
        for index, product in enumerate(products):
            button = QPushButton(product.button_text)
            button.setMinimumHeight(72)
            button.setIcon(QIcon(str(_product_icon_path(product.icon_filename))))
            button.setIconSize(QSize(64, 64))
            button.clicked.connect(
                lambda _checked=False, product_id=product.product_id: self._run_keyboard_command(
                    Command.SELECT_PRODUCT,
                    product_id,
                )
            )
            self._product_buttons.append(button)
            self._products_layout.addWidget(button, index // 3, index % 3)

    def _refresh_piece_quantity_panel(self, view_state: ViewState) -> None:
        self._selected_product_value.setText(_selected_product_text(view_state))
        self._products_layout.addWidget(QLabel(SALES_SELECTED_PRODUCT_LABEL), 0, 0)
        self._products_layout.addWidget(self._selected_product_value, 0, 1)
        self._products_layout.addWidget(QLabel(SALES_QUANTITY_LABEL), 1, 0)
        self._products_layout.addWidget(self._quantity_input, 1, 1)
        self._products_layout.addWidget(self._confirm_selection_button, 2, 0)
        self._products_layout.addWidget(self._cancel_selection_button, 2, 1)

    def _refresh_weight_panel(self, view_state: ViewState) -> None:
        self._selected_product_value.setText(_selected_product_text(view_state))
        self._weight_value.setText(view_state.current_weight_text or "")
        self._products_layout.addWidget(QLabel(SALES_SELECTED_PRODUCT_LABEL), 0, 0)
        self._products_layout.addWidget(self._selected_product_value, 0, 1)
        self._products_layout.addWidget(QLabel(SALES_WEIGHT_LABEL), 1, 0)
        self._products_layout.addWidget(self._weight_value, 1, 1)
        self._products_layout.addWidget(self._confirm_selection_button, 2, 0)
        self._products_layout.addWidget(self._cancel_selection_button, 2, 1)

    def _refresh_payment_panel(self, view_state: ViewState) -> None:
        self._refresh_payment_status(view_state)
        self._products_layout.addLayout(
            _summary_row(SALES_ROUNDED_TOTAL_LABEL, QLabel(view_state.rounded_total_text)),
            0,
            0,
            1,
            2,
        )
        self._products_layout.addWidget(QLabel(SALES_PAID_INPUT_LABEL), 1, 0)
        self._products_layout.addWidget(self._payment_input, 1, 1)
        self._products_layout.addLayout(
            _summary_row(SALES_PAID_LABEL, self._payment_paid_value),
            2,
            0,
            1,
            2,
        )
        self._products_layout.addLayout(
            _summary_row(SALES_CHANGE_LABEL, self._payment_change_value),
            3,
            0,
            1,
            2,
        )
        self._products_layout.addWidget(self._payment_status_value, 4, 0, 1, 2)
        self._products_layout.addWidget(self._confirm_selection_button, 5, 0)
        self._products_layout.addWidget(self._save_sale_button, 5, 1)
        self._products_layout.addWidget(self._cancel_selection_button, 6, 0, 1, 2)

    def _refresh_cart(self, view_state: ViewState) -> None:
        self._cart_table.setRowCount(len(view_state.cart_items))
        if not view_state.cart_items:
            self._cart_table.setRowCount(1)
            self._cart_table.setItem(0, 0, QTableWidgetItem(NO_CART_ITEMS_TEXT))
            for column in range(1, self._cart_table.columnCount()):
                self._cart_table.setItem(0, column, QTableWidgetItem(""))
            return

        for row, item in enumerate(view_state.cart_items):
            self._cart_table.setItem(row, 0, QTableWidgetItem(item.product_name))
            self._cart_table.setItem(row, 1, QTableWidgetItem(item.quantity_text))
            self._cart_table.setItem(row, 2, QTableWidgetItem(item.unit_price_text))
            self._cart_table.setItem(row, 3, QTableWidgetItem(item.line_total_text))
        self._cart_table.resizeColumnsToContents()

    def _refresh_controls(self, view_state: ViewState) -> None:
        in_quantity_mode = view_state.app_state is AppState.ENTERING_QUANTITY
        in_payment_mode = view_state.app_state is AppState.PAYMENT

        self._rounded_total_value.setText(view_state.rounded_total_text)
        self._quantity_input.setEnabled(in_quantity_mode)
        if not in_quantity_mode:
            self._quantity_digits = ""
            self._quantity_input.setValue(1)

        self._payment_input.setEnabled(in_payment_mode)
        self._remove_last_button.setEnabled(not view_state.is_cart_empty)
        self._clear_cart_button.setEnabled(not view_state.is_cart_empty)
        self._start_payment_button.setEnabled(not view_state.is_cart_empty and not in_payment_mode)
        self._save_sale_button.setEnabled(in_payment_mode and view_state.change_grosze is not None)
        self._sync_keyboard_buffers(view_state)

    def _confirm_current_action(self) -> None:
        if self._view_state.app_state is AppState.ENTERING_QUANTITY:
            quantity = self._quantity_input.value()
            self._run_controller_action(
                lambda: self._controller.add_selected_piece_product(quantity)
            )
            return

        if self._view_state.app_state is AppState.READING_WEIGHT:
            self._run_controller_action(self._controller.add_selected_weighted_product)
            return

        if self._view_state.app_state is AppState.PAYMENT:
            self._run_keyboard_command(Command.CONFIRM)

    def _quantity_value_changed(self, quantity: int) -> None:
        if self._is_refreshing or self._view_state.app_state is not AppState.ENTERING_QUANTITY:
            return
        self._quantity_digits = str(quantity)

    def _payment_value_changed(self, text: str) -> None:
        if self._is_refreshing or self._view_state.app_state is not AppState.PAYMENT:
            return
        try:
            self._keyboard_controller.set_payment_buffer_text(text)
        except ValueError as error:
            self._show_error(str(error))
            return
        self._payment_status_value.setText(SALES_PAYMENT_STATUS_ENTER_AMOUNT_TEXT)

    def _save_sale(self) -> None:
        try:
            self._keyboard_controller.handle(Command.SAVE_SALE)
        except ValueError as error:
            self._show_error(str(error))
            return
        QMessageBox.information(self, INFORMATION_DIALOG_TITLE, SALE_SAVED_TEXT)
        self.refresh()

    def _run_keyboard_command(self, command: Command, payload: object | None = None) -> None:
        try:
            self._keyboard_controller.handle(command, payload)
        except ValueError as error:
            self._show_error(str(error))
            return
        self.refresh()

    def _run_controller_action(self, action: Callable[[], object]) -> None:
        try:
            action()
        except ValueError as error:
            self._show_error(str(error))
            return
        self.refresh()

    def _sync_keyboard_buffers(self, view_state: ViewState) -> None:
        if view_state.app_state is AppState.PAYMENT:
            payment_text = self._keyboard_controller.payment_buffer_text
            self._payment_input.setText(payment_text)
            return

        if view_state.app_state is not AppState.ENTERING_QUANTITY:
            return

        quantity_text = self._keyboard_controller.quantity_buffer_text
        quantity = int(quantity_text) if quantity_text else 1
        self._quantity_input.setValue(quantity)

    def _refresh_payment_status(self, view_state: ViewState) -> None:
        self._payment_paid_value.setText(view_state.paid_text or "")
        self._payment_change_value.setText(view_state.change_text or "")

        if view_state.missing_grosze is not None:
            self._payment_status_value.setText(SALES_PAYMENT_STATUS_TOO_LOW_TEXT)
            return

        if view_state.change_grosze is not None:
            self._payment_status_value.setText("")
            return

        self._payment_status_value.setText(SALES_PAYMENT_STATUS_ENTER_AMOUNT_TEXT)

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, ERROR_DIALOG_TITLE, message)

    def _clear_products_layout(self) -> None:
        while self._products_layout.count():
            item = self._products_layout.takeAt(0)
            if item is None:
                continue
            _clear_layout_item(item)

    def _create_cart_table(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(
            [
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

    def _create_quantity_input(self) -> QSpinBox:
        input_widget = QSpinBox()
        input_widget.setRange(1, 999)
        input_widget.setValue(1)
        input_widget.setEnabled(False)
        return input_widget

    def _create_payment_input(self) -> QLineEdit:
        input_widget = QLineEdit()
        input_widget.setPlaceholderText("0,00")
        input_widget.setEnabled(False)
        return input_widget


def _summary_row(label_text: str, value_label: QLabel) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.addWidget(QLabel(label_text))
    layout.addStretch()
    layout.addWidget(value_label)
    return layout


def _clear_layout_item(item: QLayoutItem) -> None:
    widget = item.widget()
    if widget is not None:
        widget.setParent(None)
        return

    layout = item.layout()
    if layout is None:
        return

    while layout.count():
        child = layout.takeAt(0)
        if child is not None:
            _clear_layout_item(child)


def _selected_product_text(view_state: ViewState) -> str:
    if view_state.selected_product is None:
        return ""
    return view_state.selected_product.name


def _product_icon_path(icon_filename: str) -> Path:
    candidate = PRODUCTS_ASSETS_PATH / Path(icon_filename).name
    if candidate.is_file():
        return candidate
    return PRODUCTS_ASSETS_PATH / FALLBACK_ICON_FILENAME


def _command_from_key_event(event: QKeyEvent) -> tuple[Command, object | None] | None:
    digit = _digit_from_key_event(event)
    if digit is not None:
        return Command.DIGIT_TYPED, digit

    if event.text() == ",":
        return Command.DECIMAL_SEPARATOR_TYPED, None

    command_by_key = {
        Qt.Key.Key_Return: Command.CONFIRM,
        Qt.Key.Key_Enter: Command.CONFIRM,
        Qt.Key.Key_Plus: Command.CONFIRM,
        Qt.Key.Key_Escape: Command.CANCEL,
        Qt.Key.Key_Backspace: Command.BACKSPACE,
        Qt.Key.Key_Minus: Command.REMOVE_LAST_ITEM,
    }
    command = command_by_key.get(Qt.Key(event.key()))
    if command is None:
        return None
    return command, None


def _digit_from_key_event(event: QKeyEvent) -> str | None:
    text = event.text()
    # Numpad digits should work independently of widget focus; Qt usually exposes
    # both numpad and top-row numbers as one-character digit text.
    if text.isdecimal() and len(text) == 1:
        return text

    digit_by_key = {
        Qt.Key.Key_0: "0",
        Qt.Key.Key_1: "1",
        Qt.Key.Key_2: "2",
        Qt.Key.Key_3: "3",
        Qt.Key.Key_4: "4",
        Qt.Key.Key_5: "5",
        Qt.Key.Key_6: "6",
        Qt.Key.Key_7: "7",
        Qt.Key.Key_8: "8",
        Qt.Key.Key_9: "9",
    }
    return digit_by_key.get(Qt.Key(event.key()))
