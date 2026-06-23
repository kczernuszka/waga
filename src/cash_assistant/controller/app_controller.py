"""Main application controller."""

from collections.abc import Callable
from datetime import UTC, datetime

from cash_assistant.controller.view_state import (
    AppState,
    PaymentState,
    ViewState,
    build_cart_item_view_state,
    build_product_view_state,
)
from cash_assistant.core.cart import Cart, CartItem
from cash_assistant.core.money import calculate_change
from cash_assistant.core.product import Product
from cash_assistant.core.sale import Sale
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.scale import Scale

__all__ = [
    "AppController",
    "AppState",
    "PaymentState",
    "ViewState",
]


class AppController:
    def __init__(
        self,
        scale: Scale,
        sale_repository: SaleRepository,
        product_repository: ProductRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._scale = scale
        self._product_repository = product_repository
        self._sale_repository = sale_repository
        self._clock = clock or _utc_now
        self._cart = Cart()
        self._state = AppState.PRODUCT_SELECTION
        self._payment: PaymentState | None = None

    @property
    def cart(self) -> Cart:
        return self._cart

    def list_active_products(self) -> list[Product]:
        return self._require_product_repository().list_active_products()

    def list_all_products(self) -> list[Product]:
        return self._require_product_repository().list_all_products()

    def get_product(self, product_id: int) -> Product | None:
        return self._require_product_repository().get_product(product_id)

    def create_product(self, product: Product) -> Product:
        return self._require_product_repository().create_product(product)

    def update_product(self, product: Product) -> Product:
        return self._require_product_repository().update_product(product)

    def deactivate_product(self, product_id: int) -> None:
        self._require_product_repository().deactivate_product(product_id)

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
        if self._state is not AppState.PAYMENT:
            raise ValueError("payment has not been started")
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

        return self._payment

    def save_sale(self) -> Sale:
        if self._cart.is_empty:
            raise ValueError("cannot save sale from empty cart")
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

    def list_recent_sales(self, limit: int = 20) -> list[Sale]:
        return self._sale_repository.list_recent_sales(limit=limit)

    def read_sale(self, sale_id: int) -> Sale | None:
        return self._sale_repository.read_sale(sale_id)

    def prepare_view_state(self) -> ViewState:
        paid_grosze = None if self._payment is None else self._payment.paid_grosze
        change_grosze = None if self._payment is None else self._payment.change_grosze
        missing_grosze = None if self._payment is None else self._payment.missing_grosze

        return ViewState(
            app_state=self._state,
            products=tuple(
                build_product_view_state(product)
                for product in self._list_active_products_if_repository_exists()
            ),
            cart_items=tuple(build_cart_item_view_state(item) for item in self._cart.items),
            technical_total_grosze=self._cart.technical_total_grosze,
            technical_total_text=_format_money(self._cart.technical_total_grosze),
            rounded_total_grosze=self._cart.rounded_total_grosze,
            rounded_total_text=_format_money(self._cart.rounded_total_grosze),
            paid_grosze=paid_grosze,
            paid_text=None if paid_grosze is None else _format_money(paid_grosze),
            change_grosze=change_grosze,
            change_text=None if change_grosze is None else _format_money(change_grosze),
            missing_grosze=missing_grosze,
            missing_text=None if missing_grosze is None else _format_money(missing_grosze),
            is_cart_empty=self._cart.is_empty,
        )

    def _reset_payment(self) -> None:
        self._payment = None

    def _require_product_repository(self) -> ProductRepository:
        if self._product_repository is None:
            raise ValueError("product repository is required for product operations")
        return self._product_repository

    def _list_active_products_if_repository_exists(self) -> list[Product]:
        if self._product_repository is None:
            return []
        return self._product_repository.list_active_products()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_money(grosze: int) -> str:
    if grosze < 0:
        raise ValueError("grosze cannot be negative")
    zloty = grosze // 100
    grosze_remainder = grosze % 100
    return f"{zloty},{grosze_remainder:02d} zł"
