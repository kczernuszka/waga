"""Main application controller."""

from collections.abc import Callable
from datetime import UTC, datetime

from cash_assistant.controller.labels import CURRENCY_TEXT, UNIT_KG_TEXT
from cash_assistant.controller.view_state import (
    AppState,
    PaymentState,
    ProductEditInput,
    ProductEditViewState,
    ProductListItemViewState,
    ProductViewState,
    SaleDetailsViewState,
    SaleSummaryViewState,
    ViewState,
    build_cart_item_view_state,
    build_product_edit_view_state,
    build_product_list_item_view_state,
    build_product_view_state,
    build_sale_details_view_state,
    build_sale_summary_view_state,
)
from cash_assistant.core.cart import Cart, CartItem
from cash_assistant.core.money import calculate_change
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import Sale
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.scale import Scale

__all__ = [
    "AppController",
    "AppState",
    "PaymentState",
    "ProductEditInput",
    "ProductEditViewState",
    "ProductListItemViewState",
    "SaleDetailsViewState",
    "SaleSummaryViewState",
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
        self._selected_piece_product_id: int | None = None
        self._selected_weighted_product_id: int | None = None

    def list_products_for_settings(self) -> list[ProductListItemViewState]:
        return [
            build_product_list_item_view_state(product)
            for product in self._require_product_repository().list_all_products()
        ]

    def prepare_product_edit_view_state(
        self,
        product_id: int | None = None,
    ) -> ProductEditViewState:
        if product_id is None:
            return build_product_edit_view_state()

        product = self._require_product_repository().get_product(product_id)
        if product is None:
            raise ValueError(f"product with id {product_id} does not exist")
        return build_product_edit_view_state(product)

    def save_product_from_input(
        self,
        product_input: ProductEditInput,
    ) -> ProductEditViewState:
        product = Product(
            id=product_input.product_id,
            name=product_input.name,
            unit_type=UnitType(product_input.unit_code),
            price_grosze=product_input.price_grosze,
            active=product_input.active,
            sort_order=product_input.sort_order,
        )

        if product_input.product_id is None:
            saved_product = self._require_product_repository().create_product(product)
        else:
            saved_product = self._require_product_repository().update_product(product)

        return build_product_edit_view_state(saved_product)

    def select_product_by_id(self, product_id: int) -> ViewState:
        product = self._require_active_product(product_id)

        if product.unit_type is UnitType.KG:
            self._reset_payment()
            self._selected_weighted_product_id = product_id
            self._selected_piece_product_id = None
            self._state = AppState.READING_WEIGHT
            return self.prepare_view_state()

        self._reset_payment()
        self._selected_weighted_product_id = None
        self._selected_piece_product_id = product_id
        self._state = AppState.ENTERING_QUANTITY
        return self.prepare_view_state()

    def add_selected_weighted_product(self) -> ViewState:
        if self._selected_weighted_product_id is None:
            raise ValueError("no weighted product selected")
        product = self._require_active_product(self._selected_weighted_product_id)
        self._add_weighted_product(product)
        return self.prepare_view_state()

    def add_selected_piece_product(self, quantity: int) -> ViewState:
        if self._selected_piece_product_id is None:
            raise ValueError("no piece product selected")
        product = self._require_active_product(self._selected_piece_product_id)
        self._add_piece_product(product, quantity=quantity)
        return self.prepare_view_state()

    def remove_last_item(self) -> ViewState:
        self._cart.remove_last_item()
        self._reset_payment()
        self._clear_selected_product()
        self._state = AppState.PRODUCT_SELECTION if self._cart.is_empty else AppState.CART_REVIEW
        return self.prepare_view_state()

    def clear_cart(self) -> ViewState:
        self._cart.clear()
        self._reset_payment()
        self._clear_selected_product()
        self._state = AppState.PRODUCT_SELECTION
        return self.prepare_view_state()

    def start_payment(self) -> ViewState:
        if self._cart.is_empty:
            raise ValueError("cannot start payment with empty cart")
        self._reset_payment()
        self._clear_selected_product()
        self._state = AppState.PAYMENT
        return self.prepare_view_state()

    def cancel_current_operation(self) -> ViewState:
        self._reset_payment()
        self._clear_selected_product()
        self._state = AppState.PRODUCT_SELECTION if self._cart.is_empty else AppState.CART_REVIEW
        return self.prepare_view_state()

    def open_settings(self) -> ViewState:
        self._state = AppState.SETTINGS
        return self.prepare_view_state()

    def open_history(self) -> ViewState:
        self._state = AppState.HISTORY
        return self.prepare_view_state()

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

    def save_sale(self) -> SaleDetailsViewState:
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
        sale_details = build_sale_details_view_state(saved_sale)
        self._cart = Cart()
        self._reset_payment()
        self._clear_selected_product()
        self._state = AppState.PRODUCT_SELECTION
        return sale_details

    def list_sales_for_history(self, limit: int = 20) -> list[SaleSummaryViewState]:
        return [
            build_sale_summary_view_state(sale)
            for sale in self._sale_repository.list_recent_sales(limit=limit)
        ]

    def read_sale_details(self, sale_id: int) -> SaleDetailsViewState | None:
        sale = self._sale_repository.read_sale(sale_id)
        if sale is None:
            return None
        return build_sale_details_view_state(sale)

    def prepare_view_state(self) -> ViewState:
        paid_grosze = None if self._payment is None else self._payment.paid_grosze
        change_grosze = None if self._payment is None else self._payment.change_grosze
        missing_grosze = None if self._payment is None else self._payment.missing_grosze
        selected_product = self._selected_product_view_state()
        current_weight_grams = (
            self._scale.get_weight_grams()
            if self._state is AppState.READING_WEIGHT
            else None
        )

        return ViewState(
            app_state=self._state,
            products=tuple(
                build_product_view_state(product)
                for product in self._list_active_products_if_repository_exists()
            ),
            selected_product=selected_product,
            current_weight_grams=current_weight_grams,
            current_weight_text=(
                None if current_weight_grams is None else _format_weight_grams(current_weight_grams)
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

    def _clear_selected_product(self) -> None:
        self._selected_piece_product_id = None
        self._selected_weighted_product_id = None

    def _add_weighted_product(self, product: Product) -> CartItem:
        self._clear_selected_product()
        item = self._cart.add_weighted_product(
            product,
            weight_grams=self._scale.get_weight_grams(),
        )
        self._reset_payment()
        self._state = AppState.CART_REVIEW
        return item

    def _add_piece_product(self, product: Product, quantity: int) -> CartItem:
        self._clear_selected_product()
        item = self._cart.add_piece_product(product, quantity=quantity)
        self._reset_payment()
        self._state = AppState.CART_REVIEW
        return item

    def _require_product_repository(self) -> ProductRepository:
        if self._product_repository is None:
            raise ValueError("product repository is required for product operations")
        return self._product_repository

    def _require_active_product(self, product_id: int) -> Product:
        product = self._require_product_repository().get_product(product_id)
        if product is None:
            raise ValueError(f"product with id {product_id} does not exist")
        if not product.active:
            raise ValueError(f"product with id {product_id} is inactive")
        return product

    def _list_active_products_if_repository_exists(self) -> list[Product]:
        if self._product_repository is None:
            return []
        return self._product_repository.list_active_products()

    def _selected_product_view_state(self) -> ProductViewState | None:
        product_id = self._selected_piece_product_id or self._selected_weighted_product_id
        if product_id is None:
            return None
        return build_product_view_state(self._require_active_product(product_id))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_money(grosze: int) -> str:
    if grosze < 0:
        raise ValueError("grosze cannot be negative")
    zloty = grosze // 100
    grosze_remainder = grosze % 100
    return f"{zloty},{grosze_remainder:02d} {CURRENCY_TEXT}"


def _format_weight_grams(weight_grams: int) -> str:
    if weight_grams < 0:
        raise ValueError("weight_grams cannot be negative")
    kilograms_hundredths = (weight_grams + 5) // 10
    kilograms = kilograms_hundredths // 100
    hundredths_remainder = kilograms_hundredths % 100
    return f"{kilograms},{hundredths_remainder:02d} {UNIT_KG_TEXT}"
