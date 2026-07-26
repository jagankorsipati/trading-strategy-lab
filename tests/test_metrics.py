from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from trading_lab.backtesting.metrics import calculate_metrics
from trading_lab.models import Direction, ExitReason, Trade

NOW = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))


def trade(pnl: float) -> Trade:
    return Trade(
        "QQQ",
        Direction.LONG,
        NOW,
        100,
        NOW,
        100 + pnl / 10,
        10,
        99,
        102,
        0,
        0,
        pnl,
        ExitReason.END_OF_DAY,
    )


def test_metrics_are_calculated():
    metrics = calculate_metrics(
        [trade(100), trade(-50), trade(25)],
        [(NOW, 10_000), (NOW, 10_100), (NOW, 10_050), (NOW, 10_075)],
        10_000,
    )
    assert metrics["total_pnl"] == 75
    assert metrics["total_return"] == pytest.approx(0.0075)
    assert metrics["win_rate"] == pytest.approx(2 / 3)
    assert metrics["average_winner"] == 62.5
    assert metrics["average_loser"] == -50
    assert metrics["profit_factor"] == 2.5
    assert metrics["maximum_drawdown"] == pytest.approx(50 / 10_100)
    assert metrics["largest_winning_trade"] == 100
    assert metrics["largest_losing_trade"] == -50


def test_empty_metrics_protect_division_by_zero():
    metrics = calculate_metrics([], [], 10_000)
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0
    assert metrics["profit_factor"] == 0
    assert metrics["maximum_drawdown"] == 0
