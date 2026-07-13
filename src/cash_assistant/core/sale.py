"""Sale domain model."""

from dataclasses import dataclass
from datetime import datetime

from cash_assistant.core.cart import Cart
from cash_assistant.core.money import calculate_change
from cash_assistant.core.product import UnitType


@dataclass(frozen=True)
class SaleItem:
    product_id: int | None
    product_name_snapshot: str
    unit_type_snapshot: UnitType
    unit_price_grosze_snapshot: int
    quantity_value: int
    line_total_grosze: int


@dataclass(frozen=True)
class Sale:
    id: int | None
    created_at: datetime
    raw_total_grosze: int
    rounded_total_grosze: int
    paid_grosze: int
    change_grosze: int
    items: tuple[SaleItem, ...]

    def __post_init__(self) -> None:
        _ensure_timezone_aware(self.created_at)

    @classmethod
    def from_cart(
        cls,
        cart: Cart,
        paid_grosze: int,
        created_at: datetime,
    ) -> "Sale":
        if cart.is_empty:
            raise ValueError("cannot create sale from empty cart")

        rounded_total_grosze = cart.rounded_total_grosze
        change_grosze = calculate_change(
            paid_grosze=paid_grosze,
            total_grosze=rounded_total_grosze,
        )

        return cls(
            id=None,
            created_at=created_at,
            raw_total_grosze=cart.technical_total_grosze,
            rounded_total_grosze=rounded_total_grosze,
            paid_grosze=paid_grosze,
            change_grosze=change_grosze,
            items=tuple(
                SaleItem(
                    product_id=item.product_id,
                    product_name_snapshot=item.product_name_snapshot,
                    unit_type_snapshot=item.unit_type_snapshot,
                    unit_price_grosze_snapshot=item.unit_price_grosze_snapshot,
                    quantity_value=item.quantity_value,
                    line_total_grosze=item.line_total_grosze,
                )
                for item in cart.items
            ),
        )


def _ensure_timezone_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
