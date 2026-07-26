import pytest

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.config.settings import BacktestConfig, ORBConfig
from trading_lab.models import ExitReason
from trading_lab.strategies.orb import ORBStrategy

from conftest import make_bar


def run(bars, **config):
    return BacktestEngine(
        ORBStrategy(ORBConfig()),
        BacktestConfig(position_size=10, **config),
    ).run(bars)


def test_stop_loss_exit(opening_bars):
    result = run(
        opening_bars
        + [
            make_bar(45, 102, 103, 101, 102.5),
            make_bar(46, 102.5, 102.6, 101, 101.5),
        ]
    )
    assert result.trades[0].exit_reason == ExitReason.STOP_LOSS
    assert result.trades[0].exit_price == pytest.approx(102.5 * 0.995)


def test_take_profit_exit(opening_bars):
    result = run(
        opening_bars
        + [
            make_bar(45, 102, 103, 101, 102.5),
            make_bar(46, 102.5, 104, 102, 103.8),
        ]
    )
    assert result.trades[0].exit_reason == ExitReason.TAKE_PROFIT
    assert result.trades[0].exit_price == pytest.approx(102.5 * 1.01)


def test_end_of_day_exit(opening_bars):
    result = run(
        opening_bars
        + [
            make_bar(45, 102, 103, 101, 102.5),
            make_bar(59, 102.5, 103, 102, 102.8, hour=15),
        ]
    )
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.END_OF_DAY
    assert trade.exit_timestamp.hour == 15


def test_fees_affect_pnl(opening_bars):
    bars = opening_bars + [
        make_bar(45, 102, 103, 101, 102.5),
        make_bar(59, 102.5, 103, 102.2, 102.5, hour=15),
    ]
    result = run(bars, trading_fee=2.0)
    assert result.trades[0].fees == 4
    assert result.trades[0].realized_pnl == pytest.approx(-4)
    assert result.metrics["ending_capital"] == pytest.approx(9_996)


def test_slippage_affects_entry_and_exit(opening_bars):
    bars = opening_bars + [
        make_bar(45, 102, 103, 101, 102.5),
        make_bar(59, 102.5, 103, 102.2, 102.5, hour=15),
    ]
    result = run(bars, slippage_bps=10)
    trade = result.trades[0]
    assert trade.entry_price == pytest.approx(102.6025)
    assert trade.exit_price == pytest.approx(102.3975)
    assert trade.realized_pnl == pytest.approx(-2.05)
    assert trade.slippage == pytest.approx(2.05)


def test_truncated_data_forces_close(opening_bars):
    result = run(opening_bars + [make_bar(45, 102, 103, 101, 102.5)])
    assert result.trades[0].exit_reason == ExitReason.END_OF_DAY
