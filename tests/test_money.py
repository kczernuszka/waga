"""Tests for money helpers."""

import pytest

from cash_assistant.core.money import (
    calculate_change,
    round_to_nearest_50_grosze,
)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (4224, 4200),
        (4225, 4250),
        (4249, 4250),
        (4250, 4250),
        (4274, 4250),
        (4275, 4300),
    ],
)
def test_round_to_nearest_50_grosze(amount: int, expected: int) -> None:
    assert round_to_nearest_50_grosze(amount) == expected


def test_round_to_nearest_50_grosze_rejects_negative_amount() -> None:
    with pytest.raises(ValueError):
        round_to_nearest_50_grosze(-1)


def test_calculate_change() -> None:
    assert calculate_change(paid_grosze=5000, total_grosze=4250) == 750


def test_calculate_change_accepts_exact_payment() -> None:
    assert calculate_change(paid_grosze=4250, total_grosze=4250) == 0


@pytest.mark.parametrize(
    ("paid", "total"),
    [
        (4200, 4250),
        (-1, 0),
        (0, -1),
    ],
)
def test_calculate_change_rejects_invalid_amounts(paid: int, total: int) -> None:
    with pytest.raises(ValueError):
        calculate_change(paid_grosze=paid, total_grosze=total)
