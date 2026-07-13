from cash_assistant.controller.time import POLAND_TIME_ZONE, now_in_poland


def test_now_in_poland_returns_timezone_aware_datetime_in_poland() -> None:
    value = now_in_poland()

    assert value.tzinfo is POLAND_TIME_ZONE
    assert value.utcoffset() is not None
    assert value.microsecond == 0
