from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from trading_lab.data.loader import REQUIRED_COLUMNS
from trading_lab.market.calendar import MarketCalendar, NyseCalendar, TradingSession

EASTERN = ZoneInfo("America/New_York")
OHLC = ("open", "high", "low", "close")
NUMERIC = (*OHLC, "volume")


@dataclass(frozen=True)
class SessionCoverage:
    session_date: date
    expected_minutes: int
    observed_minutes: int
    missing_minutes: int
    is_early_close: bool


@dataclass(frozen=True)
class DataQualityReport:
    path: Path
    year: int
    total_raw_bars: int
    earliest_timestamp: datetime | None
    latest_timestamp: datetime | None
    unique_calendar_dates: int
    expected_sessions: int
    represented_sessions: int
    duplicate_timestamp_rows: int
    duplicate_timestamp_values: int
    out_of_order_timestamps: int
    invalid_timestamps: int
    malformed_ohlc_candles: int
    non_finite_numeric_rows: int
    non_numeric_rows: int
    missing_ohlc_rows: int
    zero_price_rows: int
    negative_price_rows: int
    zero_volume_rows: int
    negative_volume_rows: int
    weekend_bars: int
    exchange_holiday_bars: int
    premarket_bars: int
    after_hours_bars: int
    regular_session_bars: int
    session_coverage: tuple[SessionCoverage, ...]
    samples: dict[str, tuple[dict[str, Any], ...]]
    winter_sample: datetime | None
    summer_sample: datetime | None

    @property
    def complete_sessions(self) -> int:
        return sum(item.missing_minutes == 0 for item in self.session_coverage)

    @property
    def sessions_with_missing_bars(self) -> int:
        return sum(
            0 < item.missing_minutes < item.expected_minutes
            for item in self.session_coverage
        )

    @property
    def absent_sessions(self) -> int:
        return sum(
            item.missing_minutes == item.expected_minutes
            for item in self.session_coverage
        )

    @property
    def largest_missing_count(self) -> int:
        return max((item.missing_minutes for item in self.session_coverage), default=0)

    @property
    def bars_per_session_distribution(self) -> dict[int, int]:
        return dict(
            sorted(Counter(item.observed_minutes for item in self.session_coverage).items())
        )


def _calendar_sessions(
    calendar: MarketCalendar, year: int
) -> dict[date, TradingSession]:
    sessions: dict[date, TradingSession] = {}
    current = date(year, 1, 1)
    last = date(year, 12, 31)
    while current <= last:
        session = calendar.session(current)
        if session is not None:
            sessions[current] = session
        current += timedelta(days=1)
    return sessions


def _sample_rows(frame: pd.DataFrame, count: int = 3) -> tuple[dict[str, Any], ...]:
    records = []
    for row in frame.head(count).itertuples(index=False):
        records.append(
            {
                "timestamp": row.timestamp.isoformat(),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
            }
        )
    return tuple(records)


def audit_historical_csv(
    path: str | Path,
    *,
    year: int,
    calendar: MarketCalendar | None = None,
) -> DataQualityReport:
    source = Path(path)
    frame = pd.read_csv(source)
    missing_columns = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing_columns:
        raise ValueError(f"missing required columns: {sorted(missing_columns)}")

    raw_count = len(frame)
    parsed_utc = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    invalid_timestamp_mask = parsed_utc.isna()
    valid_timestamp_mask = ~invalid_timestamp_mask
    eastern = parsed_utc.dt.tz_convert(EASTERN)

    duplicate_mask = parsed_utc.duplicated(keep=False) & valid_timestamp_mask
    duplicate_values = int(parsed_utc[duplicate_mask].nunique())
    valid_order = parsed_utc[valid_timestamp_mask]
    out_of_order = int((valid_order.diff().dropna() < pd.Timedelta(0)).sum())

    numeric = frame.loc[:, NUMERIC].apply(pd.to_numeric, errors="coerce")
    missing_ohlc = int(frame.loc[:, OHLC].isna().any(axis=1).sum())
    non_numeric = int(
        (
            numeric.isna()
            & ~frame.loc[:, NUMERIC].isna()
        ).any(axis=1).sum()
    )
    finite = np.isfinite(numeric.to_numpy(dtype=float))
    non_finite = int((~finite).any(axis=1).sum())
    prices = numeric.loc[:, OHLC]
    zero_prices = int((prices == 0).any(axis=1).sum())
    negative_prices = int((prices < 0).any(axis=1).sum())
    zero_volume = int((numeric["volume"] == 0).sum())
    negative_volume = int((numeric["volume"] < 0).sum())

    finite_ohlc = np.isfinite(prices.to_numpy(dtype=float)).all(axis=1)
    malformed = finite_ohlc & (
        (prices["high"] < prices.max(axis=1))
        | (prices["low"] > prices.min(axis=1))
    )

    market_calendar = calendar or NyseCalendar()
    sessions = _calendar_sessions(market_calendar, year)
    regular_mask = pd.Series(False, index=frame.index)
    premarket_mask = pd.Series(False, index=frame.index)
    after_hours_mask = pd.Series(False, index=frame.index)
    weekend_mask = pd.Series(False, index=frame.index)
    holiday_mask = pd.Series(False, index=frame.index)

    normalized = pd.DataFrame(
        {
            "timestamp": eastern,
            "open": numeric["open"],
            "high": numeric["high"],
            "low": numeric["low"],
            "close": numeric["close"],
            "volume": numeric["volume"],
        }
    )
    normalized["_date"] = normalized["timestamp"].dt.date

    for index, timestamp in eastern[valid_timestamp_mask].items():
        session_date = timestamp.date()
        session = sessions.get(session_date)
        if session is None:
            if timestamp.weekday() >= 5:
                weekend_mask.at[index] = True
            else:
                holiday_mask.at[index] = True
        elif timestamp < session.market_open:
            premarket_mask.at[index] = True
        elif timestamp >= session.market_close:
            after_hours_mask.at[index] = True
        else:
            regular_mask.at[index] = True

    regular = normalized[regular_mask].copy()
    observed_by_date = {
        session_date: set(group["timestamp"].tolist())
        for session_date, group in regular.groupby("_date")
    }
    coverage: list[SessionCoverage] = []
    for session_date, session in sessions.items():
        expected = pd.date_range(
            session.market_open,
            session.market_close,
            freq="1min",
            inclusive="left",
        )
        observed = observed_by_date.get(session_date, set())
        observed_expected = sum(timestamp in observed for timestamp in expected)
        coverage.append(
            SessionCoverage(
                session_date=session_date,
                expected_minutes=len(expected),
                observed_minutes=observed_expected,
                missing_minutes=len(expected) - observed_expected,
                is_early_close=session.is_early_close,
            )
        )

    represented_dates = set(regular["_date"])
    normal_candidates = [
        item.session_date
        for item in coverage
        if not item.is_early_close and item.observed_minutes > 0
    ]
    normal_date = normal_candidates[0] if normal_candidates else None
    early_date = date(year, 7, 3)

    def session_samples(
        session_date: date | None,
    ) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        if session_date is None:
            return (), ()
        rows = regular[regular["_date"] == session_date].drop(columns="_date")
        return _sample_rows(rows), _sample_rows(rows.tail(3))

    normal_first, normal_last = session_samples(normal_date)
    early_first, early_last = session_samples(early_date)
    winter_rows = regular[regular["timestamp"].dt.month <= 2]
    summer_rows = regular[
        (regular["timestamp"].dt.month >= 6)
        & (regular["timestamp"].dt.month <= 8)
    ]

    return DataQualityReport(
        path=source,
        year=year,
        total_raw_bars=raw_count,
        earliest_timestamp=(
            eastern[valid_timestamp_mask].min().to_pydatetime()
            if valid_timestamp_mask.any()
            else None
        ),
        latest_timestamp=(
            eastern[valid_timestamp_mask].max().to_pydatetime()
            if valid_timestamp_mask.any()
            else None
        ),
        unique_calendar_dates=int(eastern[valid_timestamp_mask].dt.date.nunique()),
        expected_sessions=len(sessions),
        represented_sessions=len(represented_dates),
        duplicate_timestamp_rows=int(duplicate_mask.sum()),
        duplicate_timestamp_values=duplicate_values,
        out_of_order_timestamps=out_of_order,
        invalid_timestamps=int(invalid_timestamp_mask.sum()),
        malformed_ohlc_candles=int(malformed.sum()),
        non_finite_numeric_rows=non_finite,
        non_numeric_rows=non_numeric,
        missing_ohlc_rows=missing_ohlc,
        zero_price_rows=zero_prices,
        negative_price_rows=negative_prices,
        zero_volume_rows=zero_volume,
        negative_volume_rows=negative_volume,
        weekend_bars=int(weekend_mask.sum()),
        exchange_holiday_bars=int(holiday_mask.sum()),
        premarket_bars=int(premarket_mask.sum()),
        after_hours_bars=int(after_hours_mask.sum()),
        regular_session_bars=int(regular_mask.sum()),
        session_coverage=tuple(coverage),
        samples={
            "normal_first": normal_first,
            "normal_last": normal_last,
            "early_close_first": early_first,
            "early_close_last": early_last,
        },
        winter_sample=(
            winter_rows.iloc[0]["timestamp"].to_pydatetime()
            if not winter_rows.empty
            else None
        ),
        summer_sample=(
            summer_rows.iloc[0]["timestamp"].to_pydatetime()
            if not summer_rows.empty
            else None
        ),
    )


def format_quality_report(report: DataQualityReport) -> str:
    missing = [
        item
        for item in report.session_coverage
        if 0 < item.missing_minutes < item.expected_minutes
    ]
    absent = [
        item for item in report.session_coverage
        if item.missing_minutes == item.expected_minutes
    ]
    missing_sample = ", ".join(
        f"{item.session_date} ({item.missing_minutes})" for item in missing[:10]
    ) or "none"
    absent_sample = ", ".join(str(item.session_date) for item in absent[:10]) or "none"

    lines = [
        f"Historical Data Quality Audit: {report.path}",
        "",
        f"Raw bars: {report.total_raw_bars:,}",
        f"Earliest timestamp: {report.earliest_timestamp}",
        f"Latest timestamp: {report.latest_timestamp}",
        f"Unique calendar dates: {report.unique_calendar_dates}",
        f"Expected exchange sessions: {report.expected_sessions}",
        f"Represented exchange sessions: {report.represented_sessions}",
        f"Regular-session bars: {report.regular_session_bars:,}",
        f"Premarket bars: {report.premarket_bars:,}",
        f"After-hours bars: {report.after_hours_bars:,}",
        f"Weekend bars: {report.weekend_bars:,}",
        f"Exchange-holiday bars: {report.exchange_holiday_bars:,}",
        "",
        f"Duplicate timestamp rows: {report.duplicate_timestamp_rows}",
        f"Duplicate timestamp values: {report.duplicate_timestamp_values}",
        f"Out-of-order timestamps: {report.out_of_order_timestamps}",
        f"Invalid timestamps: {report.invalid_timestamps}",
        f"Malformed OHLC candles: {report.malformed_ohlc_candles}",
        f"Missing OHLC rows: {report.missing_ohlc_rows}",
        f"Non-numeric rows: {report.non_numeric_rows}",
        f"Non-finite numeric rows: {report.non_finite_numeric_rows}",
        f"Zero-price rows: {report.zero_price_rows}",
        f"Negative-price rows: {report.negative_price_rows}",
        f"Zero-volume rows: {report.zero_volume_rows}",
        f"Negative-volume rows: {report.negative_volume_rows}",
        "",
        f"Bars/session distribution: {report.bars_per_session_distribution}",
        f"Complete sessions: {report.complete_sessions}",
        f"Sessions with missing minutes: {report.sessions_with_missing_bars}",
        f"Completely absent sessions: {report.absent_sessions}",
        f"Largest missing count: {report.largest_missing_count}",
        f"Missing-session sample date (missing count): {missing_sample}",
        f"Absent-session sample: {absent_sample}",
        "",
        f"Winter Eastern sample: {report.winter_sample}",
        f"Summer Eastern sample: {report.summer_sample}",
    ]
    for label, rows in report.samples.items():
        lines.extend(["", f"{label}:"])
        lines.extend(
            f"  {row['timestamp']} O={row['open']} H={row['high']} "
            f"L={row['low']} C={row['close']} V={row['volume']}"
            for row in rows
        )
    return "\n".join(lines)
