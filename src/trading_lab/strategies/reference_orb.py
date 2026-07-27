from __future__ import annotations

from datetime import date, datetime, timedelta

from trading_lab.config.settings import ReferenceORBConfig
from trading_lab.data.aggregation import aggregate_complete_candle
from trading_lab.models import Direction, MarketBar, RiskSizing, Signal
from trading_lab.strategies.base import TradingStrategy


class ReferenceORBStrategy(TradingStrategy):
    """Conservative interpretation of the public five-minute ORB notebook."""

    def __init__(self, config: ReferenceORBConfig | None = None) -> None:
        self.config = config or ReferenceORBConfig()
        self.initialize()

    def initialize(self) -> None:
        self.session_date: date | None = None
        self._opening_minutes: list[MarketBar] = []
        self.setup_evaluated = False
        self.trades_today = 0
        self.first_candle: MarketBar | None = None

    def _new_session(self, session_date: date) -> None:
        self.session_date = session_date
        self._opening_minutes = []
        self.setup_evaluated = False
        self.trades_today = 0
        self.first_candle = None

    def _expected_timestamp(self, bar: MarketBar) -> datetime:
        opening = datetime.combine(
            bar.timestamp.date(),
            self.config.market_open,
            tzinfo=bar.timestamp.tzinfo,
        )
        return opening + timedelta(minutes=len(self._opening_minutes))

    def on_bar(self, bar: MarketBar, has_open_position: bool) -> Signal | None:
        if bar.timestamp.date() != self.session_date:
            self._new_session(bar.timestamp.date())
        if self.setup_evaluated:
            return None

        expected = self._expected_timestamp(bar)
        if bar.timestamp != expected:
            # The reference setup requires a complete first five-minute candle.
            if not self._opening_minutes:
                return None
            self.setup_evaluated = True
            return None
        self._opening_minutes.append(bar)
        if len(self._opening_minutes) < self.config.candle_minutes:
            return None

        self.setup_evaluated = True
        candle = aggregate_complete_candle(
            self._opening_minutes,
            minutes=self.config.candle_minutes,
        )
        self.first_candle = candle
        if round(candle.open, 2) == round(candle.close, 2):
            return None
        direction = (
            Direction.LONG if candle.close > candle.open else Direction.SHORT
        )
        stop = candle.low if direction == Direction.LONG else candle.high
        return Signal(
            symbol=self.config.symbol,
            timestamp=bar.timestamp,
            direction=direction,
            reference_price=bar.close,
            stop_price=stop,
            reward_risk_multiple=self.config.reward_risk_multiple,
            risk_sizing=RiskSizing(
                account_value=self.config.account_value,
                risk_fraction=self.config.risk_fraction,
                max_leverage=self.config.max_leverage,
                minimum_risk_per_share=self.config.minimum_risk_per_share,
                commission_per_share=self.config.commission_per_share,
            ),
        )

    def on_signal_executed(self, signal: Signal) -> None:
        self.trades_today += 1
