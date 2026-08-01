from __future__ import annotations

from dataclasses import dataclass, replace

from trading_lab.backtesting.metrics import calculate_metrics
from trading_lab.backtesting.portfolio import Portfolio
from trading_lab.config.settings import BacktestConfig
from trading_lab.data.loader import validate_bars
from trading_lab.execution import ExecutionModel, RejectionReason
from trading_lab.market.calendar import MarketCalendar, NyseCalendar, TradingSession
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
    order_intents: list[object]
    order_results: list[object]
    final_cash: float


class BacktestEngine:
    def __init__(
        self,
        strategy: TradingStrategy,
        config: BacktestConfig,
        market_calendar: MarketCalendar | None = None,
        execution_model: ExecutionModel | None = None,
    ) -> None:
        self.strategy = strategy
        self.config = config
        self.market_calendar = market_calendar or NyseCalendar()
        self.execution_model = execution_model

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

    def _close_for_risk(
        self, portfolio: Portfolio, bar: MarketBar, session: TradingSession
    ) -> bool:
        risk_exit = self._risk_exit(portfolio, bar)
        if risk_exit is None:
            return False
        reason, reference = risk_exit
        trade = portfolio.close(bar, reference, reason, session)
        if trade is not None:
            self.strategy.on_trade_closed(bar)
            return True
        return False

    def _regular_session_bars(
        self, bars: list[MarketBar]
    ) -> list[tuple[MarketBar, TradingSession]]:
        accepted: list[tuple[MarketBar, TradingSession]] = []
        for bar in bars:
            session = self.market_calendar.session(bar.timestamp.date())
            if session is not None and session.contains(bar.timestamp):
                accepted.append((bar, session))
        if not accepted:
            raise ValueError("market data contains no valid regular-session bars")
        return accepted

    def run(self, bars: list[MarketBar]) -> BacktestResult:
        bars = validate_bars(bars)
        session_bars = self._regular_session_bars(bars)
        self.strategy.initialize()
        portfolio = Portfolio(self.config, self.execution_model)
        pending_signal: Signal | None = None
        pending_delay = 0

        for index, (bar, session) in enumerate(session_bars):
            closed_this_bar = False
            is_last_session_bar = (
                index == len(session_bars) - 1
                or session_bars[index + 1][1].session_date != session.session_date
            )

            # A signal is based on a completed bar. It first becomes executable
            # at the following same-session bar's open.
            entered_this_bar = False
            if pending_signal is not None:
                executable = (
                    pending_signal.timestamp.date() == bar.timestamp.date()
                )
                if executable and pending_delay > 0:
                    pending_delay -= 1
                elif executable:
                    execution_signal = replace(
                        pending_signal,
                        timestamp=bar.timestamp,
                        reference_price=bar.open,
                    )
                    entered_this_bar = portfolio.open(
                        execution_signal,
                        bar,
                        session,
                        order_reference_price=pending_signal.reference_price,
                        delayed_bars=(
                            self.execution_model.entry_delay_bars
                            if self.execution_model is not None
                            else 0
                        ),
                    )
                    if entered_this_bar:
                        self.strategy.on_signal_executed(execution_signal)
                    pending_signal = None
                elif not executable:
                    pending_signal = None
                    pending_delay = 0

            if portfolio.position is not None:
                closed_this_bar = self._close_for_risk(portfolio, bar, session)

            signal = self.strategy.on_bar(
                bar,
                portfolio.position is not None
                or closed_this_bar
                or pending_signal is not None,
            )
            if signal is not None and not is_last_session_bar:
                pending_signal = signal
                pending_delay = (
                    self.execution_model.entry_delay_bars
                    if self.execution_model is not None
                    else 0
                )
            if is_last_session_bar:
                if pending_signal is not None:
                    portfolio.reject_pending(
                        RejectionReason.SESSION_ENDED,
                        "delayed entry would execute after the regular session",
                    )
                pending_signal = None
                pending_delay = 0
                if portfolio.position is not None:
                    trade = portfolio.close(
                        bar, bar.close, ExitReason.END_OF_DAY, session
                    )
                    if trade is None:
                        raise RuntimeError(
                            "execution model rejected mandatory end-of-day liquidation"
                        )
                    self.strategy.on_trade_closed(bar)
            portfolio.mark(bar)

        metrics = calculate_metrics(
            portfolio.trades, portfolio.equity_curve, self.config.starting_capital
        )
        return BacktestResult(
            portfolio.trades,
            metrics,
            portfolio.equity_curve,
            session_bars[0][0].timestamp,
            session_bars[-1][0].timestamp,
            portfolio.executions,
            portfolio.order_intents,
            portfolio.order_results,
            portfolio.cash,
        )
