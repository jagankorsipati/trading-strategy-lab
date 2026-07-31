from __future__ import annotations

from datetime import date

from trading_lab.research.models import DateRange, WalkForwardConfig, WalkForwardWindow


def _year_range(first: int, length: int) -> DateRange:
    return DateRange(date(first, 1, 1), date(first + length - 1, 12, 31))


def generate_walk_forward_windows(
    config: WalkForwardConfig,
    *,
    available_start: date,
    available_end: date,
) -> tuple[WalkForwardWindow, ...]:
    """Generate non-leaking rolling windows with inclusive date boundaries."""
    if available_end < available_start:
        raise ValueError("available data range is invalid")
    windows: list[WalkForwardWindow] = []
    research_start_year = config.first_research_year
    window_id = 1
    while True:
        research = _year_range(research_start_year, config.research_years)
        validation = _year_range(research.end.year + 1, config.validation_years)
        out_of_sample = _year_range(validation.end.year + 1, config.test_years)
        if out_of_sample.end.year > config.last_available_year:
            break
        window = WalkForwardWindow(window_id, research, validation, out_of_sample)
        if research.start < available_start or out_of_sample.end > available_end:
            raise ValueError("generated window falls outside available data")
        windows.append(window)
        research_start_year += config.step_years
        window_id += 1
    if not windows:
        raise ValueError("configuration does not produce any complete windows")
    signatures = {
        (window.research, window.validation, window.out_of_sample)
        for window in windows
    }
    if len(signatures) != len(windows):
        raise ValueError("duplicate walk-forward windows generated")
    return tuple(windows)
