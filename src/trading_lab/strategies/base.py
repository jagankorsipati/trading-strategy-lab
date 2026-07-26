from __future__ import annotations

from abc import ABC, abstractmethod

from trading_lab.models import MarketBar, Signal


class TradingStrategy(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Reset all strategy state."""

    @abstractmethod
    def on_bar(self, bar: MarketBar, has_open_position: bool) -> Signal | None:
        """Observe one completed bar and optionally emit a signal."""

    def on_trade_closed(self, bar: MarketBar) -> None:
        """Receive notification after a position closes."""

    def on_signal_executed(self, signal: Signal) -> None:
        """Receive notification after a signal becomes an actual position."""
