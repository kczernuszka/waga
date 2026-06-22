"""Main application controller."""

from enum import Enum


class AppState(Enum):
    PRODUCT_SELECTION = "product_selection"
    ENTERING_QUANTITY = "entering_quantity"
    READING_WEIGHT = "reading_weight"
    CART_REVIEW = "cart_review"
    PAYMENT = "payment"
    SETTINGS = "settings"
    HISTORY = "history"


class AppController:
    pass

