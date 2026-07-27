from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from trading_lab.data.quality import audit_historical_csv, format_quality_report
from trading_lab.market.calendar import MarketCalendar, TradingSession

EASTERN = ZoneInfo("America/New_York")


class TinyCalendar(MarketCalendar):
    def __init__(self) -> None:
        self.sessions = {
            date(2025, 1, 2): TradingSession(
                date(2025, 1, 2),
                datetime(2025, 1, 2, 9, 30, tzinfo=EASTERN),
                datetime(2025, 1, 2, 9, 33, tzinfo=EASTERN),
                False,
            ),
            date(2025, 7, 3): TradingSession(
                date(2025, 7, 3),
                datetime(2025, 7, 3, 9, 30, tzinfo=EASTERN),
                datetime(2025, 7, 3, 9, 32, tzinfo=EASTERN),
                True,
            ),
        }

    def session(self, session_date: date) -> TradingSession | None:
        return self.sessions.get(session_date)


def row(timestamp: str, **overrides):
    values = {
        "timestamp": timestamp,
        "open": 100,
        "high": 101,
        "low": 99,
        "close": 100,
        "volume": 1_000,
    }
    values.update(overrides)
    return values


def test_quality_audit_classifies_sessions_and_missing_minutes(tmp_path):
    path = tmp_path / "bars.csv"
    pd.DataFrame(
        [
            row("2025-01-02T09:00:00-05:00"),
            row("2025-01-02T09:30:00-05:00"),
            row("2025-01-02T09:32:00-05:00"),
            row("2025-01-02T09:33:00-05:00"),
            row("2025-01-04T09:30:00-05:00"),
            row("2025-01-06T09:30:00-05:00"),
            row("2025-07-03T09:30:00-04:00"),
            row("2025-07-03T09:31:00-04:00"),
        ]
    ).to_csv(path, index=False)

    report = audit_historical_csv(path, year=2025, calendar=TinyCalendar())

    assert report.total_raw_bars == 8
    assert report.regular_session_bars == 4
    assert report.premarket_bars == 1
    assert report.after_hours_bars == 1
    assert report.weekend_bars == 1
    assert report.exchange_holiday_bars == 1
    assert report.complete_sessions == 1
    assert report.sessions_with_missing_bars == 1
    assert report.absent_sessions == 0
    assert report.largest_missing_count == 1
    assert report.bars_per_session_distribution == {2: 2}


def test_quality_audit_detects_structural_anomalies(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame(
        [
            row("2025-01-02T09:31:00-05:00"),
            row("2025-01-02T09:30:00-05:00", high=98),
            row("2025-01-02T09:30:00-05:00", open=0, volume=0),
            row("2025-01-02T09:32:00-05:00", close=None, volume=-1),
        ]
    ).to_csv(path, index=False)

    report = audit_historical_csv(path, year=2025, calendar=TinyCalendar())

    assert report.duplicate_timestamp_rows == 2
    assert report.duplicate_timestamp_values == 1
    assert report.out_of_order_timestamps == 1
    assert report.malformed_ohlc_candles == 2
    assert report.missing_ohlc_rows == 1
    assert report.non_finite_numeric_rows == 1
    assert report.zero_price_rows == 1
    assert report.zero_volume_rows == 1
    assert report.negative_volume_rows == 1


def test_quality_report_is_concise_and_contains_samples(tmp_path):
    path = tmp_path / "bars.csv"
    pd.DataFrame(
        [
            row("2025-01-02T09:30:00-05:00"),
            row("2025-01-02T09:31:00-05:00"),
            row("2025-01-02T09:32:00-05:00"),
        ]
    ).to_csv(path, index=False)
    report = audit_historical_csv(path, year=2025, calendar=TinyCalendar())
    text = format_quality_report(report)
    assert "Raw bars: 3" in text
    assert "Complete sessions: 1" in text
    assert "normal_first:" in text
    assert len(text.splitlines()) < 80
