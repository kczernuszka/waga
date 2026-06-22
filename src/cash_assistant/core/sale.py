"""Sale domain model."""

from dataclasses import dataclass
from datetime import datetime

from cash_assistant.core.cart import CartItem


@dataclass(frozen=True)
class Sale:
    id: int | None
    created_at: datetime
    raw_total_grosze: int
    rounded_total_grosze: int
    paid_grosze: int
    change_grosze: int
    items: tuple[CartItem, ...]

