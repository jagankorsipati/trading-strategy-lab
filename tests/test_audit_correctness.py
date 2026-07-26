from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.backtesting.metrics import calculate_metrics
from trading_lab.config.settings import BacktestConfig, ORBConfig
from trading_lab.data.loader import validate_bars
from trading_lab.models import Direction, ExitReason, MarketBar, TradeDirection
from trading_lab.strategies.orb import ORBStrategy

from conftest import EASTERN, make_bar


def engine(
    bars,
    *,
    orb_config: ORBConfig | None = None,
    backtest_config: BacktestConfig | None = None,
):
    return BacktestEngine(
        ORBStrategy(orb_config or ORBConfig()),
        backtest_config or BacktestConfig(position_size=10),
    ).run(bars)


def test_breakout_executes_at_next_bar_open_and_respects_gap(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 105, 105.5, 104.5, 105),
        ]
    )
    assert result.trades[0].entry_timestamp.minute == 46
    assert result.trades[0].entry_price == 105
    assert result.trades[0].entry_price != 102  # never fill at the ORB threshold


def test_entry_bar_with_stop_and_target_uses_stop_first(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 100, 105, 95, 101),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.exit_price == pytest.approx(99.5)


def test_long_stop_gap_fills_at_worse_open(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 103, 103.2, 102.8, 103),
            make_bar(47, 90, 91, 89, 90),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.exit_price == 90


def test_short_stop_gap_fills_at_worse_open(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 98, 99, 96, 97),
            make_bar(46, 97, 97.2, 96.8, 97),
            make_bar(47, 110, 111, 109, 110),
        ],
        orb_config=ORBConfig(trade_direction=TradeDirection.SHORT),
    )
    trade = result.trades[0]
    assert trade.direction == Direction.SHORT
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.exit_price == 110


def test_take_profit_gap_does_not_invent_price_improvement(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 103, 103.2, 102.8, 103),
            make_bar(47, 110, 111, 109, 110),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.TAKE_PROFIT
    assert trade.exit_price == pytest.approx(103 * 1.01)


def test_fixed_quantity_order_rejected_without_buying_power(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 103, 103.2, 102.8, 103),
        ],
        backtest_config=BacktestConfig(
            starting_capital=1_000, position_size=10
        ),
    )
    assert result.trades == []
    assert result.executions == []
    assert result.final_cash == 1_000


@pytest.mark.parametrize("direction", [TradeDirection.LONG, TradeDirection.SHORT])
def test_cash_returns_to_equity_after_flat_round_trip(opening_bars, direction):
    breakout = (
        make_bar(45, 102, 104, 101, 103)
        if direction == TradeDirection.LONG
        else make_bar(45, 98, 99, 96, 97)
    )
    fill = (
        make_bar(46, 103, 103.2, 102.8, 103)
        if direction == TradeDirection.LONG
        else make_bar(46, 97, 97.2, 96.8, 97)
    )
    result = engine(
        opening_bars + [breakout, fill],
        orb_config=ORBConfig(trade_direction=direction),
    )
    assert result.final_cash == pytest.approx(10_000)
    assert result.metrics["ending_capital"] == pytest.approx(10_000)


def test_missing_eod_bar_closes_before_next_session_gap(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 103, 103.2, 102.8, 103),
            make_bar(47, 103, 103.2, 102.8, 103),
            make_bar(30, 50, 51, 49, 50, day=3),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_timestamp.day == 2
    assert trade.exit_timestamp.minute == 47
    assert trade.exit_price == 103
    assert trade.exit_reason == ExitReason.END_OF_DAY


def test_after_hours_bar_cannot_change_pre_cutoff_liquidation(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 103, 103.2, 102.8, 103),
            make_bar(58, 103, 103.2, 102.8, 103, hour=15),
            make_bar(0, 50, 200, 40, 50, hour=16),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_timestamp.hour == 15
    assert trade.exit_timestamp.minute == 58
    assert trade.exit_price == 103
    assert trade.exit_reason == ExitReason.END_OF_DAY


def test_max_trades_counts_fills_not_repeated_signals(opening_bars):
    result = engine(
        opening_bars
        + [
            make_bar(45, 102, 104, 101, 103),
            make_bar(46, 103, 103.1, 100, 101),
            make_bar(47, 103, 104, 102, 103.5),
            make_bar(48, 103.5, 104, 100, 101),
        ],
        orb_config=ORBConfig(maximum_trades_per_day=1),
    )
    assert len(result.trades) == 1


def test_strategy_range_and_trade_count_reset_each_day():
    strategy = ORBStrategy(ORBConfig(maximum_trades_per_day=1))
    strategy.on_bar(make_bar(30, 100, 102, 98, 100), False)
    signal = strategy.on_bar(make_bar(45, 102, 103, 101, 102.5), False)
    assert signal is not None
    strategy.on_signal_executed(signal)
    assert strategy.trades_today == 1

    strategy.on_bar(make_bar(30, 200, 202, 198, 200, day=3), False)
    assert strategy.session_date is not None
    assert strategy.session_date.day == 3
    assert strategy.opening_range_high == 202
    assert strategy.opening_range_low == 198
    assert strategy.trades_today == 0


def test_validation_normalizes_utc_to_new_york():
    utc = ZoneInfo("UTC")
    bars = [
        MarketBar(datetime(2025, 1, 2, 14, 30, tzinfo=utc), 100, 101, 99, 100, 1)
    ]
    normalized = validate_bars(bars)
    assert normalized[0].timestamp.hour == 9
    assert normalized[0].timestamp.tzinfo == EASTERN


def test_new_york_dst_conversion_in_winter_and_summer():
    utc = ZoneInfo("UTC")
    winter = validate_bars(
        [MarketBar(datetime(2025, 1, 2, 14, 30, tzinfo=utc), 100, 101, 99, 100, 1)]
    )[0]
    summer = validate_bars(
        [MarketBar(datetime(2025, 7, 2, 13, 30, tzinfo=utc), 100, 101, 99, 100, 1)]
    )[0]
    assert winter.timestamp.hour == summer.timestamp.hour == 9
    assert winter.timestamp.utcoffset().total_seconds() == -5 * 3600
    assert summer.timestamp.utcoffset().total_seconds() == -4 * 3600


def test_max_drawdown_uses_starting_capital_as_initial_peak():
    metrics = calculate_metrics([], [(object(), 9_900)], 10_000)
    assert metrics["maximum_drawdown"] == pytest.approx(0.01)
