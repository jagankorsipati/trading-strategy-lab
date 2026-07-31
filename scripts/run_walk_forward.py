from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

from trading_lab.data.loader import load_csv
from trading_lab.data.quality import DataQualityReport, audit_historical_csv
from trading_lab.market.calendar import NyseCalendar
from trading_lab.research.models import DataQualityStatus, DateRange, WalkForwardConfig
from trading_lab.research.reporting import write_walk_forward_reports
from trading_lab.research.walk_forward import (
    SUPPORTED_STRATEGIES,
    run_fixed_strategy_walk_forward,
)
from trading_lab.research.windows import generate_walk_forward_windows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fixed-strategy rolling out-of-sample evaluation"
    )
    parser.add_argument(
        "--data",
        nargs="+",
        required=True,
        help="Annual CSV files, a combined CSV, or a directory of annual CSV files",
    )
    parser.add_argument("--strategy", choices=SUPPORTED_STRATEGIES, required=True)
    parser.add_argument("--first-year", type=int, default=2018)
    parser.add_argument("--last-year", type=int, default=2025)
    parser.add_argument("--research-years", type=int, default=3)
    parser.add_argument("--validation-years", type=int, default=1)
    parser.add_argument("--test-years", type=int, default=1)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument("--slippage-bps", type=float, nargs="+", default=[0, 2, 5])
    parser.add_argument("--output-root", default="output/walk_forward")
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def _paths(values: list[str], first_year: int, last_year: int) -> list[Path]:
    if len(values) == 1 and Path(values[0]).is_dir():
        root = Path(values[0])
        paths = [root / f"{year}-01-01_{year}-12-31.csv" for year in range(first_year, last_year + 1)]
    else:
        paths = [Path(value) for value in values]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing data files: {missing}")
    return paths


def _quality_lookup(reports: dict[int, DataQualityReport]):
    def lookup(period: DateRange) -> DataQualityStatus:
        selected = [reports[year] for year in range(period.start.year, period.end.year + 1)]
        coverage = [
            item
            for report in selected
            for item in report.session_coverage
            if period.start <= item.session_date <= period.end
        ]
        missing = tuple(item.session_date for item in coverage if item.observed_minutes == 0)
        truncated = tuple(
            item.session_date
            for item in coverage
            if 0 < item.observed_minutes < item.expected_minutes
        )
        return DataQualityStatus(
            expected_sessions=len(coverage),
            represented_sessions=len(coverage) - len(missing),
            missing_sessions=missing,
            truncated_sessions=truncated,
            missing_regular_session_bars=sum(item.missing_minutes for item in coverage),
            malformed_bars=sum(report.malformed_ohlc_candles for report in selected),
            duplicate_timestamps=sum(report.duplicate_timestamp_rows for report in selected),
        )

    return lookup


def main(argv: list[str] | None = None) -> Path:
    args = parse_args(argv)
    calendar = NyseCalendar()
    config = WalkForwardConfig(
        first_research_year=args.first_year,
        last_available_year=args.last_year,
        research_years=args.research_years,
        validation_years=args.validation_years,
        test_years=args.test_years,
        step_years=args.step_years,
        slippage_bps=tuple(args.slippage_bps),
    )
    paths = _paths(args.data, args.first_year, args.last_year)
    bars = sorted(
        (bar for path in paths for bar in load_csv(str(path))),
        key=lambda bar: bar.timestamp,
    )
    reports: dict[int, DataQualityReport] = {}
    for year in range(args.first_year, args.last_year + 1):
        matching = [path for path in paths if path.name.startswith(f"{year}-")]
        source = matching[0] if matching else paths[0]
        reports[year] = audit_historical_csv(source, year=year, calendar=calendar)
    windows = generate_walk_forward_windows(
        config,
        available_start=date(args.first_year, 1, 1),
        available_end=date(args.last_year, 12, 31),
    )
    result = run_fixed_strategy_walk_forward(
        strategy_name=args.strategy,
        bars=bars,
        config=config,
        windows=windows,
        quality_lookup=_quality_lookup(reports),
        calendar=calendar,
    )
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(args.output_root) / args.strategy / run_id
    write_walk_forward_reports(result, output)
    print(f"Wrote {output.resolve()}")
    return output


if __name__ == "__main__":
    main()
