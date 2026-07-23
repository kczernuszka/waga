"""Product domain model."""

from dataclasses import dataclass
from enum import Enum


class UnitType(Enum):
    KG = "kg"
    PIECE = "piece"


@dataclass(frozen=True)
class Product:
    id: int | None
    code: str
    name: str
    unit_type: UnitType
    price_grosze: int
    active: bool = True
    sort_order: int = 0
    icon_filename: str = "fallback.png"

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("product code is required")
        if self.price_grosze < 0:
            raise ValueError("price_grosze cannot be negative")
        if not self.icon_filename.strip():
            raise ValueError("icon_filename is required")
