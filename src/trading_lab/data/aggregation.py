from __future__ import annotations

from datetime import timedelta

from trading_lab.models import MarketBar


def aggregate_complete_candle(
    bars: list[MarketBar],
    *,
    minutes: int = 5,
) -> MarketBar:
    """Aggregate one complete, consecutive minute bucket."""
    if len(bars) != minutes:
        raise ValueError(f"expected {minutes} one-minute bars")
    first = bars[0]
    for index, bar in enumerate(bars):
        if bar.timestamp != first.timestamp + timedelta(minutes=index):
            raise ValueError("minute bars must be consecutive")
        if bar.timestamp.date() != first.timestamp.date():
            raise ValueError("minute bars cannot cross a session date")
    return MarketBar(
        timestamp=first.timestamp,
        open=first.open,
        high=max(bar.high for bar in bars),
        low=min(bar.low for bar in bars),
        close=bars[-1].close,
        volume=sum(bar.volume for bar in bars),
    )
