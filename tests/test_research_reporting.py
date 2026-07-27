from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trading_lab.models import MarketBar
from trading_lab.reporting.research import (
    annualized_daily_ratios,
    buy_and_hold_benchmark,
)

UTC = ZoneInfo("UTC")


def test_daily_ratios_use_session_ending_equity():
    start = datetime(2025, 1, 2, tzinfo=UTC)
    curve = [
        (start, 100),
        (start + timedelta(minutes=1), 101),
        (start + timedelta(days=1), 100),
        (start + timedelta(days=2), 102),
    ]
    sharpe, sortino = annualized_daily_ratios(curve, 100)
    assert sharpe is not None
    assert sortino is None  # only one negative daily return


def test_buy_and_hold_uses_first_open_and_last_close():
    bars = [
        MarketBar(datetime(2025, 1, 2, 14, 30, tzinfo=UTC), 100, 101, 99, 101, 1),
        MarketBar(datetime(2025, 1, 3, 20, 59, tzinfo=UTC), 101, 111, 100, 110, 1),
    ]
    result = buy_and_hold_benchmark(bars, 10_000)
    assert result["entry_price"] == 100
    assert result["exit_price"] == 110
    assert result["ending_equity"] == pytest.approx(11_000)
    assert result["total_return"] == pytest.approx(0.10)
