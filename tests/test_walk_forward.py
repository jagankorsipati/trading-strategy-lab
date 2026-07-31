from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from scripts.run_walk_forward import parse_args
from trading_lab import __version__
from trading_lab.config.settings import ORBConfig, ReferenceORBConfig
from trading_lab.models import BreakoutConfirmation, MarketBar, TradeDirection
from trading_lab.research.models import (
    DataQualityStatus,
    DateRange,
    PeriodPurpose,
    WalkForwardConfig,
    WalkForwardWindow,
)
from trading_lab.research.reporting import write_walk_forward_reports
from trading_lab.research.walk_forward import run_fixed_strategy_walk_forward
from trading_lab.research.windows import generate_walk_forward_windows

EASTERN = ZoneInfo("America/New_York")


def _config(**overrides) -> WalkForwardConfig:
    values = {
        "first_research_year": 2018,
        "last_available_year": 2025,
        "research_years": 3,
        "validation_years": 1,
        "test_years": 1,
        "step_years": 1,
        "slippage_bps": (0.0, 2.0, 5.0),
    }
    values.update(overrides)
    return WalkForwardConfig(**values)


def _windows(config: WalkForwardConfig | None = None):
    return generate_walk_forward_windows(
        config or _config(),
        available_start=date(2018, 1, 1),
        available_end=date(2025, 12, 31),
    )


def _bars(first_year=2018, last_year=2022):
    bars = []
    for year in range(first_year, last_year + 1):
        day = datetime(year, 1, 2, 9, 30, tzinfo=EASTERN)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        for minute in range(17):
            price = 100.0 if minute < 15 else 102.0 + minute - 15
            bars.append(
                MarketBar(
                    day + timedelta(minutes=minute),
                    price,
                    price + 0.2,
                    price - 0.2,
                    price,
                    1_000,
                )
            )
    return bars


def _quality(period: DateRange) -> DataQualityStatus:
    finding = period.start.year == 2018
    return DataQualityStatus(
        expected_sessions=1,
        represented_sessions=1,
        truncated_sessions=(date(2018, 5, 2),) if finding else (),
        missing_regular_session_bars=389 if finding else 0,
    )


def test_generates_expected_chronological_windows_and_step():
    windows = _windows()
    assert len(windows) == 4
    assert windows[0].research == DateRange(date(2018, 1, 1), date(2020, 12, 31))
    assert windows[0].validation == DateRange(date(2021, 1, 1), date(2021, 12, 31))
    assert windows[0].out_of_sample == DateRange(date(2022, 1, 1), date(2022, 12, 31))
    assert windows[-1].out_of_sample.end == date(2025, 12, 31)
    stepped = _windows(_config(step_years=2))
    assert [window.research.start.year for window in stepped] == [2018, 2020]


def test_window_roles_must_be_ordered_and_non_overlapping():
    with pytest.raises(ValueError, match="overlap"):
        WalkForwardWindow(
            1,
            DateRange(date(2020, 1, 1), date(2021, 1, 1)),
            DateRange(date(2021, 1, 1), date(2021, 12, 31)),
            DateRange(date(2022, 1, 1), date(2022, 12, 31)),
        )
    with pytest.raises(ValueError, match="research must precede"):
        WalkForwardWindow(
            1,
            DateRange(date(2022, 1, 1), date(2022, 12, 31)),
            DateRange(date(2021, 1, 1), date(2021, 12, 31)),
            DateRange(date(2023, 1, 1), date(2023, 12, 31)),
        )
    with pytest.raises(ValueError, match="validation must precede"):
        WalkForwardWindow(
            1,
            DateRange(date(2020, 1, 1), date(2020, 12, 31)),
            DateRange(date(2022, 1, 1), date(2022, 12, 31)),
            DateRange(date(2021, 1, 1), date(2021, 12, 31)),
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"research_years": 0},
        {"validation_years": 0},
        {"test_years": 0},
        {"step_years": 0},
        {"slippage_bps": ()},
        {"slippage_bps": (2.0, 2.0)},
        {"slippage_bps": (-1.0,)},
    ],
)
def test_invalid_window_configurations_are_rejected(overrides):
    with pytest.raises(ValueError):
        _config(**overrides)


def test_invalid_ranges_and_windows_outside_data_are_rejected():
    with pytest.raises(ValueError, match="end date"):
        DateRange(date(2021, 1, 2), date(2021, 1, 1))
    with pytest.raises(ValueError, match="outside available data"):
        generate_walk_forward_windows(
            _config(),
            available_start=date(2019, 1, 1),
            available_end=date(2025, 12, 31),
        )


def test_fixed_evaluation_assigns_metrics_quality_and_friction_to_periods(tmp_path):
    config = _config(last_available_year=2022, slippage_bps=(0.0, 2.0))
    windows = _windows(config)
    before = ORBConfig()
    result = run_fixed_strategy_walk_forward(
        strategy_name="orb-v1",
        bars=_bars(),
        config=config,
        windows=windows,
        quality_lookup=_quality,
    )
    assert ORBConfig() == before
    assert len(result.periods) == 6
    assert {period.purpose for period in result.periods} == set(PeriodPurpose)
    research = next(
        period
        for period in result.periods
        if period.purpose == PeriodPurpose.RESEARCH and period.friction_bps == 0
    )
    test = next(
        period
        for period in result.periods
        if period.purpose == PeriodPurpose.OUT_OF_SAMPLE and period.friction_bps == 0
    )
    assert research.start_date.year == 2018
    assert research.data_quality.truncated_sessions == (date(2018, 5, 2),)
    assert test.start_date.year == 2022
    assert test.data_quality.is_clean
    zero = next(p for p in result.periods if p.purpose == PeriodPurpose.OUT_OF_SAMPLE and p.friction_bps == 0)
    friction = next(p for p in result.periods if p.purpose == PeriodPurpose.OUT_OF_SAMPLE and p.friction_bps == 2)
    assert zero.metrics["total_trades"] == friction.metrics["total_trades"]
    assert friction.metrics["total_pnl"] < zero.metrics["total_pnl"]

    destination = write_walk_forward_reports(result, tmp_path / "report")
    assert {path.name for path in destination.iterdir()} == {
        "config.json", "windows.csv", "period_metrics.csv", "summary.json", "report.md"
    }
    summary = json.loads((destination / "summary.json").read_text())
    assert summary["primary_basis"] == "out_of_sample periods"


def test_cli_does_not_expose_baseline_parameter_overrides():
    base = ["--data", "bars.csv", "--strategy", "orb-v1"]
    with pytest.raises(SystemExit):
        parse_args(base + ["--opening-range-minutes", "30"])
    reference = ["--data", "bars.csv", "--strategy", "reference-orb-v1"]
    with pytest.raises(SystemExit):
        parse_args(reference + ["--reward-risk-multiple", "2"])


def test_frozen_baseline_default_snapshot():
    assert __version__ == "0.1.0"
    assert ORBConfig() == ORBConfig(
        symbol="QQQ",
        opening_range_minutes=15,
        market_open=time(9, 30),
        trade_direction=TradeDirection.BOTH,
        confirmation=BreakoutConfirmation.CLOSE,
        maximum_trades_per_day=1,
    )
    assert ReferenceORBConfig() == ReferenceORBConfig(
        symbol="QQQ",
        market_open=time(9, 30),
        candle_minutes=5,
        account_value=25_000,
        risk_fraction=0.01,
        max_leverage=4,
        minimum_risk_per_share=0.05,
        reward_risk_multiple=10,
        commission_per_share=0.0005,
        maximum_trades_per_day=1,
    )
