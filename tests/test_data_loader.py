from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from trading_lab.data.loader import load_csv, validate_bars
from trading_lab.models import MarketBar

from conftest import make_bar


@pytest.mark.parametrize(
    "bars,match",
    [
        ([make_bar(30, 100, 99, 98, 100)], "invalid high"),
        ([make_bar(30, 100, 101, 100.5, 100)], "invalid low"),
        ([make_bar(30, 100, 101, 99, 100)] * 2, "duplicate"),
        (
            [make_bar(31, 100, 101, 99, 100), make_bar(30, 100, 101, 99, 100)],
            "incorrectly ordered",
        ),
    ],
)
def test_invalid_market_data_rejected(bars, match):
    with pytest.raises(ValueError, match=match):
        validate_bars(bars)


def test_naive_timestamp_rejected():
    bar = MarketBar(datetime(2025, 1, 1, 9, 30), 100, 101, 99, 100, 10)
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_bars([bar])


def test_csv_requires_explicit_timezone(tmp_path):
    path = tmp_path / "bars.csv"
    pd.DataFrame(
        [{"timestamp": "2025-01-01 09:30:00", "open": 100, "high": 101,
          "low": 99, "close": 100, "volume": 10}]
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="timezone"):
        load_csv(str(path))
