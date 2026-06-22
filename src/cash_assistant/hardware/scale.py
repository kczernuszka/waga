"""Scale interface."""

from abc import ABC, abstractmethod


class Scale(ABC):
    @abstractmethod
    def get_weight_grams(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def tare(self) -> None:
        raise NotImplementedError

