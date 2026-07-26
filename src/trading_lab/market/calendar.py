from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class TradingSession:
    session_date: date
    market_open: datetime
    market_close: datetime
    is_early_close: bool

    def contains(self, timestamp: datetime) -> bool:
        """Return whether a bar-start timestamp is inside regular hours."""
        return self.market_open <= timestamp < self.market_close


class MarketCalendar(ABC):
    """Replaceable source of exchange trading-session boundaries."""

    @abstractmethod
    def session(self, session_date: date) -> TradingSession | None:
        """Return the session or None when the exchange is closed."""

    def is_session(self, session_date: date) -> bool:
        return self.session(session_date) is not None

    def session_open(self, session_date: date) -> datetime | None:
        value = self.session(session_date)
        return value.market_open if value else None

    def session_close(self, session_date: date) -> datetime | None:
        value = self.session(session_date)
        return value.market_close if value else None

    def session_bounds(self, session_date: date) -> tuple[datetime, datetime] | None:
        value = self.session(session_date)
        return (value.market_open, value.market_close) if value else None


class NyseCalendar(MarketCalendar):
    """NYSE regular-session calendar backed by pandas-market-calendars."""

    def __init__(self) -> None:
        self._calendar = mcal.get_calendar("NYSE")

    @lru_cache(maxsize=512)
    def session(self, session_date: date) -> TradingSession | None:
        schedule = self._calendar.schedule(
            start_date=session_date,
            end_date=session_date,
        )
        if schedule.empty:
            return None
        row = schedule.iloc[0]
        market_open = row["market_open"].to_pydatetime().astimezone(EASTERN)
        market_close = row["market_close"].to_pydatetime().astimezone(EASTERN)
        is_early_close = not self._calendar.early_closes(schedule).empty
        return TradingSession(
            session_date,
            market_open,
            market_close,
            is_early_close,
        )
