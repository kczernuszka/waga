"""Keyboard command controller."""

from enum import Enum


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
    pass

