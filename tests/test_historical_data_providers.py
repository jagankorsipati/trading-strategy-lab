from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from trading_lab.data.cache import CACHE_COLUMNS, HistoricalDataCache
from trading_lab.data.providers.alpaca import AlpacaHistoricalDataProvider
from trading_lab.data.providers.base import (
    HistoricalDataProviderError,
    MissingCredentialsError,
)
from trading_lab.data.providers.csv import CsvHistoricalDataProvider
from trading_lab.models import MarketBar

UTC = ZoneInfo("UTC")
EASTERN = ZoneInfo("America/New_York")
START = date(2025, 1, 2)
END = date(2025, 1, 3)


@dataclass
class FakeAlpacaBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class FakeClient:
    def __init__(self, bars=None, error: Exception | None = None) -> None:
        self.bars = [] if bars is None else bars
        self.error = error
        self.calls = 0
        self.request = None

    def get_stock_bars(self, request):
        self.calls += 1
        self.request = request
        if self.error is not None:
            raise self.error
        return {"QQQ": self.bars}


def fake_bar(
    minute: int,
    *,
    open_: float = 100,
    high: float = 101,
    low: float = 99,
    close: float = 100,
) -> FakeAlpacaBar:
    return FakeAlpacaBar(
        datetime(2025, 1, 2, 14, minute, tzinfo=UTC),
        open_,
        high,
        low,
        close,
        1_000,
    )


def market_bars() -> list[MarketBar]:
    return [
        MarketBar(datetime(2025, 1, 2, 9, 30, tzinfo=EASTERN), 100, 101, 99, 100, 1_000),
        MarketBar(datetime(2025, 1, 3, 9, 30, tzinfo=EASTERN), 101, 102, 100, 101, 2_000),
    ]


def test_alpaca_bar_converts_to_market_bar_and_normalizes_utc():
    provider = AlpacaHistoricalDataProvider(FakeClient([fake_bar(30)]))
    bars = provider.get_bars("qqq", START, START)
    assert bars == [
        MarketBar(
            datetime(2025, 1, 2, 9, 30, tzinfo=EASTERN),
            100,
            101,
            99,
            100,
            1_000,
        )
    ]


def test_alpaca_results_are_sorted_chronologically():
    provider = AlpacaHistoricalDataProvider(
        FakeClient([fake_bar(32), fake_bar(30), fake_bar(31)])
    )
    bars = provider.get_bars("QQQ", START, START)
    assert [bar.timestamp.minute for bar in bars] == [30, 31, 32]


def test_duplicate_alpaca_bars_are_rejected():
    provider = AlpacaHistoricalDataProvider(
        FakeClient([fake_bar(30), fake_bar(30)])
    )
    with pytest.raises(HistoricalDataProviderError) as error:
        provider.get_bars("QQQ", START, START)
    assert isinstance(error.value.__cause__, ValueError)
    assert "duplicate timestamp" in str(error.value.__cause__)


def test_malformed_alpaca_bar_is_rejected():
    provider = AlpacaHistoricalDataProvider(
        FakeClient([fake_bar(30, high=98)])
    )
    with pytest.raises(HistoricalDataProviderError) as error:
        provider.get_bars("QQQ", START, START)
    assert isinstance(error.value.__cause__, ValueError)
    assert "invalid high" in str(error.value.__cause__)


def test_credentials_are_read_from_environment_without_persistence():
    captured = {}

    def factory(api_key, secret_key):
        captured["api_key"] = api_key
        captured["secret_key"] = secret_key
        return FakeClient()

    provider = AlpacaHistoricalDataProvider.from_env(
        environ={
            "ALPACA_API_KEY": "test-api-key",
            "ALPACA_SECRET_KEY": "test-secret-key",
        },
        client_factory=factory,
    )
    assert isinstance(provider, AlpacaHistoricalDataProvider)
    assert captured == {
        "api_key": "test-api-key",
        "secret_key": "test-secret-key",
    }
    assert not hasattr(provider, "api_key")
    assert not hasattr(provider, "secret_key")


def test_missing_credentials_produce_useful_error():
    with pytest.raises(MissingCredentialsError) as error:
        AlpacaHistoricalDataProvider.from_env(environ={})
    assert "ALPACA_API_KEY" in str(error.value)
    assert "ALPACA_SECRET_KEY" in str(error.value)


def test_provider_errors_are_surfaced_without_credentials():
    provider = AlpacaHistoricalDataProvider(
        FakeClient(error=RuntimeError("request rejected for secret-value"))
    )
    with pytest.raises(HistoricalDataProviderError) as error:
        provider.get_bars("QQQ", START, START)
    assert str(error.value) == "Alpaca historical data request failed for QQQ"
    assert "secret-value" not in str(error.value)


def test_cache_writing_contains_market_data_only(tmp_path):
    cache = HistoricalDataCache(tmp_path)
    path = cache.write("QQQ", "1Min", START, END, market_bars())
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == list(CACHE_COLUMNS)
    content = path.read_text(encoding="utf-8")
    assert "api_key" not in content.lower()
    assert "secret" not in content.lower()


def test_cache_reading_reuses_covering_range(tmp_path):
    cache = HistoricalDataCache(tmp_path)
    cache.write("QQQ", "1Min", START, END, market_bars())
    client = FakeClient(error=AssertionError("cache miss"))
    provider = AlpacaHistoricalDataProvider(client, cache)
    bars = provider.get_bars("QQQ", START, START)
    assert len(bars) == 1
    assert bars[0].timestamp.date() == START
    assert client.calls == 0


def test_alpaca_download_is_written_to_cache(tmp_path):
    cache = HistoricalDataCache(tmp_path)
    client = FakeClient([fake_bar(30)])
    provider = AlpacaHistoricalDataProvider(client, cache)
    bars = provider.get_bars("QQQ", START, START)
    path = cache.path_for("QQQ", "1Min", START, START)
    assert len(bars) == 1
    assert path.exists()
    assert cache.read("QQQ", "1Min", START, START) == bars


def test_existing_csv_provider_workflow(tmp_path):
    cache = HistoricalDataCache(tmp_path)
    path = cache.write("QQQ", "1Min", START, END, market_bars())
    provider = CsvHistoricalDataProvider(path)
    bars = provider.get_bars("QQQ", END, END, "1Min")
    assert len(bars) == 1
    assert bars[0].timestamp.date() == END


def test_only_one_minute_timeframe_is_currently_supported():
    provider = AlpacaHistoricalDataProvider(FakeClient())
    with pytest.raises(ValueError, match="only the 1Min"):
        provider.get_bars("QQQ", START, END, "5Min")
