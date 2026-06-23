"""View-state DTOs and presentation builders for controllers."""

from dataclasses import dataclass
from enum import Enum

from cash_assistant.core.cart import CartItem
from cash_assistant.core.product import Product, UnitType


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
    product_id: int | None
    name: str
    price_text: str
    unit_text: str
    button_text: str


@dataclass(frozen=True)
class CartItemViewState:
    product_id: int | None
    product_name: str
    unit_price_text: str
    quantity_text: str
    line_total_text: str


@dataclass(frozen=True)
class ViewState:
    app_state: AppState
    products: tuple[ProductViewState, ...]
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
    unit_text = _format_unit_type(product.unit_type)
    price_text = _format_unit_price(product.price_grosze, unit_text)
    return ProductViewState(
        product_id=product.id,
        name=product.name,
        price_text=price_text,
        unit_text=unit_text,
        button_text=f"{product.name}\n{price_text}",
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


def _format_money(grosze: int) -> str:
    _ensure_non_negative(grosze, "grosze")
    zloty = grosze // 100
    grosze_remainder = grosze % 100
    return f"{zloty},{grosze_remainder:02d} zł"


def _format_weight_grams(weight_grams: int) -> str:
    _ensure_non_negative(weight_grams, "weight_grams")
    kilograms_hundredths = (weight_grams + 5) // 10
    kilograms = kilograms_hundredths // 100
    hundredths_remainder = kilograms_hundredths % 100
    return f"{kilograms},{hundredths_remainder:02d} kg"


def _format_piece_quantity(quantity: int) -> str:
    _ensure_non_negative(quantity, "quantity")
    return f"{quantity} szt."


def _format_unit_type(unit_type: UnitType) -> str:
    match unit_type:
        case UnitType.KG:
            return "kg"
        case UnitType.PIECE:
            return "szt."


def _format_quantity(unit_type: UnitType, quantity_value: int) -> str:
    match unit_type:
        case UnitType.KG:
            return _format_weight_grams(quantity_value)
        case UnitType.PIECE:
            return _format_piece_quantity(quantity_value)


def _format_unit_price(price_grosze: int, unit_text: str) -> str:
    return f"{_format_money(price_grosze)}/{unit_text}"


def _ensure_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
