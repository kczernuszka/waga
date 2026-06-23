"""Formatting helpers for UI text."""


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


def format_unit_price(price_grosze: int, unit_text: str) -> str:
    """Format product price with a unit suffix."""
    if unit_text == "":
        raise ValueError("unit_text cannot be empty")
    return f"{format_money(price_grosze)}/{unit_text}"


def _ensure_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
