from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.config.settings import BacktestConfig, ORBConfig, ReferenceORBConfig
from trading_lab.market.calendar import MarketCalendar, NyseCalendar
from trading_lab.models import MarketBar
from trading_lab.reporting.research import summarize_backtest
from trading_lab.research.models import (
    DataQualityStatus,
    DateRange,
    PeriodResult,
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardWindow,
)
from trading_lab.strategies.orb import ORBStrategy
from trading_lab.strategies.reference_orb import ReferenceORBStrategy

QualityLookup = Callable[[DateRange], DataQualityStatus]
SUPPORTED_STRATEGIES = ("orb-v1", "reference-orb-v1")


def _fixed_components(strategy_name: str, slippage_bps: float):
    if strategy_name == "orb-v1":
        return ORBStrategy(ORBConfig()), BacktestConfig(
            starting_capital=10_000,
            position_size=10,
            stop_loss_pct=0.005,
            take_profit_pct=0.01,
            trading_fee=0,
            slippage_bps=slippage_bps,
        )
    if strategy_name == "reference-orb-v1":
        return ReferenceORBStrategy(ReferenceORBConfig()), BacktestConfig(
            starting_capital=25_000,
            position_size=1,
            trading_fee=0,
            slippage_bps=slippage_bps,
        )
    raise ValueError(f"unsupported frozen strategy: {strategy_name}")


def run_fixed_strategy_walk_forward(
    *,
    strategy_name: str,
    bars: Sequence[MarketBar],
    config: WalkForwardConfig,
    windows: Sequence[WalkForwardWindow],
    quality_lookup: QualityLookup,
    calendar: MarketCalendar | None = None,
) -> WalkForwardResult:
    """Evaluate an unchanged strategy independently in every window period."""
    market_calendar = calendar or NyseCalendar()
    ordered = list(bars)
    if not ordered:
        raise ValueError("walk-forward evaluation requires market bars")
    results: list[PeriodResult] = []
    for friction_bps in config.slippage_bps:
        for window in windows:
            for purpose, period in window.periods():
                period_bars = [
                    bar for bar in ordered if period.start <= bar.timestamp.date() <= period.end
                ]
                if not period_bars:
                    raise ValueError(
                        f"no data for window {window.window_id} {purpose.value} period"
                    )
                regular_minutes = sum(
                    (session := market_calendar.session(bar.timestamp.date())) is not None
                    and session.contains(bar.timestamp)
                    for bar in period_bars
                )
                strategy, backtest_config = _fixed_components(strategy_name, friction_bps)
                backtest = BacktestEngine(
                    strategy, backtest_config, market_calendar
                ).run(period_bars)
                results.append(
                    PeriodResult(
                        window_id=window.window_id,
                        purpose=purpose,
                        start_date=period.start,
                        end_date=period.end,
                        strategy_name=strategy_name,
                        friction_bps=friction_bps,
                        metrics=summarize_backtest(backtest, regular_minutes),
                        data_quality=quality_lookup(period),
                    )
                )
    return WalkForwardResult(
        mode="Fixed-strategy rolling out-of-sample evaluation",
        strategy_name=strategy_name,
        config=config,
        windows=tuple(windows),
        periods=tuple(results),
    )
