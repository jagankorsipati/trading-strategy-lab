from __future__ import annotations

import subprocess
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from scripts.run_execution_study import parse_args
from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.backtesting.portfolio import Portfolio
from trading_lab.config.settings import BacktestConfig
from trading_lab.execution import (
    ExecutionContext,
    ExecutionStatus,
    FixedBpsExecutionConfig,
    FixedBpsExecutionModel,
    LatencyExecutionConfig,
    LatencyExecutionModel,
    LimitFillPolicy,
    LimitOrderExecutionConfig,
    LimitOrderExecutionModel,
    OrderIntent,
    OrderSide,
    OrderType,
    RejectionReason,
    SpreadBasedExecutionModel,
    SpreadExecutionConfig,
    SpreadMode,
    VolumeAwareExecutionConfig,
    VolumeAwareExecutionModel,
)
from trading_lab.execution.reporting import write_execution_study
from trading_lab.market.calendar import TradingSession
from trading_lab.models import Direction, ExitReason, MarketBar, Signal
from trading_lab.strategies.base import TradingStrategy

EASTERN = ZoneInfo("America/New_York")


def _bar(minute=0, *, open=100, high=101, low=99, close=100, volume=10_000):
    return MarketBar(
        datetime(2025, 1, 2, 9, 30, tzinfo=EASTERN) + timedelta(minutes=minute),
        open, high, low, close, volume,
    )


def _session(close_hour=16):
    return TradingSession(
        date(2025, 1, 2),
        datetime(2025, 1, 2, 9, 30, tzinfo=EASTERN),
        datetime(2025, 1, 2, close_hour, 0, tzinfo=EASTERN),
        close_hour != 16,
    )


def _intent(side=OrderSide.BUY, quantity=10, reference=100, **kwargs):
    return OrderIntent(
        _bar().timestamp,
        side,
        kwargs.pop("order_type", OrderType.MARKET),
        quantity,
        reference,
        **kwargs,
    )


def _context(bar=None, session=None, delayed=0):
    return ExecutionContext(bar or _bar(), session or _session(), delayed_bars=delayed)


def test_fixed_bps_is_adverse_for_buy_and_sell():
    model = FixedBpsExecutionModel(FixedBpsExecutionConfig(2))
    buy = model.execute(_intent(OrderSide.BUY), _context())
    sell = model.execute(_intent(OrderSide.SELL), _context())
    assert buy.fill.price == pytest.approx(100.02)
    assert sell.fill.price == pytest.approx(99.98)
    assert buy.fill.costs.fixed_slippage == pytest.approx(0.20)
    assert sell.fill.costs.fixed_slippage == pytest.approx(0.20)


def test_spread_cost_is_adverse_on_both_sides_and_time_of_day_selects_proxy():
    constant = SpreadBasedExecutionModel(
        SpreadExecutionConfig(constant_spread_bps=4)
    )
    assert constant.execute(_intent(OrderSide.BUY), _context()).fill.price == pytest.approx(100.02)
    assert constant.execute(_intent(OrderSide.SELL), _context()).fill.price == pytest.approx(99.98)

    timed = SpreadBasedExecutionModel(
        SpreadExecutionConfig(
            mode=SpreadMode.TIME_OF_DAY,
            open_spread_bps=6,
            middle_spread_bps=2,
            close_spread_bps=4,
            open_window_minutes=30,
            close_window_minutes=30,
        )
    )
    assert timed.spread_bps(_context(_bar(5))) == 6
    assert timed.spread_bps(_context(_bar(120))) == 2
    assert timed.spread_bps(_context(_bar(380))) == 4


def test_volume_participation_partial_rejection_and_impact():
    context = _context(_bar(volume=100))
    partial_model = VolumeAwareExecutionModel(
        VolumeAwareExecutionConfig(
            maximum_participation_rate=0.10,
            minimum_bar_volume=0,
            impact_coefficient_bps=100,
            maximum_impact_bps=100,
            allow_partial_fills=True,
        )
    )
    partial = partial_model.execute(_intent(quantity=25), context)
    assert partial.status == ExecutionStatus.PARTIALLY_FILLED
    assert partial.filled_quantity == 10
    assert partial.unfilled_quantity == 15

    rejecting = VolumeAwareExecutionModel(
        VolumeAwareExecutionConfig(
            maximum_participation_rate=0.10,
            minimum_bar_volume=0,
            allow_partial_fills=False,
        )
    ).execute(_intent(quantity=25), context)
    assert rejecting.status == ExecutionStatus.REJECTED
    assert rejecting.rejection_reason == RejectionReason.INSUFFICIENT_LIQUIDITY

    small = partial_model.execute(_intent(quantity=5), context)
    large = partial_model.execute(_intent(quantity=10), context)
    assert large.fill.costs.market_impact / 10 > small.fill.costs.market_impact / 5


@pytest.mark.parametrize(
    "side,order_type,level,bar,filled",
    [
        (OrderSide.BUY, OrderType.LIMIT, 100, _bar(low=99), True),
        (OrderSide.SELL, OrderType.LIMIT, 100, _bar(high=101), True),
        (OrderSide.BUY, OrderType.STOP, 100, _bar(high=101), True),
        (OrderSide.SELL, OrderType.STOP, 100, _bar(low=99), True),
        (OrderSide.BUY, OrderType.LIMIT, 98, _bar(low=99), False),
    ],
)
def test_limit_and_stop_trigger_rules(side, order_type, level, bar, filled):
    model = LimitOrderExecutionModel(
        LimitOrderExecutionConfig(LimitFillPolicy.TRADE_THROUGH_REQUIRED)
    )
    intent = _intent(
        side,
        order_type=order_type,
        limit_price=level if order_type == OrderType.LIMIT else None,
        stop_price=level if order_type == OrderType.STOP else None,
    )
    result = model.execute(intent, _context(bar))
    assert (result.fill is not None) is filled


def test_conservative_policy_rejects_touch_only_ambiguity():
    model = LimitOrderExecutionModel()
    intent = _intent(
        OrderSide.BUY,
        order_type=OrderType.LIMIT,
        limit_price=99,
    )
    result = model.execute(intent, _context(_bar(low=99)))
    assert result.status == ExecutionStatus.NOT_FILLED
    assert result.rejection_reason == RejectionReason.AMBIGUOUS_BAR


def test_latency_cost_and_delay_are_deterministic():
    model = LatencyExecutionModel(
        LatencyExecutionConfig(delay_bars=2, adverse_bps_per_delayed_bar=1)
    )
    result = model.execute(_intent(), _context(delayed=2))
    assert model.entry_delay_bars == 2
    assert result.fill.price == pytest.approx(100.02)
    assert result.fill.costs.latency == pytest.approx(0.20)


class OneSignalStrategy(TradingStrategy):
    def initialize(self):
        self.sent = False

    def on_bar(self, bar, has_open_position):
        if not self.sent:
            self.sent = True
            return Signal("QQQ", bar.timestamp, Direction.LONG, bar.close)
        return None


def test_engine_applies_one_bar_latency_without_future_leakage():
    bars = [_bar(i, high=100.1, low=99.9) for i in range(4)]
    result = BacktestEngine(
        OneSignalStrategy(),
        BacktestConfig(position_size=1),
        execution_model=LatencyExecutionModel(LatencyExecutionConfig(delay_bars=1)),
    ).run(bars)
    assert result.trades[0].entry_timestamp == bars[2].timestamp


def test_latency_does_not_cross_session_close_silently():
    bars = [
        MarketBar(datetime(2025, 7, 3, 12, 58, tzinfo=EASTERN), 100, 100.1, 99.9, 100, 1_000),
        MarketBar(datetime(2025, 7, 3, 12, 59, tzinfo=EASTERN), 100, 100.1, 99.9, 100, 1_000),
    ]
    result = BacktestEngine(
        OneSignalStrategy(),
        BacktestConfig(position_size=1),
        execution_model=LatencyExecutionModel(LatencyExecutionConfig(delay_bars=1)),
    ).run(bars)
    assert not result.trades
    assert result.order_results[-1].rejection_reason == RejectionReason.SESSION_ENDED


def test_default_and_explicit_fixed_model_are_identical():
    bars = [_bar(i, high=100.1, low=99.9) for i in range(3)]
    config = BacktestConfig(position_size=1, slippage_bps=2)
    default = BacktestEngine(OneSignalStrategy(), config).run(bars)
    explicit = BacktestEngine(
        OneSignalStrategy(), config,
        execution_model=FixedBpsExecutionModel(FixedBpsExecutionConfig(2)),
    ).run(bars)
    assert default.metrics == explicit.metrics
    assert default.trades == explicit.trades


def test_partial_fill_and_cost_breakdown_reconcile_with_portfolio_cash():
    model = VolumeAwareExecutionModel(
        VolumeAwareExecutionConfig(
            maximum_participation_rate=0.1,
            minimum_bar_volume=0,
            impact_coefficient_bps=0,
            maximum_impact_bps=1,
            allow_partial_fills=True,
        )
    )
    portfolio = Portfolio(BacktestConfig(position_size=20), model)
    signal = Signal("QQQ", _bar().timestamp, Direction.LONG, 100)
    assert portfolio.open(signal, _bar(volume=100), _session())
    assert portfolio.position.quantity == 10
    trade = portfolio.close(_bar(1, open=101, high=101, low=101, close=101), 101, ExitReason.END_OF_DAY, _session())
    assert trade.realized_pnl == pytest.approx(10)
    assert portfolio.cash == pytest.approx(10_010)
    assert portfolio.order_results[0].status == ExecutionStatus.PARTIALLY_FILLED


def test_rejected_order_does_not_change_cash_or_position():
    model = VolumeAwareExecutionModel(
        VolumeAwareExecutionConfig(
            maximum_participation_rate=0.01,
            minimum_bar_volume=1_000,
            allow_partial_fills=False,
        )
    )
    portfolio = Portfolio(BacktestConfig(position_size=10), model)
    signal = Signal("QQQ", _bar().timestamp, Direction.LONG, 100)
    assert not portfolio.open(signal, _bar(volume=10), _session())
    assert portfolio.cash == 10_000
    assert portfolio.position is None


def test_frozen_strategy_git_fingerprints():
    expected = {
        "src/trading_lab/strategies/orb.py": "eea3f866275e03a8985c35ea12a19ee10eaa00c7",
        "src/trading_lab/strategies/reference_orb.py": "354ea9f0f6de67d8908b55a8b8119ef02ab64d9e",
        "src/trading_lab/config/settings.py": "25bb5120c6d2c96ef83fe1b7de1ee478957f68ba",
    }
    for path, fingerprint in expected.items():
        actual = subprocess.check_output(["git", "hash-object", path], text=True).strip()
        assert actual == fingerprint


def test_invalid_execution_configurations_are_rejected():
    with pytest.raises(ValueError):
        FixedBpsExecutionConfig(-1)
    with pytest.raises(ValueError):
        SpreadExecutionConfig(constant_spread_bps=-1)
    with pytest.raises(ValueError):
        VolumeAwareExecutionConfig(maximum_participation_rate=0)
    with pytest.raises(ValueError):
        VolumeAwareExecutionConfig(maximum_participation_rate=1.1)
    with pytest.raises(ValueError):
        VolumeAwareExecutionConfig(impact_coefficient_bps=-1)
    with pytest.raises(ValueError):
        LimitOrderExecutionConfig(adverse_bps=-1)
    with pytest.raises(ValueError):
        LatencyExecutionConfig(delay_bars=-1)
    with pytest.raises(ValueError):
        LatencyExecutionConfig(delay_bars=1, reject_at_session_end=False)
    with pytest.raises(ValueError):
        _intent(quantity=-1)
    with pytest.raises(ValueError):
        _intent(order_type=OrderType.MARKET, limit_price=99)
    with pytest.raises(ValueError):
        _intent(order_type=OrderType.LIMIT, limit_price=-1)
    with pytest.raises(ValueError):
        _intent(order_type=OrderType.MARKET, limit_price=99)


def test_execution_cli_does_not_expose_frozen_strategy_parameters():
    base = ["--data", "bars.csv", "--strategy", "orb-v1"]
    with pytest.raises(SystemExit):
        parse_args(base + ["--opening-range-minutes", "30"])
    reference = ["--data", "bars.csv", "--strategy", "reference-orb-v1"]
    with pytest.raises(SystemExit):
        parse_args(reference + ["--reward-risk-multiple", "2"])


def test_execution_reports_are_generated_without_credentials(tmp_path):
    metrics = {
        "scenario": "synthetic", "total_return": 0.0, "total_pnl": 0.0,
        "trades_attempted": 0, "fully_filled_entries": 0,
        "partially_filled_entries": 0, "unfilled_entries": 0,
        "rejected_entries": 0, "profit_factor": 0.0,
        "maximum_drawdown": 0.0, "total_modeled_execution_cost": 0.0,
    }
    destination = write_execution_study(
        strategy_name="orb-v1",
        assumptions={"synthetic": True},
        scenarios=[{"metrics": metrics, "fills": [], "rejected_orders": []}],
        output_dir=tmp_path / "study",
    )
    assert {path.name for path in destination.iterdir()} == {
        "config.json", "fills.csv", "rejected_orders.csv", "partial_fills.csv",
        "metrics.csv", "summary.json", "report.md",
    }
    contents = "\n".join(path.read_text() for path in destination.iterdir())
    assert "ALPACA_API_KEY" not in contents
    assert "ALPACA_SECRET_KEY" not in contents
