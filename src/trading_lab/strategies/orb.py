from __future__ import annotations

from datetime import date

from trading_lab.config.settings import ORBConfig
from trading_lab.models import (
    BreakoutConfirmation,
    Direction,
    MarketBar,
    Signal,
    TradeDirection,
)
from trading_lab.strategies.base import TradingStrategy


class ORBStrategy(TradingStrategy):
    def __init__(self, config: ORBConfig) -> None:
        self.config = config
        self.initialize()

    def initialize(self) -> None:
        self.session_date: date | None = None
        self.opening_range_high: float | None = None
        self.opening_range_low: float | None = None
        self.trades_today = 0

    def _new_session(self, session_date: date) -> None:
        self.session_date = session_date
        self.opening_range_high = None
        self.opening_range_low = None
        self.trades_today = 0

    def on_bar(self, bar: MarketBar, has_open_position: bool) -> Signal | None:
        session_date = bar.timestamp.date()
        if session_date != self.session_date:
            self._new_session(session_date)

        current_time = bar.timestamp.time().replace(tzinfo=None)
        if self.config.market_open <= current_time < self.config.range_end:
            self.opening_range_high = (
                bar.high
                if self.opening_range_high is None
                else max(self.opening_range_high, bar.high)
            )
            self.opening_range_low = (
                bar.low
                if self.opening_range_low is None
                else min(self.opening_range_low, bar.low)
            )
            return None

        if (
            current_time < self.config.range_end
            or self.opening_range_high is None
            or has_open_position
            or self.trades_today >= self.config.maximum_trades_per_day
        ):
            return None

        long_value = (
            bar.close
            if self.config.confirmation == BreakoutConfirmation.CLOSE
            else bar.high
        )
        short_value = (
            bar.close
            if self.config.confirmation == BreakoutConfirmation.CLOSE
            else bar.low
        )
        direction = None
        if (
            self.config.trade_direction in (TradeDirection.LONG, TradeDirection.BOTH)
            and long_value > self.opening_range_high
        ):
            direction = Direction.LONG
        elif (
            self.config.trade_direction in (TradeDirection.SHORT, TradeDirection.BOTH)
            and short_value < self.opening_range_low
        ):
            direction = Direction.SHORT
        if direction is None:
            return None
        return Signal(self.config.symbol, bar.timestamp, direction, bar.close)

    def on_signal_executed(self, signal: Signal) -> None:
        self.trades_today += 1
