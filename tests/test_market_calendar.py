from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.config.settings import BacktestConfig, ORBConfig
from trading_lab.market.calendar import NyseCalendar
from trading_lab.models import ExitReason, MarketBar
from trading_lab.strategies.orb import ORBStrategy

EASTERN = ZoneInfo("America/New_York")


def bar(
    session_date: date,
    hour: int,
    minute: int,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> MarketBar:
    return MarketBar(
        datetime(
            session_date.year,
            session_date.month,
            session_date.day,
            hour,
            minute,
            tzinfo=EASTERN,
        ),
        open_,
        high,
        low,
        close,
        1_000,
    )


def run(bars: list[MarketBar]):
    return BacktestEngine(
        ORBStrategy(ORBConfig()),
        BacktestConfig(position_size=10),
        NyseCalendar(),
    ).run(bars)


def session_bars(
    session_date: date,
    final_hour: int,
    final_minute: int,
) -> list[MarketBar]:
    return [
        bar(session_date, 9, 30, 100, 101, 99, 100),
        bar(session_date, 9, 35, 100, 102, 99.5, 101),
        bar(session_date, 9, 40, 101, 101.5, 98, 100),
        bar(session_date, 9, 45, 102, 103, 101, 102.5),
        bar(session_date, 9, 50, 102.5, 103, 102.2, 102.5),
        bar(
            session_date,
            final_hour,
            final_minute,
            102.5,
            103,
            102.2,
            102.5,
        ),
    ]


def test_normal_nyse_session_is_930_to_1600_eastern():
    session = NyseCalendar().session(date(2025, 7, 2))
    assert session is not None
    assert (session.market_open.hour, session.market_open.minute) == (9, 30)
    assert (session.market_close.hour, session.market_close.minute) == (16, 0)
    assert session.market_open.tzinfo == EASTERN
    assert session.market_close.tzinfo == EASTERN
    assert not session.is_early_close


@pytest.mark.parametrize(
    "closed_date",
    [
        date(2025, 7, 5),  # Saturday
        date(2025, 7, 4),  # Independence Day
    ],
)
def test_weekends_and_holidays_are_not_sessions(closed_date):
    calendar = NyseCalendar()
    assert not calendar.is_session(closed_date)
    assert calendar.session_bounds(closed_date) is None


def test_known_early_close_is_1300_eastern():
    session = NyseCalendar().session(date(2025, 7, 3))
    assert session is not None
    assert (session.market_open.hour, session.market_open.minute) == (9, 30)
    assert (session.market_close.hour, session.market_close.minute) == (13, 0)
    assert session.is_early_close


def test_position_liquidates_on_last_valid_early_close_bar():
    result = run(session_bars(date(2025, 7, 3), 12, 59))
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.END_OF_DAY
    assert (trade.exit_timestamp.hour, trade.exit_timestamp.minute) == (12, 59)
    assert trade.exit_price == 102.5


def test_after_hours_early_close_candle_cannot_affect_trade():
    bars = session_bars(date(2025, 7, 3), 12, 59)
    bars.append(bar(date(2025, 7, 3), 13, 0, 50, 200, 40, 50))
    result = run(bars)
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.END_OF_DAY
    assert trade.exit_timestamp.hour == 12
    assert trade.exit_price == 102.5
    assert all(point[0].hour < 13 for point in result.equity_curve)


def test_calendar_open_remains_930_across_dst():
    calendar = NyseCalendar()
    winter = calendar.session(date(2025, 1, 2))
    summer = calendar.session(date(2025, 7, 2))
    assert winter is not None and summer is not None
    assert winter.market_open.hour == summer.market_open.hour == 9
    assert winter.market_open.utcoffset().total_seconds() == -5 * 3600
    assert summer.market_open.utcoffset().total_seconds() == -4 * 3600


def test_regular_session_eod_behavior_remains_unchanged():
    result = run(session_bars(date(2025, 7, 2), 15, 59))
    trade = result.trades[0]
    assert trade.exit_reason == ExitReason.END_OF_DAY
    assert (trade.exit_timestamp.hour, trade.exit_timestamp.minute) == (15, 59)


def test_sessions_around_holiday_process_without_holiday_bars():
    early_close = session_bars(date(2025, 7, 3), 12, 59)
    holiday = [
        bar(date(2025, 7, 4), 9, 30, 500, 600, 400, 550),
        bar(date(2025, 7, 4), 9, 45, 550, 700, 300, 650),
    ]
    following_session = session_bars(date(2025, 7, 7), 15, 59)
    result = run(early_close + holiday + following_session)
    assert len(result.trades) == 2
    assert {trade.entry_timestamp.date() for trade in result.trades} == {
        date(2025, 7, 3),
        date(2025, 7, 7),
    }
    assert date(2025, 7, 4) not in {
        timestamp.date() for timestamp, _ in result.equity_curve
    }


def test_out_of_session_bars_cannot_create_breakout_or_execution():
    session_date = date(2025, 7, 2)
    bars = [
        bar(session_date, 9, 0, 100, 1_000, 1, 900),
        *session_bars(session_date, 15, 59),
        bar(session_date, 16, 0, 50, 2_000, 1, 1_500),
    ]
    result = run(bars)
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 102.5
    assert all(
        9 <= execution.timestamp.hour < 16 for execution in result.executions
    )


def test_all_out_of_session_data_is_rejected():
    session_date = date(2025, 7, 4)
    with pytest.raises(ValueError, match="no valid regular-session bars"):
        run([bar(session_date, 9, 30, 100, 101, 99, 100)])
