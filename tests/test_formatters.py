import pytest

from cash_assistant.ui.formatters import (
    format_money,
    format_piece_quantity,
    format_unit_price,
    format_weight_grams,
)


@pytest.mark.parametrize(
    ("grosze", "expected"),
    [
        (0, "0,00 zł"),
        (1, "0,01 zł"),
        (120, "1,20 zł"),
        (4_250, "42,50 zł"),
        (10_000, "100,00 zł"),
    ],
)
def test_format_money(grosze: int, expected: str) -> None:
    assert format_money(grosze) == expected


def test_format_money_rejects_negative_amount() -> None:
    with pytest.raises(ValueError):
        format_money(-1)


@pytest.mark.parametrize(
    ("weight_grams", "expected"),
    [
        (0, "0,00 kg"),
        (1, "0,00 kg"),
        (4, "0,00 kg"),
        (5, "0,01 kg"),
        (994, "0,99 kg"),
        (995, "1,00 kg"),
        (999, "1,00 kg"),
        (1_500, "1,50 kg"),
        (23_000, "23,00 kg"),
    ],
)
def test_format_weight_grams(weight_grams: int, expected: str) -> None:
    assert format_weight_grams(weight_grams) == expected


def test_format_weight_grams_rejects_negative_weight() -> None:
    with pytest.raises(ValueError):
        format_weight_grams(-1)


def test_format_piece_quantity() -> None:
    assert format_piece_quantity(0) == "0 szt."
    assert format_piece_quantity(3) == "3 szt."


def test_format_piece_quantity_rejects_negative_quantity() -> None:
    with pytest.raises(ValueError):
        format_piece_quantity(-1)


def test_format_unit_price_uses_unit_text() -> None:
    assert format_unit_price(699, "kg") == "6,99 zł/kg"
    assert format_unit_price(120, "szt.") == "1,20 zł/szt."


def test_format_unit_price_rejects_empty_unit_text() -> None:
    with pytest.raises(ValueError):
        format_unit_price(699, "")
