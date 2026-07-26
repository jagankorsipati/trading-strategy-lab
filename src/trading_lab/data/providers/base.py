from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from trading_lab.models import MarketBar

ONE_MINUTE = "1Min"


class HistoricalDataProviderError(RuntimeError):
    """A historical provider could not satisfy a request."""


class MissingCredentialsError(HistoricalDataProviderError):
    """Required provider credentials were not configured."""


class HistoricalDataProvider(ABC):
    """Source-agnostic interface for inclusive historical date ranges."""

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        timeframe: str = ONE_MINUTE,
    ) -> list[MarketBar]:
        """Return normalized bars for start through end, inclusive."""


def validate_request(
    symbol: str,
    start: date,
    end: date,
    timeframe: str,
) -> tuple[str, str]:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")
    if start > end:
        raise ValueError("start date must be on or before end date")
    normalized_timeframe = timeframe.strip().lower()
    if normalized_timeframe != ONE_MINUTE.lower():
        raise ValueError("only the 1Min timeframe is currently supported")
    return normalized_symbol, ONE_MINUTE
