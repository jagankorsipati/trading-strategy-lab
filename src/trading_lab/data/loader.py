from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
import math
from zoneinfo import ZoneInfo

import pandas as pd

from trading_lab.models import MarketBar

EASTERN = ZoneInfo("America/New_York")
REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def load_csv(path: str) -> list[MarketBar]:
    frame = pd.read_csv(path)
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    try:
        parsed = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError("timestamps must be valid and timezone-aware") from exc
    # pandas treats naive values as UTC when utc=True, so reject them explicitly.
    raw = frame["timestamp"].astype(str)
    has_timezone = raw.str.contains(r"(?:Z|[+-]\d\d:?\d\d)$", regex=True)
    if not bool(has_timezone.all()):
        raise ValueError("all timestamps must include a timezone or UTC offset")
    frame = frame.copy()
    frame["timestamp"] = parsed.dt.tz_convert(EASTERN)
    bars = [
        MarketBar(
            timestamp=row.timestamp.to_pydatetime(),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )
        for row in frame.itertuples(index=False)
    ]
    return validate_bars(bars)


def validate_bars(bars: Iterable[MarketBar]) -> list[MarketBar]:
    result = list(bars)
    if not result:
        raise ValueError("market data cannot be empty")
    previous = None
    normalized: list[MarketBar] = []
    for bar in result:
        if bar.timestamp.tzinfo is None or bar.timestamp.utcoffset() is None:
            raise ValueError("market timestamps must be timezone-aware")
        bar = replace(bar, timestamp=bar.timestamp.astimezone(EASTERN))
        values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("market data contains missing or non-finite values")
        if min(bar.open, bar.high, bar.low, bar.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if bar.volume < 0:
            raise ValueError("volume cannot be negative")
        if bar.high < max(bar.open, bar.low, bar.close):
            raise ValueError(f"malformed candle at {bar.timestamp}: invalid high")
        if bar.low > min(bar.open, bar.high, bar.close):
            raise ValueError(f"malformed candle at {bar.timestamp}: invalid low")
        if previous is not None and bar.timestamp <= previous:
            message = "duplicate" if bar.timestamp == previous else "incorrectly ordered"
            raise ValueError(f"{message} timestamp: {bar.timestamp}")
        previous = bar.timestamp
        normalized.append(bar)
    return normalized
