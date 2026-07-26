from __future__ import annotations

from datetime import date
from pathlib import Path

from trading_lab.data.loader import load_csv
from trading_lab.data.providers.base import (
    HistoricalDataProvider,
    ONE_MINUTE,
    validate_request,
)
from trading_lab.models import MarketBar


class CsvHistoricalDataProvider(HistoricalDataProvider):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        timeframe: str = ONE_MINUTE,
    ) -> list[MarketBar]:
        validate_request(symbol, start, end, timeframe)
        bars = load_csv(str(self.path))
        selected = [bar for bar in bars if start <= bar.timestamp.date() <= end]
        if not selected:
            raise ValueError("CSV contains no bars in the requested date range")
        return selected
