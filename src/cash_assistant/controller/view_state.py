"""View-state DTOs and presentation builders for controllers."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from cash_assistant.controller.labels import (
    CURRENCY_TEXT,
    DATETIME_TEXT_FORMAT,
    PRODUCT_ACTIVE_TEXT,
    PRODUCT_BUTTON_TEXT_SEPARATOR,
    PRODUCT_INACTIVE_TEXT,
    UNIT_KG_TEXT,
    UNIT_PIECE_TEXT,
    UNIT_PRICE_TEXT_SEPARATOR,
)
from cash_assistant.controller.time import POLAND_TIME_ZONE
from cash_assistant.core.cart import CartItem
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import Sale, SaleItem


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
class ProductViewState:
    product_id: int
    name: str
    price_text: str
    unit_text: str
    button_text: str


@dataclass(frozen=True)
class UnitOptionViewState:
    unit_code: str
    label: str


@dataclass(frozen=True)
class ProductListItemViewState:
    product_id: int
    name: str
    unit_code: str
    unit_text: str
    price_grosze: int
    price_text: str
    active: bool
    active_text: str
    sort_order: int


@dataclass(frozen=True)
class ProductEditViewState:
    product_id: int | None
    name: str
    unit_code: str
    price_grosze: int
    active: bool
    sort_order: int
    unit_options: tuple[UnitOptionViewState, ...]


@dataclass(frozen=True)
class ProductEditInput:
    product_id: int | None
    name: str
    unit_code: str
    price_grosze: int
    active: bool = True
    sort_order: int = 0


@dataclass(frozen=True)
class CartItemViewState:
    product_id: int | None
    product_name: str
    unit_price_text: str
    quantity_text: str
    line_total_text: str


@dataclass(frozen=True)
class SaleItemViewState:
    product_id: int | None
    product_name: str
    unit_price_text: str
    quantity_text: str
    line_total_text: str


@dataclass(frozen=True)
class SaleSummaryViewState:
    sale_id: int
    created_at_text: str
    raw_total_grosze: int
    raw_total_text: str
    rounded_total_grosze: int
    rounded_total_text: str
    paid_grosze: int
    paid_text: str
    change_grosze: int
    change_text: str
    items_count: int


@dataclass(frozen=True)
class SaleDetailsViewState:
    sale_id: int
    created_at_text: str
    raw_total_grosze: int
    raw_total_text: str
    rounded_total_grosze: int
    rounded_total_text: str
    paid_grosze: int
    paid_text: str
    change_grosze: int
    change_text: str
    items: tuple[SaleItemViewState, ...]


@dataclass(frozen=True)
class ViewState:
    app_state: AppState
    products: tuple[ProductViewState, ...]
    selected_product: ProductViewState | None
    current_weight_grams: int | None
    current_weight_text: str | None
    cart_items: tuple[CartItemViewState, ...]
    technical_total_grosze: int
    technical_total_text: str
    rounded_total_grosze: int
    rounded_total_text: str
    paid_grosze: int | None
    paid_text: str | None
    change_grosze: int | None
    change_text: str | None
    missing_grosze: int | None
    missing_text: str | None
    is_cart_empty: bool


def build_product_view_state(product: Product) -> ProductViewState:
    if product.id is None:
        raise ValueError("product id is required for product view state")

    unit_text = _format_unit_type(product.unit_type)
    price_text = _format_unit_price(product.price_grosze, unit_text)
    return ProductViewState(
        product_id=product.id,
        name=product.name,
        price_text=price_text,
        unit_text=unit_text,
        button_text=f"{product.name}{PRODUCT_BUTTON_TEXT_SEPARATOR}{price_text}",
    )


def build_product_list_item_view_state(product: Product) -> ProductListItemViewState:
    if product.id is None:
        raise ValueError("product id is required for product list item view state")

    unit_text = _format_unit_type(product.unit_type)
    return ProductListItemViewState(
        product_id=product.id,
        name=product.name,
        unit_code=product.unit_type.value,
        unit_text=unit_text,
        price_grosze=product.price_grosze,
        price_text=_format_unit_price(product.price_grosze, unit_text),
        active=product.active,
        active_text=_format_active(product.active),
        sort_order=product.sort_order,
    )


def build_product_edit_view_state(
    product: Product | None = None,
) -> ProductEditViewState:
    return ProductEditViewState(
        product_id=None if product is None else product.id,
        name="" if product is None else product.name,
        unit_code=UnitType.KG.value if product is None else product.unit_type.value,
        price_grosze=0 if product is None else product.price_grosze,
        active=True if product is None else product.active,
        sort_order=0 if product is None else product.sort_order,
        unit_options=_unit_options(),
    )


def build_cart_item_view_state(item: CartItem) -> CartItemViewState:
    unit_text = _format_unit_type(item.unit_type_snapshot)
    return CartItemViewState(
        product_id=item.product_id,
        product_name=item.product_name_snapshot,
        unit_price_text=_format_unit_price(item.unit_price_grosze_snapshot, unit_text),
        quantity_text=_format_quantity(item.unit_type_snapshot, item.quantity_value),
        line_total_text=_format_money(item.line_total_grosze),
    )


def build_sale_item_view_state(item: SaleItem) -> SaleItemViewState:
    unit_text = _format_unit_type(item.unit_type_snapshot)
    return SaleItemViewState(
        product_id=item.product_id,
        product_name=item.product_name_snapshot,
        unit_price_text=_format_unit_price(item.unit_price_grosze_snapshot, unit_text),
        quantity_text=_format_quantity(item.unit_type_snapshot, item.quantity_value),
        line_total_text=_format_money(item.line_total_grosze),
    )


def build_sale_summary_view_state(sale: Sale) -> SaleSummaryViewState:
    sale_id = _require_sale_id(sale)
    return SaleSummaryViewState(
        sale_id=sale_id,
        created_at_text=_format_datetime(sale.created_at),
        raw_total_grosze=sale.raw_total_grosze,
        raw_total_text=_format_money(sale.raw_total_grosze),
        rounded_total_grosze=sale.rounded_total_grosze,
        rounded_total_text=_format_money(sale.rounded_total_grosze),
        paid_grosze=sale.paid_grosze,
        paid_text=_format_money(sale.paid_grosze),
        change_grosze=sale.change_grosze,
        change_text=_format_money(sale.change_grosze),
        items_count=len(sale.items),
    )


def build_sale_details_view_state(sale: Sale) -> SaleDetailsViewState:
    sale_id = _require_sale_id(sale)
    return SaleDetailsViewState(
        sale_id=sale_id,
        created_at_text=_format_datetime(sale.created_at),
        raw_total_grosze=sale.raw_total_grosze,
        raw_total_text=_format_money(sale.raw_total_grosze),
        rounded_total_grosze=sale.rounded_total_grosze,
        rounded_total_text=_format_money(sale.rounded_total_grosze),
        paid_grosze=sale.paid_grosze,
        paid_text=_format_money(sale.paid_grosze),
        change_grosze=sale.change_grosze,
        change_text=_format_money(sale.change_grosze),
        items=tuple(build_sale_item_view_state(item) for item in sale.items),
    )


def _format_money(grosze: int) -> str:
    _ensure_non_negative(grosze, "grosze")
    zloty = grosze // 100
    grosze_remainder = grosze % 100
    return f"{zloty},{grosze_remainder:02d} {CURRENCY_TEXT}"


def _format_weight_grams(weight_grams: int) -> str:
    _ensure_non_negative(weight_grams, "weight_grams")
    kilograms_hundredths = (weight_grams + 5) // 10
    kilograms = kilograms_hundredths // 100
    hundredths_remainder = kilograms_hundredths % 100
    return f"{kilograms},{hundredths_remainder:02d} {UNIT_KG_TEXT}"


def _format_piece_quantity(quantity: int) -> str:
    _ensure_non_negative(quantity, "quantity")
    return f"{quantity} {UNIT_PIECE_TEXT}"


def _format_unit_type(unit_type: UnitType) -> str:
    match unit_type:
        case UnitType.KG:
            return UNIT_KG_TEXT
        case UnitType.PIECE:
            return UNIT_PIECE_TEXT


def _format_active(active: bool) -> str:
    return PRODUCT_ACTIVE_TEXT if active else PRODUCT_INACTIVE_TEXT


def _format_quantity(unit_type: UnitType, quantity_value: int) -> str:
    match unit_type:
        case UnitType.KG:
            return _format_weight_grams(quantity_value)
        case UnitType.PIECE:
            return _format_piece_quantity(quantity_value)


def _format_unit_price(price_grosze: int, unit_text: str) -> str:
    return f"{_format_money(price_grosze)}{UNIT_PRICE_TEXT_SEPARATOR}{unit_text}"


def _format_datetime(value: datetime) -> str:
    return value.astimezone(POLAND_TIME_ZONE).strftime(DATETIME_TEXT_FORMAT)


def _require_sale_id(sale: Sale) -> int:
    if sale.id is None:
        raise ValueError("sale id is required for sale view state")
    return sale.id


def _unit_options() -> tuple[UnitOptionViewState, ...]:
    return (
        UnitOptionViewState(unit_code=UnitType.KG.value, label=UNIT_KG_TEXT),
        UnitOptionViewState(unit_code=UnitType.PIECE.value, label=UNIT_PIECE_TEXT),
    )


def _ensure_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
