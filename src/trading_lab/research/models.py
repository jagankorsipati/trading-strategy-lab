from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class PeriodPurpose(StrEnum):
    RESEARCH = "research"
    VALIDATION = "validation"
    OUT_OF_SAMPLE = "out_of_sample"


@dataclass(frozen=True)
class DateRange:
    """An inclusive calendar-date range."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("period end date cannot precede its start date")

    def overlaps(self, other: DateRange) -> bool:
        return self.start <= other.end and other.start <= self.end


@dataclass(frozen=True)
class WalkForwardConfig:
    first_research_year: int
    last_available_year: int
    research_years: int = 3
    validation_years: int = 1
    test_years: int = 1
    step_years: int = 1
    slippage_bps: tuple[float, ...] = (0.0, 2.0, 5.0)

    def __post_init__(self) -> None:
        lengths = (
            self.research_years,
            self.validation_years,
            self.test_years,
            self.step_years,
        )
        if any(value <= 0 for value in lengths):
            raise ValueError("window lengths and rolling step must be positive")
        if self.last_available_year < self.first_research_year:
            raise ValueError("available year range is invalid")
        if not self.slippage_bps:
            raise ValueError("at least one friction scenario is required")
        if any(value < 0 for value in self.slippage_bps):
            raise ValueError("slippage cannot be negative")
        if len(set(self.slippage_bps)) != len(self.slippage_bps):
            raise ValueError("friction scenarios cannot be duplicated")


@dataclass(frozen=True)
class WalkForwardWindow:
    window_id: int
    research: DateRange
    validation: DateRange
    out_of_sample: DateRange

    def __post_init__(self) -> None:
        if self.window_id <= 0:
            raise ValueError("window_id must be positive")
        roles = (self.research, self.validation, self.out_of_sample)
        if any(left.overlaps(right) for index, left in enumerate(roles) for right in roles[index + 1 :]):
            raise ValueError("period roles within a window cannot overlap")
        if not self.research.end < self.validation.start:
            raise ValueError("research must precede validation")
        if not self.validation.end < self.out_of_sample.start:
            raise ValueError("validation must precede out-of-sample testing")

    def periods(self) -> tuple[tuple[PeriodPurpose, DateRange], ...]:
        return (
            (PeriodPurpose.RESEARCH, self.research),
            (PeriodPurpose.VALIDATION, self.validation),
            (PeriodPurpose.OUT_OF_SAMPLE, self.out_of_sample),
        )


@dataclass(frozen=True)
class DataQualityStatus:
    expected_sessions: int
    represented_sessions: int
    missing_sessions: tuple[date, ...] = ()
    truncated_sessions: tuple[date, ...] = ()
    missing_regular_session_bars: int = 0
    malformed_bars: int = 0
    duplicate_timestamps: int = 0

    @property
    def all_expected_sessions_represented(self) -> bool:
        return not self.missing_sessions and self.represented_sessions == self.expected_sessions

    @property
    def is_clean(self) -> bool:
        return (
            self.all_expected_sessions_represented
            and not self.truncated_sessions
            and self.missing_regular_session_bars == 0
            and self.malformed_bars == 0
            and self.duplicate_timestamps == 0
        )


@dataclass(frozen=True)
class PeriodResult:
    window_id: int
    purpose: PeriodPurpose
    start_date: date
    end_date: date
    strategy_name: str
    friction_bps: float
    metrics: Mapping[str, Any]
    data_quality: DataQualityStatus

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("period result dates are invalid")
        if self.friction_bps < 0:
            raise ValueError("friction cannot be negative")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))


@dataclass(frozen=True)
class WalkForwardResult:
    mode: str
    strategy_name: str
    config: WalkForwardConfig
    windows: tuple[WalkForwardWindow, ...]
    periods: tuple[PeriodResult, ...]

    def __post_init__(self) -> None:
        valid_ids = {window.window_id for window in self.windows}
        if any(period.window_id not in valid_ids for period in self.periods):
            raise ValueError("period result references an unknown window")
