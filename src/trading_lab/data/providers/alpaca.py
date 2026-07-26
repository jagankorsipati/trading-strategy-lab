from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
import os
from typing import Any, Callable
from zoneinfo import ZoneInfo

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from trading_lab.data.cache import HistoricalDataCache
from trading_lab.data.loader import validate_bars
from trading_lab.data.providers.base import (
    HistoricalDataProvider,
    HistoricalDataProviderError,
    MissingCredentialsError,
    ONE_MINUTE,
    validate_request,
)
from trading_lab.models import MarketBar

EASTERN = ZoneInfo("America/New_York")
ClientFactory = Callable[[str, str], Any]


class AlpacaHistoricalDataProvider(HistoricalDataProvider):
    def __init__(
        self,
        client: Any,
        cache: HistoricalDataCache | None = None,
    ) -> None:
        self._client = client
        self.cache = cache

    @classmethod
    def from_env(
        cls,
        *,
        cache: HistoricalDataCache | None = None,
        environ: Mapping[str, str] | None = None,
        client_factory: ClientFactory = StockHistoricalDataClient,
    ) -> AlpacaHistoricalDataProvider:
        values = os.environ if environ is None else environ
        api_key = values.get("ALPACA_API_KEY", "").strip()
        secret_key = values.get("ALPACA_SECRET_KEY", "").strip()
        missing = [
            name
            for name, value in (
                ("ALPACA_API_KEY", api_key),
                ("ALPACA_SECRET_KEY", secret_key),
            )
            if not value
        ]
        if missing:
            raise MissingCredentialsError(
                f"missing Alpaca credentials: {', '.join(missing)}"
            )
        return cls(client_factory(api_key, secret_key), cache)

    @staticmethod
    def _convert_bar(bar: Any) -> MarketBar:
        timestamp = bar.timestamp
        if not isinstance(timestamp, datetime):
            raise HistoricalDataProviderError("Alpaca returned an invalid timestamp")
        return MarketBar(
            timestamp=timestamp,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=float(bar.volume),
        )

    def get_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        timeframe: str = ONE_MINUTE,
    ) -> list[MarketBar]:
        symbol, timeframe = validate_request(symbol, start, end, timeframe)
        if self.cache is not None:
            cached = self.cache.read(symbol, timeframe, start, end)
            if cached is not None:
                return cached

        start_at = datetime.combine(start, time.min, tzinfo=EASTERN)
        end_at = datetime.combine(end + timedelta(days=1), time.min, tzinfo=EASTERN)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=start_at,
            end=end_at,
        )
        try:
            response = self._client.get_stock_bars(request)
            alpaca_bars = response[symbol]
            converted = sorted(
                (self._convert_bar(bar) for bar in alpaca_bars),
                key=lambda bar: bar.timestamp,
            )
            bars = validate_bars(converted)
        except HistoricalDataProviderError:
            raise
        except Exception as exc:
            raise HistoricalDataProviderError(
                f"Alpaca historical data request failed for {symbol}"
            ) from exc

        if self.cache is not None:
            self.cache.write(symbol, timeframe, start, end, bars)
        return bars
