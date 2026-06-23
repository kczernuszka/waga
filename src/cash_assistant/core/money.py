"""Money helpers.

Amounts are represented as integer grosze.
"""


def _ensure_non_negative(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative")


def calculate_weighted_line_total_grosze(
    unit_price_grosze: int,
    weight_grams: int,
) -> int:
    """Return line total for a weighted product.

    The unit price is expressed per kilogram and weight is expressed in grams.
    The result is rounded to the nearest grosz, with halves rounded up.
    """
    _ensure_non_negative(unit_price_grosze, "unit_price_grosze")
    _ensure_non_negative(weight_grams, "weight_grams")
    return (unit_price_grosze * weight_grams + 500) // 1_000


def calculate_piece_line_total_grosze(
    unit_price_grosze: int,
    quantity: int,
) -> int:
    """Return line total for a product sold by piece."""
    _ensure_non_negative(unit_price_grosze, "unit_price_grosze")
    _ensure_non_negative(quantity, "quantity")
    return unit_price_grosze * quantity


def round_to_nearest_50_grosze(amount_grosze: int) -> int:
    """Round an amount to the nearest 50 grosze, with halves rounded up."""
    _ensure_non_negative(amount_grosze, "amount_grosze")
    return ((amount_grosze + 25) // 50) * 50


def calculate_change(paid_grosze: int, total_grosze: int) -> int:
    """Return change due, rejecting negative values and insufficient payment."""
    _ensure_non_negative(paid_grosze, "paid_grosze")
    _ensure_non_negative(total_grosze, "total_grosze")
    if paid_grosze < total_grosze:
        raise ValueError("paid amount is lower than total")
    return paid_grosze - total_grosze
