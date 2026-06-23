"""Main application controller."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from cash_assistant.core.cart import Cart, CartItem
from cash_assistant.core.money import calculate_change
from cash_assistant.core.product import Product
from cash_assistant.core.sale import Sale
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.scale import Scale


class AppState(Enum):
    PRODUCT_SELECTION = "product_selection"
    ENTERING_QUANTITY = "entering_quantity"
    READING_WEIGHT = "reading_weight"
    CART_REVIEW = "cart_review"
    PAYMENT = "payment"
    SETTINGS = "settings"
    HISTORY = "history"


@dataclass(frozen=True)
class PaymentState:
    paid_grosze: int
    change_grosze: int | None
    missing_grosze: int | None


@dataclass(frozen=True)
class ViewState:
    app_state: AppState
    cart_items: tuple[CartItem, ...]
    technical_total_grosze: int
    rounded_total_grosze: int
    paid_grosze: int | None
    change_grosze: int | None
    missing_grosze: int | None
    is_cart_empty: bool


class AppController:
    def __init__(
        self,
        scale: Scale,
        sale_repository: SaleRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._scale = scale
        self._sale_repository = sale_repository
        self._clock = clock or _utc_now
        self._cart = Cart()
        self._state = AppState.PRODUCT_SELECTION
        self._payment: PaymentState | None = None

    @property
    def cart(self) -> Cart:
        return self._cart

    def add_weighted_product(self, product: Product) -> CartItem:
        item = self._cart.add_weighted_product(
            product,
            weight_grams=self._scale.get_weight_grams(),
        )
        self._reset_payment()
        self._state = AppState.CART_REVIEW
        return item

    def add_piece_product(self, product: Product, quantity: int) -> CartItem:
        item = self._cart.add_piece_product(product, quantity=quantity)
        self._reset_payment()
        self._state = AppState.CART_REVIEW
        return item

    def remove_last_item(self) -> CartItem | None:
        item = self._cart.remove_last_item()
        self._reset_payment()
        self._state = AppState.PRODUCT_SELECTION if self._cart.is_empty else AppState.CART_REVIEW
        return item

    def clear_cart(self) -> None:
        self._cart.clear()
        self._reset_payment()
        self._state = AppState.PRODUCT_SELECTION

    def start_quantity_entry(self) -> None:
        self._reset_payment()
        self._state = AppState.ENTERING_QUANTITY

    def start_payment(self) -> None:
        if self._cart.is_empty:
            raise ValueError("cannot start payment with empty cart")
        self._reset_payment()
        self._state = AppState.PAYMENT

    def cancel_current_operation(self) -> None:
        self._reset_payment()
        self._state = AppState.PRODUCT_SELECTION if self._cart.is_empty else AppState.CART_REVIEW

    def open_settings(self) -> None:
        self._state = AppState.SETTINGS

    def open_history(self) -> None:
        self._state = AppState.HISTORY

    def set_paid_grosze(self, paid_grosze: int) -> PaymentState:
        if paid_grosze < 0:
            raise ValueError("paid_grosze cannot be negative")

        rounded_total_grosze = self._cart.rounded_total_grosze
        if paid_grosze < rounded_total_grosze:
            self._payment = PaymentState(
                paid_grosze=paid_grosze,
                change_grosze=None,
                missing_grosze=rounded_total_grosze - paid_grosze,
            )
        else:
            self._payment = PaymentState(
                paid_grosze=paid_grosze,
                change_grosze=calculate_change(
                    paid_grosze=paid_grosze,
                    total_grosze=rounded_total_grosze,
                ),
                missing_grosze=None,
            )

        self._state = AppState.PAYMENT
        return self._payment

    def save_sale(self) -> Sale:
        if self._payment is None:
            raise ValueError("paid_grosze is required before saving sale")
        if self._payment.missing_grosze is not None:
            raise ValueError("paid amount is lower than rounded total")

        sale = Sale.from_cart(
            self._cart,
            paid_grosze=self._payment.paid_grosze,
            created_at=self._clock(),
        )
        saved_sale = self._sale_repository.save_sale(sale)
        self._cart = Cart()
        self._reset_payment()
        self._state = AppState.PRODUCT_SELECTION
        return saved_sale

    def prepare_view_state(self) -> ViewState:
        return ViewState(
            app_state=self._state,
            cart_items=self._cart.items,
            technical_total_grosze=self._cart.technical_total_grosze,
            rounded_total_grosze=self._cart.rounded_total_grosze,
            paid_grosze=None if self._payment is None else self._payment.paid_grosze,
            change_grosze=None if self._payment is None else self._payment.change_grosze,
            missing_grosze=None if self._payment is None else self._payment.missing_grosze,
            is_cart_empty=self._cart.is_empty,
        )

    def _reset_payment(self) -> None:
        self._payment = None


def _utc_now() -> datetime:
    return datetime.now(UTC)
