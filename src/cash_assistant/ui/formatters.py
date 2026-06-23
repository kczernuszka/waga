"""Formatting helpers for UI text."""

from cash_assistant.core.product import UnitType


def format_money(grosze: int) -> str:
    """Format grosze as Polish złoty text."""
    _ensure_non_negative(grosze, "grosze")
    zloty = grosze // 100
    grosze_remainder = grosze % 100
    return f"{zloty},{grosze_remainder:02d} zł"


def format_weight_grams(weight_grams: int) -> str:
    """Format grams as kilograms with two decimal places."""
    _ensure_non_negative(weight_grams, "weight_grams")
    kilograms_hundredths = (weight_grams + 5) // 10
    kilograms = kilograms_hundredths // 100
    hundredths_remainder = kilograms_hundredths % 100
    return f"{kilograms},{hundredths_remainder:02d} kg"


def format_piece_quantity(quantity: int) -> str:
    """Format a piece quantity for UI display."""
    _ensure_non_negative(quantity, "quantity")
    return f"{quantity} szt."


def format_unit_type(unit_type: UnitType) -> str:
    """Format product unit type for UI display."""
    match unit_type:
        case UnitType.KG:
            return "kg"
        case UnitType.PIECE:
            return "szt."


def format_quantity(unit_type: UnitType, quantity_value: int) -> str:
    """Format cart/sale quantity according to its unit type."""
    match unit_type:
        case UnitType.KG:
            return format_weight_grams(quantity_value)
        case UnitType.PIECE:
            return format_piece_quantity(quantity_value)


def format_unit_price(price_grosze: int, unit_type: UnitType) -> str:
    """Format product price with a unit suffix."""
    return f"{format_money(price_grosze)}/{format_unit_type(unit_type)}"


def _ensure_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
