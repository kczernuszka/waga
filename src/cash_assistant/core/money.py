"""Money helpers.

Amounts are represented as integer grosze.
"""


def format_money(grosze: int) -> str:
    raise NotImplementedError


def parse_money(text: str) -> int:
    raise NotImplementedError


def round_to_nearest_50_grosze(amount_grosze: int) -> int:
    raise NotImplementedError


def calculate_change(paid_grosze: int, total_grosze: int) -> int:
    raise NotImplementedError

