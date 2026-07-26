from __future__ import annotations

from dataclasses import dataclass

from trading_lab.backtesting.metrics import calculate_metrics
from trading_lab.backtesting.portfolio import Portfolio
from trading_lab.config.settings import BacktestConfig
from trading_lab.data.loader import validate_bars
from trading_lab.models import Direction, ExitReason, MarketBar, Trade
from trading_lab.strategies.base import TradingStrategy


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    metrics: dict[str, float | int | None]
    equity_curve: list[tuple[object, float]]
    start_timestamp: object
    end_timestamp: object
    executions: list[object]


class BacktestEngine:
    def __init__(self, strategy: TradingStrategy, config: BacktestConfig) -> None:
        self.strategy = strategy
        self.config = config

    def _risk_exit(self, portfolio: Portfolio, bar: MarketBar) -> ExitReason | None:
        position = portfolio.position
        if position is None:
            return None
        if position.direction == Direction.LONG:
            if bar.low <= position.stop_price:
                return ExitReason.STOP_LOSS
            if bar.high >= position.take_profit_price:
                return ExitReason.TAKE_PROFIT
        else:
            if bar.high >= position.stop_price:
                return ExitReason.STOP_LOSS
            if bar.low <= position.take_profit_price:
                return ExitReason.TAKE_PROFIT
        return None

    def run(self, bars: list[MarketBar]) -> BacktestResult:
        bars = validate_bars(bars)
        self.strategy.initialize()
        portfolio = Portfolio(self.config)

        for bar in bars:
            local_time = bar.timestamp.time().replace(tzinfo=None)
            closed_this_bar = False
            if portfolio.position is not None:
                reason = self._risk_exit(portfolio, bar)
                reference = None
                if reason == ExitReason.STOP_LOSS:
                    reference = portfolio.position.stop_price
                elif reason == ExitReason.TAKE_PROFIT:
                    reference = portfolio.position.take_profit_price
                elif local_time >= self.config.end_of_day:
                    reason = ExitReason.END_OF_DAY
                    reference = bar.close
                if reason is not None and reference is not None:
                    portfolio.close(bar, reference, reason)
                    self.strategy.on_trade_closed(bar)
                    closed_this_bar = True

            signal = self.strategy.on_bar(
                bar, portfolio.position is not None or closed_this_bar
            )
            if signal is not None and local_time < self.config.end_of_day:
                portfolio.open(signal)
            portfolio.mark(bar)

        # A truncated dataset must still never leave an overnight/open position.
        if portfolio.position is not None:
            last = bars[-1]
            portfolio.close(last, last.close, ExitReason.END_OF_DAY)
            portfolio.equity_curve[-1] = (last.timestamp, portfolio.cash)

        metrics = calculate_metrics(
            portfolio.trades, portfolio.equity_curve, self.config.starting_capital
        )
        return BacktestResult(
            portfolio.trades,
            metrics,
            portfolio.equity_curve,
            bars[0].timestamp,
            bars[-1].timestamp,
            portfolio.executions,
        )
