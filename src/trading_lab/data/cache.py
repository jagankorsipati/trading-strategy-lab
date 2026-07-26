from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from trading_lab.data.loader import load_csv, validate_bars
from trading_lab.models import MarketBar

CACHE_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


class HistoricalDataCache:
    """CSV cache keyed by symbol, timeframe, and inclusive date coverage."""

    def __init__(self, root: str | Path = "data/historical") -> None:
        self.root = Path(root)

    def _directory(self, symbol: str, timeframe: str) -> Path:
        return self.root / symbol.upper() / timeframe.lower()

    def path_for(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> Path:
        return self._directory(symbol, timeframe) / f"{start}_{end}.csv"

    def find_covering(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> Path | None:
        directory = self._directory(symbol, timeframe)
        if not directory.exists():
            return None
        for path in sorted(directory.glob("*.csv")):
            try:
                cached_start_text, cached_end_text = path.stem.split("_", maxsplit=1)
                cached_start = date.fromisoformat(cached_start_text)
                cached_end = date.fromisoformat(cached_end_text)
            except ValueError:
                continue
            if cached_start <= start and cached_end >= end:
                return path
        return None

    def read(
        self, symbol: str, timeframe: str, start: date, end: date
    ) -> list[MarketBar] | None:
        path = self.find_covering(symbol, timeframe, start, end)
        if path is None:
            return None
        bars = load_csv(str(path))
        selected = [bar for bar in bars if start <= bar.timestamp.date() <= end]
        return validate_bars(selected) if selected else None

    def write(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
        bars: list[MarketBar],
    ) -> Path:
        normalized = validate_bars(bars)
        path = self.path_for(symbol, timeframe, start, end)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CACHE_COLUMNS)
            writer.writeheader()
            for bar in normalized:
                writer.writerow(
                    {
                        "timestamp": bar.timestamp.isoformat(),
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                    }
                )
        return path
