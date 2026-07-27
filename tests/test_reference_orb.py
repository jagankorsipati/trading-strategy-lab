from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.backtesting.portfolio import Portfolio
from trading_lab.config.settings import BacktestConfig, ReferenceORBConfig
from trading_lab.data.aggregation import aggregate_complete_candle
from trading_lab.models import (
    Direction,
    ExitReason,
    MarketBar,
    RiskSizing,
    Signal,
)
from trading_lab.strategies.reference_orb import ReferenceORBStrategy

EASTERN = ZoneInfo("America/New_York")
NORMAL_DAY = date(2025, 7, 2)
EARLY_CLOSE_DAY = date(2025, 7, 3)


def bar(
    minute: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    hour: int = 9,
    day: date = NORMAL_DAY,
) -> MarketBar:
    return MarketBar(
        datetime(
            day.year,
            day.month,
            day.day,
            hour,
            minute,
            tzinfo=EASTERN,
        ),
        open_,
        high,
        low,
        close,
        1_000,
    )


def bullish_opening(day: date = NORMAL_DAY) -> list[MarketBar]:
    return [
        bar(30, 100, 101, 99.5, 100.2, day=day),
        bar(31, 100.2, 101.2, 100, 100.8, day=day),
        bar(32, 100.8, 101.5, 100.5, 101.2, day=day),
        bar(33, 101.2, 102, 100.7, 101.4, day=day),
        bar(34, 101.4, 101.6, 99, 101, day=day),
    ]


def short_opening(day: date = NORMAL_DAY) -> list[MarketBar]:
    return [
        bar(30, 100, 100.5, 99.5, 99.8, day=day),
        bar(31, 99.8, 100, 99.2, 99.6, day=day),
        bar(32, 99.6, 99.8, 99, 99.4, day=day),
        bar(33, 99.4, 99.7, 98.8, 99.2, day=day),
        bar(34, 99.2, 101, 98.5, 99, day=day),
    ]


def run(bars: list[MarketBar], *, slippage_bps: float = 0):
    return BacktestEngine(
        ReferenceORBStrategy(),
        BacktestConfig(
            starting_capital=25_000,
            position_size=1,
            slippage_bps=slippage_bps,
        ),
    ).run(bars)


def test_first_five_minute_candle_construction():
    candle = aggregate_complete_candle(bullish_opening())
    assert candle.timestamp.minute == 30
    assert candle.open == 100
    assert candle.high == 102
    assert candle.low == 99
    assert candle.close == 101
    assert candle.volume == 5_000


def test_aggregation_rejects_missing_minute():
    bars = bullish_opening()
    bars[3] = bar(35, 101.2, 102, 100.7, 101.4)
    with pytest.raises(ValueError, match="consecutive"):
        aggregate_complete_candle(bars)


@pytest.mark.parametrize(
    ("opening", "expected"),
    [(bullish_opening, Direction.LONG), (short_opening, Direction.SHORT)],
)
def test_direction_comes_from_first_candle_body(opening, expected):
    strategy = ReferenceORBStrategy()
    signals = [strategy.on_bar(item, False) for item in opening()]
    assert all(signal is None for signal in signals[:-1])
    assert signals[-1] is not None
    assert signals[-1].direction == expected


def test_signal_executes_at_second_candle_open_without_lookahead():
    bars = bullish_opening() + [
        bar(35, 101, 101.5, 100, 101.2),
        bar(36, 101.2, 101.6, 100.8, 101.5),
    ]
    result = run(bars)
    trade = result.trades[0]
    assert trade.entry_timestamp.minute == 35
    assert trade.entry_price == 101
    assert trade.direction == Direction.LONG


def test_stop_and_ten_r_target_use_actual_entry():
    result = run(
        bullish_opening()
        + [
            bar(35, 101, 101.5, 100, 101.2),
            bar(36, 101.2, 101.6, 100.8, 101.5),
        ]
    )
    trade = result.trades[0]
    assert trade.stop_price == 99
    assert trade.take_profit_price == 121
    assert trade.quantity == 125  # $250 fixed risk / $2 risk per share
    assert trade.fees == pytest.approx(0.125)


def test_risk_sizing_honors_four_x_leverage_cap():
    portfolio = Portfolio(BacktestConfig(starting_capital=200_000, position_size=1))
    signal = Signal(
        "QQQ",
        bullish_opening()[-1].timestamp,
        Direction.LONG,
        100,
        stop_price=99.9,
        reward_risk_multiple=10,
        risk_sizing=RiskSizing(25_000, 0.01, 4, 0.05, 0.0005),
    )
    assert portfolio.open(signal)
    assert portfolio.position is not None
    assert portfolio.position.quantity == 1_000


def test_conservative_buying_power_caps_reference_leverage():
    portfolio = Portfolio(BacktestConfig(starting_capital=25_000, position_size=1))
    signal = Signal(
        "QQQ",
        bullish_opening()[-1].timestamp,
        Direction.LONG,
        100,
        stop_price=99.9,
        reward_risk_multiple=10,
        risk_sizing=RiskSizing(25_000, 0.01, 4, 0.05, 0.0005),
    )
    assert portfolio.open(signal)
    assert portfolio.position is not None
    assert portfolio.position.quantity == 249
    assert portfolio.position.entry_fee == pytest.approx(0.1245)


def test_daily_trade_limit_emits_only_one_setup():
    strategy = ReferenceORBStrategy()
    signal = None
    for item in bullish_opening():
        signal = strategy.on_bar(item, False)
    assert signal is not None
    strategy.on_signal_executed(signal)
    assert strategy.on_bar(bar(35, 101, 110, 90, 105), False) is None
    assert strategy.trades_today == 1


def test_rounded_two_decimal_doji_skips_session():
    opening = bullish_opening()
    opening[-1] = bar(34, 101.4, 101.6, 99, 100.004)
    strategy = ReferenceORBStrategy()
    assert all(strategy.on_bar(item, False) is None for item in opening)


def test_risk_distance_below_five_cents_rejects_entry():
    opening = [
        bar(30, 100, 100.01, 99.99, 100),
        bar(31, 100, 100.01, 99.99, 100),
        bar(32, 100, 100.01, 99.99, 100),
        bar(33, 100, 100.01, 99.99, 100),
        bar(34, 100, 100.02, 99.99, 100.01),
    ]
    result = run(opening + [bar(35, 100.02, 100.03, 100, 100.02)])
    assert result.trades == []


def test_entry_candle_risk_is_not_ignored_and_stop_wins_ambiguity():
    result = run(
        bullish_opening()
        + [bar(35, 101, 125, 98, 110)]
    )
    trade = result.trades[0]
    assert trade.exit_timestamp.minute == 35
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.exit_price == 99


def test_gap_through_stop_uses_worse_open():
    result = run(
        bullish_opening()
        + [
            bar(35, 101, 102, 100, 101),
            bar(36, 95, 96, 94, 95),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.exit_price == 95


def test_slippage_is_adverse_on_reference_entry_and_exit():
    result = run(
        bullish_opening()
        + [
            bar(35, 101, 102, 100, 101),
            bar(36, 95, 96, 94, 95),
        ],
        slippage_bps=10,
    )
    trade = result.trades[0]
    assert trade.entry_price == pytest.approx(101.101)
    assert trade.exit_price < 95


def test_early_close_uses_final_calendar_bar_and_ignores_after_hours():
    bars = bullish_opening(EARLY_CLOSE_DAY) + [
        bar(35, 101, 102, 100, 101, day=EARLY_CLOSE_DAY),
        bar(59, 105, 106, 104, 105, hour=12, day=EARLY_CLOSE_DAY),
        bar(0, 50, 200, 1, 50, hour=13, day=EARLY_CLOSE_DAY),
    ]
    result = run(bars)
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.END_OF_DAY
    assert (trade.exit_timestamp.hour, trade.exit_timestamp.minute) == (12, 59)
    assert trade.exit_price == 105


def test_premarket_bar_cannot_change_first_candle():
    bars = [
        bar(0, 1, 1_000, 1, 900, hour=9),
        *bullish_opening(),
        bar(35, 101, 102, 100, 101),
    ]
    result = run(bars)
    assert result.trades[0].stop_price == 99
