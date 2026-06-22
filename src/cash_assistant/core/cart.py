"""Cart domain model."""

from dataclasses import dataclass

from cash_assistant.core.product import UnitType


@dataclass(frozen=True)
class CartItem:
    product_id: int | None
    product_name_snapshot: str
    unit_type_snapshot: UnitType
    unit_price_grosze_snapshot: int
    quantity_value: int
    line_total_grosze: int


class Cart:
    """Shopping cart aggregate."""

    pass

