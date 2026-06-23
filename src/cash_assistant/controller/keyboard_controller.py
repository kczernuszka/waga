"""Keyboard command controller."""

from collections.abc import Sequence
from enum import Enum
from typing import Any

from cash_assistant.controller.app_controller import AppController, AppState
from cash_assistant.core.product import Product, UnitType


class Command(Enum):
    SELECT_PRODUCT = "select_product"
    DIGIT_TYPED = "digit_typed"
    DECIMAL_SEPARATOR_TYPED = "decimal_separator_typed"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    BACKSPACE = "backspace"
    REMOVE_LAST_ITEM = "remove_last_item"
    CLEAR_CART = "clear_cart"
    START_PAYMENT = "start_payment"
    SAVE_SALE = "save_sale"
    OPEN_SETTINGS = "open_settings"
    OPEN_HISTORY = "open_history"


class KeyboardController:
    def __init__(
        self,
        app_controller: AppController,
        products: Sequence[Product] = (),
    ) -> None:
        self._app_controller = app_controller
        self._products = tuple(products)
        self._selected_piece_product: Product | None = None
        self._quantity_buffer = ""
        self._payment_buffer = ""

    def set_products(self, products: Sequence[Product]) -> None:
        self._products = tuple(products)

    def handle(self, command: Command, payload: object | None = None) -> Any:
        result: Any = None
        match command:
            case Command.SELECT_PRODUCT:
                result = self._select_product(self._product_from_payload(payload))
            case Command.DIGIT_TYPED:
                result = self._handle_digit(payload)
            case Command.DECIMAL_SEPARATOR_TYPED:
                self._handle_decimal_separator()
            case Command.CONFIRM:
                result = self._confirm()
            case Command.CANCEL:
                self._cancel()
            case Command.BACKSPACE:
                self._backspace()
            case Command.REMOVE_LAST_ITEM:
                self._clear_input_buffers()
                result = self._app_controller.remove_last_item()
            case Command.CLEAR_CART:
                self._clear_input_buffers()
                self._app_controller.clear_cart()
            case Command.START_PAYMENT:
                self._clear_input_buffers()
                self._app_controller.start_payment()
            case Command.SAVE_SALE:
                self._clear_input_buffers()
                result = self._app_controller.save_sale()
            case Command.OPEN_SETTINGS:
                self._clear_input_buffers()
                self._app_controller.open_settings()
            case Command.OPEN_HISTORY:
                self._clear_input_buffers()
                self._app_controller.open_history()
        return result

    def _handle_digit(self, payload: object | None) -> Any:
        digit = self._digit_from_payload(payload)
        app_state = self._app_controller.prepare_view_state().app_state

        if app_state is AppState.ENTERING_QUANTITY:
            self._quantity_buffer += digit
            return None

        if app_state is AppState.PAYMENT:
            self._payment_buffer += digit
            return self._app_controller.set_paid_grosze(self._payment_buffer_to_grosze())

        return self._select_product(self._product_by_shortcut(digit))

    def _handle_decimal_separator(self) -> None:
        app_state = self._app_controller.prepare_view_state().app_state
        if app_state is not AppState.PAYMENT:
            raise ValueError("decimal separator is only valid during payment")
        if "," in self._payment_buffer:
            raise ValueError("payment already contains decimal separator")
        if self._payment_buffer == "":
            self._payment_buffer = "0"
        self._payment_buffer += ","
        self._app_controller.set_paid_grosze(self._payment_buffer_to_grosze())

    def _confirm(self) -> Any:
        app_state = self._app_controller.prepare_view_state().app_state

        if app_state is AppState.ENTERING_QUANTITY:
            if self._selected_piece_product is None:
                raise ValueError("no piece product selected")
            if self._quantity_buffer == "":
                raise ValueError("quantity is required")
            quantity = int(self._quantity_buffer)
            product = self._selected_piece_product
            self._clear_input_buffers()
            return self._app_controller.add_piece_product(product, quantity=quantity)

        if app_state is AppState.PAYMENT:
            return self._app_controller.save_sale()

        return None

    def _cancel(self) -> None:
        self._clear_input_buffers()
        self._app_controller.cancel_current_operation()

    def _backspace(self) -> None:
        app_state = self._app_controller.prepare_view_state().app_state

        if app_state is AppState.ENTERING_QUANTITY:
            self._quantity_buffer = self._quantity_buffer[:-1]
            return

        if app_state is AppState.PAYMENT:
            self._payment_buffer = self._payment_buffer[:-1]
            paid_grosze = 0 if self._payment_buffer == "" else self._payment_buffer_to_grosze()
            self._app_controller.set_paid_grosze(paid_grosze)

    def _select_product(self, product: Product) -> Any:
        self._clear_input_buffers()

        if product.unit_type is UnitType.KG:
            return self._app_controller.add_weighted_product(product)

        if product.unit_type is UnitType.PIECE:
            self._selected_piece_product = product
            self._app_controller.start_quantity_entry()
            return None

    def _product_from_payload(self, payload: object | None) -> Product:
        if isinstance(payload, Product):
            return payload
        if isinstance(payload, int | str):
            return self._product_by_shortcut(str(payload))
        raise ValueError("SELECT_PRODUCT requires a Product or product shortcut")

    def _product_by_shortcut(self, shortcut: str) -> Product:
        if not shortcut.isdecimal() or len(shortcut) != 1:
            raise ValueError("product shortcut must be a single digit")

        index = int(shortcut) - 1
        if index < 0 or index >= len(self._products):
            raise ValueError(f"product shortcut {shortcut} is not assigned")
        return self._products[index]

    def _digit_from_payload(self, payload: object | None) -> str:
        if isinstance(payload, int):
            digit = str(payload)
        elif isinstance(payload, str):
            digit = payload
        else:
            raise ValueError("DIGIT_TYPED requires a digit payload")

        if not digit.isdecimal() or len(digit) != 1:
            raise ValueError("DIGIT_TYPED requires a single digit")
        return digit

    def _payment_buffer_to_grosze(self) -> int:
        if "," not in self._payment_buffer:
            return int(self._payment_buffer) * 100 if self._payment_buffer else 0

        zloty_text, grosze_text = self._payment_buffer.split(",", maxsplit=1)
        zloty = int(zloty_text) if zloty_text else 0
        grosze = int((grosze_text + "00")[:2])
        return zloty * 100 + grosze

    def _clear_input_buffers(self) -> None:
        self._selected_piece_product = None
        self._quantity_buffer = ""
        self._payment_buffer = ""
