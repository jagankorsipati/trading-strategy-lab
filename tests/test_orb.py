from trading_lab.config.settings import ORBConfig
from trading_lab.models import Direction, TradeDirection
from trading_lab.strategies.orb import ORBStrategy

from conftest import make_bar


def test_opening_range_high_and_low(opening_bars):
    strategy = ORBStrategy(ORBConfig())
    for bar in opening_bars:
        assert strategy.on_bar(bar, False) is None
    assert strategy.opening_range_high == 102
    assert strategy.opening_range_low == 98


def test_breakout_only_after_range_and_no_lookahead(opening_bars):
    strategy = ORBStrategy(ORBConfig())
    # A large high inside the range updates the range; it cannot signal on itself.
    bars = opening_bars + [make_bar(44, 100, 105, 99, 104)]
    assert all(strategy.on_bar(bar, False) is None for bar in bars)
    assert strategy.opening_range_high == 105
    assert strategy.on_bar(make_bar(45, 104, 105, 103, 104.9), False) is None
    signal = strategy.on_bar(make_bar(46, 105, 106, 104, 105.1), False)
    assert signal is not None
    assert signal.timestamp.minute == 46


def test_long_breakout(opening_bars):
    strategy = ORBStrategy(ORBConfig(trade_direction=TradeDirection.LONG))
    for bar in opening_bars:
        strategy.on_bar(bar, False)
    signal = strategy.on_bar(make_bar(45, 102, 103, 101, 102.5), False)
    assert signal is not None and signal.direction == Direction.LONG


def test_short_breakout(opening_bars):
    strategy = ORBStrategy(ORBConfig(trade_direction=TradeDirection.SHORT))
    for bar in opening_bars:
        strategy.on_bar(bar, False)
    signal = strategy.on_bar(make_bar(45, 98, 99, 97, 97.5), False)
    assert signal is not None and signal.direction == Direction.SHORT


def test_maximum_trades_per_day(opening_bars):
    strategy = ORBStrategy(ORBConfig(maximum_trades_per_day=1))
    for bar in opening_bars:
        strategy.on_bar(bar, False)
    signal = strategy.on_bar(make_bar(45, 102, 103, 101, 102.5), False)
    assert signal
    strategy.on_signal_executed(signal)
    assert strategy.on_bar(make_bar(46, 102, 103, 97, 97.5), False) is None
