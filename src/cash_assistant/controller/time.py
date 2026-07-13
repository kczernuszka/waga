"""Timezone helpers for controller and presentation layer."""

from datetime import datetime
from zoneinfo import ZoneInfo

POLAND_TIME_ZONE = ZoneInfo("Europe/Warsaw")


def now_in_poland() -> datetime:
    return datetime.now(POLAND_TIME_ZONE).replace(microsecond=0)
