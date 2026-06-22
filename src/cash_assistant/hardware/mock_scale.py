"""Mock scale adapter."""

from cash_assistant.hardware.scale import Scale


class MockScale(Scale):
    def __init__(self) -> None:
        self._weight_grams = 0

    def set_weight_grams(self, weight_grams: int) -> None:
        if weight_grams < 0:
            raise ValueError("weight_grams cannot be negative")
        self._weight_grams = weight_grams

    def get_weight_grams(self) -> int:
        return self._weight_grams

    def tare(self) -> None:
        self._weight_grams = 0

