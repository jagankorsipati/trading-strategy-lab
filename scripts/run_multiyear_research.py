from __future__ import annotations

import argparse
import json
from math import prod
from pathlib import Path

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.config.settings import (
    BacktestConfig,
    ORBConfig,
    ReferenceORBConfig,
)
from trading_lab.data.loader import load_csv
from trading_lab.data.quality import audit_historical_csv
from trading_lab.market.calendar import NyseCalendar
from trading_lab.reporting.research import (
    buy_and_hold_benchmark,
    summarize_backtest,
)
from trading_lab.strategies.orb import ORBStrategy
from trading_lab.strategies.reference_orb import ReferenceORBStrategy

YEARS = tuple(range(2018, 2026))
SCENARIOS = {"zero_0bps": 0.0, "modest_2bps": 2.0, "stress_5bps": 5.0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run frozen QQQ strategies across 2018-2025"
    )
    parser.add_argument("--cache-dir", default="data/historical/QQQ/1min")
    parser.add_argument("--output", default="output/multiyear_results.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    calendar = NyseCalendar()
    bars_by_year = {}
    regular_by_year = {}
    quality = {}

    for year in YEARS:
        path = cache_dir / f"{year}-01-01_{year}-12-31.csv"
        report = audit_historical_csv(path, year=year, calendar=calendar)
        quality[str(year)] = {
            "raw_bars": report.total_raw_bars,
            "expected_sessions": report.expected_sessions,
            "represented_sessions": report.represented_sessions,
            "regular_session_bars": report.regular_session_bars,
            "missing_sessions": report.absent_sessions,
            "sessions_with_missing_bars": report.sessions_with_missing_bars,
            "largest_missing_count": report.largest_missing_count,
            "malformed_bars": report.malformed_ohlc_candles,
            "duplicate_timestamp_rows": report.duplicate_timestamp_rows,
        }
        bars = load_csv(str(path))
        regular = [
            bar
            for bar in bars
            if (session := calendar.session(bar.timestamp.date())) is not None
            and session.contains(bar.timestamp)
        ]
        bars_by_year[year] = bars
        regular_by_year[year] = regular
        print(f"Validated and loaded {year}: {len(regular):,} regular bars")

    results = {
        "data_quality": quality,
        "strategies": {"ORB-v1": {}, "Reference-ORB-v1": {}},
        "buy_and_hold": {},
        "combined_continuous": {"ORB-v1": {}, "Reference-ORB-v1": {}},
        "independent_year_aggregates": {"ORB-v1": {}, "Reference-ORB-v1": {}},
    }
    all_regular = [
        bar for year in YEARS for bar in regular_by_year[year]
    ]

    for year in YEARS:
        results["buy_and_hold"][str(year)] = buy_and_hold_benchmark(
            regular_by_year[year]
        )
    results["buy_and_hold"]["2018-2025"] = buy_and_hold_benchmark(all_regular)

    for strategy_name in ("ORB-v1", "Reference-ORB-v1"):
        for scenario_name, slippage_bps in SCENARIOS.items():
            annual = {}
            for year in YEARS:
                if strategy_name == "ORB-v1":
                    strategy = ORBStrategy(ORBConfig())
                    config = BacktestConfig(
                        starting_capital=10_000,
                        position_size=10,
                        stop_loss_pct=0.005,
                        take_profit_pct=0.01,
                        trading_fee=0,
                        slippage_bps=slippage_bps,
                    )
                else:
                    strategy = ReferenceORBStrategy(ReferenceORBConfig())
                    config = BacktestConfig(
                        starting_capital=25_000,
                        position_size=1,
                        trading_fee=0,
                        slippage_bps=slippage_bps,
                    )
                result = BacktestEngine(strategy, config, calendar).run(
                    regular_by_year[year]
                )
                annual[str(year)] = summarize_backtest(
                    result, len(regular_by_year[year])
                )
                print(
                    f"{strategy_name} {scenario_name} {year}: "
                    f"{annual[str(year)]['total_return']:.2%}"
                )
            results["strategies"][strategy_name][scenario_name] = annual
            annual_returns = [
                annual[str(year)]["total_return"] for year in YEARS
            ]
            results["independent_year_aggregates"][strategy_name][scenario_name] = {
                "sum_of_yearly_pnl": sum(
                    annual[str(year)]["total_pnl"] for year in YEARS
                ),
                "compounded_annual_return_sequence": prod(
                    1 + value for value in annual_returns
                ) - 1,
                "profitable_years": sum(value > 0 for value in annual_returns),
                "losing_years": sum(value < 0 for value in annual_returns),
            }

            if strategy_name == "ORB-v1":
                combined_strategy = ORBStrategy(ORBConfig())
                combined_config = BacktestConfig(
                    starting_capital=10_000,
                    position_size=10,
                    stop_loss_pct=0.005,
                    take_profit_pct=0.01,
                    trading_fee=0,
                    slippage_bps=slippage_bps,
                )
            else:
                combined_strategy = ReferenceORBStrategy(ReferenceORBConfig())
                combined_config = BacktestConfig(
                    starting_capital=25_000,
                    position_size=1,
                    trading_fee=0,
                    slippage_bps=slippage_bps,
                )
            combined = BacktestEngine(
                combined_strategy, combined_config, calendar
            ).run(all_regular)
            results["combined_continuous"][strategy_name][scenario_name] = (
                summarize_backtest(combined, len(all_regular))
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, allow_nan=False)
    print(f"Wrote {output.resolve()}")


if __name__ == "__main__":
    main()
