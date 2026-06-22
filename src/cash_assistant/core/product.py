"""Product domain model."""

from dataclasses import dataclass
from enum import Enum


class UnitType(Enum):
    KG = "kg"
    PIECE = "piece"


@dataclass(frozen=True)
class Product:
    id: int | None
    name: str
    unit_type: UnitType
    price_grosze: int
    active: bool = True
    sort_order: int = 0

