"""Cart domain model."""

from dataclasses import dataclass

from cash_assistant.core.money import (
    calculate_piece_line_total_grosze,
    calculate_weighted_line_total_grosze,
    round_to_nearest_50_grosze,
)
from cash_assistant.core.product import Product, UnitType


@dataclass(frozen=True)
class CartItem:
    product_id: int | None
    product_code_snapshot: str
    product_name_snapshot: str
    unit_type_snapshot: UnitType
    unit_price_grosze_snapshot: int
    quantity_value: int
    line_total_grosze: int


class Cart:
    """Shopping cart aggregate."""

    def __init__(self) -> None:
        self._items: list[CartItem] = []

    @property
    def items(self) -> tuple[CartItem, ...]:
        return tuple(self._items)

    @property
    def is_empty(self) -> bool:
        return not self._items

    @property
    def technical_total_grosze(self) -> int:
        return sum(item.line_total_grosze for item in self._items)

    @property
    def rounded_total_grosze(self) -> int:
        return round_to_nearest_50_grosze(self.technical_total_grosze)

    def add_weighted_product(self, product: Product, weight_grams: int) -> CartItem:
        if product.unit_type is not UnitType.KG:
            raise ValueError("weighted products must use UnitType.KG")

        item = CartItem(
            product_id=product.id,
            product_code_snapshot=product.code,
            product_name_snapshot=product.name,
            unit_type_snapshot=product.unit_type,
            unit_price_grosze_snapshot=product.price_grosze,
            quantity_value=weight_grams,
            line_total_grosze=calculate_weighted_line_total_grosze(
                product.price_grosze,
                weight_grams,
            ),
        )
        self._items.append(item)
        return item

    def add_piece_product(self, product: Product, quantity: int) -> CartItem:
        if product.unit_type is not UnitType.PIECE:
            raise ValueError("piece products must use UnitType.PIECE")

        item = CartItem(
            product_id=product.id,
            product_code_snapshot=product.code,
            product_name_snapshot=product.name,
            unit_type_snapshot=product.unit_type,
            unit_price_grosze_snapshot=product.price_grosze,
            quantity_value=quantity,
            line_total_grosze=calculate_piece_line_total_grosze(
                product.price_grosze,
                quantity,
            ),
        )
        self._items.append(item)
        return item

    def remove_last_item(self) -> CartItem | None:
        if not self._items:
            return None
        return self._items.pop()

    def clear(self) -> None:
        self._items.clear()
