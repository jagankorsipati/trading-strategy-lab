from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from trading_lab.models import MarketBar

EASTERN = ZoneInfo("America/New_York")


def make_bar(
    minute: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    hour: int = 9,
    day: int = 2,
) -> MarketBar:
    return MarketBar(
        datetime(2025, 1, day, hour, minute, tzinfo=EASTERN),
        open_,
        high,
        low,
        close,
        1_000,
    )


@pytest.fixture
def opening_bars() -> list[MarketBar]:
    return [
        make_bar(30, 100, 101, 99, 100),
        make_bar(35, 100, 102, 99.5, 101),
        make_bar(40, 101, 101.5, 98, 100),
    ]
