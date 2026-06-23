from typing import Any

import pytest

from cash_assistant.hardware.mock_scale import MockScale
from cash_assistant.hardware.scale import Scale


def test_scale_interface_cannot_be_instantiated_directly() -> None:
    scale_type: Any = Scale

    with pytest.raises(TypeError):
        scale_type()


def test_mock_scale_initial_weight_is_zero() -> None:
    scale = MockScale()

    assert scale.get_weight_grams() == 0


def test_mock_scale_returns_set_weight_in_grams() -> None:
    scale = MockScale()

    scale.set_weight_grams(1_500)

    assert scale.get_weight_grams() == 1_500


def test_mock_scale_tare_resets_weight_to_zero() -> None:
    scale = MockScale()
    scale.set_weight_grams(1_500)

    scale.tare()

    assert scale.get_weight_grams() == 0


def test_mock_scale_rejects_negative_weight() -> None:
    scale = MockScale()

    with pytest.raises(ValueError):
        scale.set_weight_grams(-1)
