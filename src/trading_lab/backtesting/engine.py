from __future__ import annotations

from dataclasses import dataclass

from trading_lab.backtesting.metrics import calculate_metrics
from trading_lab.backtesting.portfolio import Portfolio
from trading_lab.config.settings import BacktestConfig
from trading_lab.data.loader import validate_bars
from trading_lab.models import Direction, ExitReason, MarketBar, Signal, Trade
from trading_lab.strategies.base import TradingStrategy


@dataclass(frozen=True)
class BacktestResult:
    trades: list[Trade]
    metrics: dict[str, float | int | None]
    equity_curve: list[tuple[object, float]]
    start_timestamp: object
    end_timestamp: object
    executions: list[object]
    final_cash: float


class BacktestEngine:
    def __init__(self, strategy: TradingStrategy, config: BacktestConfig) -> None:
        self.strategy = strategy
        self.config = config

    def _risk_exit(
        self, portfolio: Portfolio, bar: MarketBar
    ) -> tuple[ExitReason, float] | None:
        position = portfolio.position
        if position is None:
            return None
        if position.direction == Direction.LONG:
            if bar.low <= position.stop_price:
                # A sell stop cannot fill above the first available price after
                # a downward gap.
                return ExitReason.STOP_LOSS, min(position.stop_price, bar.open)
            if bar.high >= position.take_profit_price:
                # Use the target itself even after a favorable gap; this avoids
                # inventing price improvement from OHLC data.
                return ExitReason.TAKE_PROFIT, position.take_profit_price
        else:
            if bar.high >= position.stop_price:
                return ExitReason.STOP_LOSS, max(position.stop_price, bar.open)
            if bar.low <= position.take_profit_price:
                return ExitReason.TAKE_PROFIT, position.take_profit_price
        return None

    def _close_for_risk_or_eod(
        self, portfolio: Portfolio, bar: MarketBar
    ) -> bool:
        risk_exit = self._risk_exit(portfolio, bar)
        if risk_exit is not None:
            reason, reference = risk_exit
        elif bar.timestamp.time().replace(tzinfo=None) >= self.config.end_of_day:
            reason, reference = ExitReason.END_OF_DAY, bar.close
        else:
            return False
        portfolio.close(bar, reference, reason)
        self.strategy.on_trade_closed(bar)
        return True

    def run(self, bars: list[MarketBar]) -> BacktestResult:
        bars = validate_bars(bars)
        self.strategy.initialize()
        portfolio = Portfolio(self.config)
        pending_signal: Signal | None = None
        previous_bar: MarketBar | None = None

        for bar in bars:
            local_time = bar.timestamp.time().replace(tzinfo=None)
            closed_this_bar = False

            # Missing an explicit EOD bar must never carry exposure overnight.
            crossed_session = (
                previous_bar is not None
                and bar.timestamp.date() != previous_bar.timestamp.date()
            )
            crossed_cutoff = (
                previous_bar is not None
                and bar.timestamp.date() == previous_bar.timestamp.date()
                and previous_bar.timestamp.time().replace(tzinfo=None)
                < self.config.end_of_day
                < local_time
            )
            if crossed_session or crossed_cutoff:
                pending_signal = None
                if portfolio.position is not None:
                    portfolio.close(
                        previous_bar, previous_bar.close, ExitReason.END_OF_DAY
                    )
                    self.strategy.on_trade_closed(previous_bar)
                    portfolio.equity_curve[-1] = (
                        previous_bar.timestamp,
                        portfolio.cash,
                    )

            # A signal is based on a completed bar. It first becomes executable
            # at the following same-session bar's open.
            entered_this_bar = False
            if pending_signal is not None:
                executable = (
                    pending_signal.timestamp.date() == bar.timestamp.date()
                    and local_time < self.config.end_of_day
                )
                if executable:
                    execution_signal = Signal(
                        pending_signal.symbol,
                        bar.timestamp,
                        pending_signal.direction,
                        bar.open,
                    )
                    entered_this_bar = portfolio.open(execution_signal)
                    if entered_this_bar:
                        self.strategy.on_signal_executed(execution_signal)
                pending_signal = None

            if portfolio.position is not None:
                closed_this_bar = self._close_for_risk_or_eod(portfolio, bar)

            signal = self.strategy.on_bar(
                bar,
                portfolio.position is not None
                or closed_this_bar
                or pending_signal is not None,
            )
            if signal is not None and local_time < self.config.end_of_day:
                pending_signal = signal
            portfolio.mark(bar)
            previous_bar = bar

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
            portfolio.cash,
        )
