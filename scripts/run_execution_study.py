from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.data.loader import load_csv
from trading_lab.execution import (
    ExecutionStatus,
    FixedBpsExecutionConfig,
    FixedBpsExecutionModel,
    LatencyExecutionConfig,
    LatencyExecutionModel,
    LimitFillPolicy,
    LimitOrderExecutionConfig,
    LimitOrderExecutionModel,
    SpreadBasedExecutionModel,
    SpreadExecutionConfig,
    SpreadMode,
    VolumeAwareExecutionConfig,
    VolumeAwareExecutionModel,
)
from trading_lab.execution.reporting import write_execution_study
from trading_lab.market.calendar import NyseCalendar
from trading_lab.reporting.research import summarize_backtest
from trading_lab.research.walk_forward import SUPPORTED_STRATEGIES, fixed_strategy_components

SCENARIOS = (
    "fixed-0bps", "fixed-2bps", "fixed-5bps", "constant-spread",
    "time-of-day-spread", "volume-aware", "one-bar-latency", "conservative-orders",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic execution sensitivity study")
    parser.add_argument("--data", required=True, help="Annual-cache directory or CSV")
    parser.add_argument("--strategy", choices=SUPPORTED_STRATEGIES, required=True)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2018, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--execution-model", choices=("all", *SCENARIOS), default="all")
    parser.add_argument("--constant-spread-bps", type=float, default=4.0)
    parser.add_argument("--open-spread-bps", type=float, default=6.0)
    parser.add_argument("--middle-spread-bps", type=float, default=2.0)
    parser.add_argument("--close-spread-bps", type=float, default=4.0)
    parser.add_argument("--maximum-participation-rate", type=float, default=0.001)
    parser.add_argument("--impact-coefficient-bps", type=float, default=100.0)
    parser.add_argument("--latency-bars", type=int, default=1)
    parser.add_argument("--latency-bps-per-bar", type=float, default=1.0)
    parser.add_argument("--output-root", default="output/execution_studies")
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def _data_paths(path: Path, start: date, end: date) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(path)
    paths = [path / f"{year}-01-01_{year}-12-31.csv" for year in range(start.year, end.year + 1)]
    missing = [str(item) for item in paths if not item.is_file()]
    if missing:
        raise FileNotFoundError(f"missing annual caches: {missing}")
    return paths


def _models(args) -> dict[str, tuple[object, dict[str, Any]]]:
    return {
        "fixed-0bps": (FixedBpsExecutionModel(FixedBpsExecutionConfig(0)), {"slippage_bps": 0}),
        "fixed-2bps": (FixedBpsExecutionModel(FixedBpsExecutionConfig(2)), {"slippage_bps": 2}),
        "fixed-5bps": (FixedBpsExecutionModel(FixedBpsExecutionConfig(5)), {"slippage_bps": 5}),
        "constant-spread": (
            SpreadBasedExecutionModel(SpreadExecutionConfig(
                mode=SpreadMode.CONSTANT, constant_spread_bps=args.constant_spread_bps,
            )),
            {"spread_proxy_bps": args.constant_spread_bps, "cost_per_side": "half spread"},
        ),
        "time-of-day-spread": (
            SpreadBasedExecutionModel(SpreadExecutionConfig(
                mode=SpreadMode.TIME_OF_DAY,
                open_spread_bps=args.open_spread_bps,
                middle_spread_bps=args.middle_spread_bps,
                close_spread_bps=args.close_spread_bps,
            )),
            {"open_spread_bps": args.open_spread_bps, "middle_spread_bps": args.middle_spread_bps,
             "close_spread_bps": args.close_spread_bps, "open_close_windows_minutes": 30},
        ),
        "volume-aware": (
            VolumeAwareExecutionModel(VolumeAwareExecutionConfig(
                maximum_participation_rate=args.maximum_participation_rate,
                minimum_bar_volume=1_000,
                impact_coefficient_bps=args.impact_coefficient_bps,
                maximum_impact_bps=5,
                allow_partial_fills=True,
            )),
            {"maximum_participation_rate": args.maximum_participation_rate,
             "minimum_bar_volume": 1000, "impact_formula": "coefficient_bps * filled_quantity / bar_volume",
             "impact_coefficient_bps": args.impact_coefficient_bps, "partial_entries": True},
        ),
        "one-bar-latency": (
            LatencyExecutionModel(LatencyExecutionConfig(
                delay_bars=args.latency_bars,
                adverse_bps_per_delayed_bar=args.latency_bps_per_bar,
            )),
            {"additional_delay_bars": args.latency_bars,
             "adverse_bps_per_delayed_bar": args.latency_bps_per_bar},
        ),
        "conservative-orders": (
            LimitOrderExecutionModel(LimitOrderExecutionConfig(
                fill_policy=LimitFillPolicy.CONSERVATIVE_NO_FILL_ON_AMBIGUITY,
            )),
            {"entry_interpretation": "hypothetical stop at completed signal-bar close; immediate-or-cancel per execution bar",
             "stop_policy": "trade-through required; touch-only is no fill",
             "target_policy": "trade-through required; touch-only is no fill"},
        ),
    }


def _scenario_result(name, assumptions, result, regular_minutes):
    metrics = summarize_backtest(result, regular_minutes)
    all_pairs = list(zip(result.order_intents, result.order_results))
    entry_pairs = [
        (intent, decision)
        for intent, decision in all_pairs
        if intent is None or intent.is_entry
    ]
    fills = []
    for execution in result.executions:
        fills.append({
            "scenario": name, "timestamp": execution.timestamp.isoformat(),
            "is_entry": execution.is_entry, "direction": execution.direction.value,
            "reference_price": execution.reference_price, "fill_price": execution.price,
            "requested_quantity": execution.requested_quantity,
            "filled_quantity": execution.quantity, "unfilled_quantity": execution.unfilled_quantity,
            "status": execution.status, "spread_cost": execution.spread_cost,
            "slippage_cost": execution.slippage, "impact_cost": execution.impact_cost,
            "latency_cost": execution.latency_cost, "commission": execution.fee,
            "explanation": execution.explanation,
        })
    rejected = []
    for intent, decision in all_pairs:
        if decision.status in (ExecutionStatus.NOT_FILLED, ExecutionStatus.REJECTED):
            rejected.append({
                "scenario": name,
                "timestamp": intent.timestamp.isoformat() if intent is not None else "",
                "is_entry": True if intent is None else intent.is_entry,
                "status": decision.status.value,
                "reason": decision.rejection_reason.value if decision.rejection_reason else "",
                "requested_quantity": decision.requested_quantity,
                "unfilled_quantity": decision.unfilled_quantity,
                "explanation": decision.explanation,
            })
    spread = sum(item["spread_cost"] for item in fills)
    slippage = sum(item["slippage_cost"] for item in fills)
    impact = sum(item["impact_cost"] for item in fills)
    latency = sum(item["latency_cost"] for item in fills)
    commission = sum(item["commission"] for item in fills)
    metrics.update({
        "scenario": name,
        "assumptions": assumptions,
        "trades_attempted": len(entry_pairs),
        "fully_filled_entries": sum(d.status == ExecutionStatus.FULLY_FILLED for _, d in entry_pairs),
        "partially_filled_entries": sum(d.status == ExecutionStatus.PARTIALLY_FILLED for _, d in entry_pairs),
        "unfilled_entries": sum(d.status == ExecutionStatus.NOT_FILLED for _, d in entry_pairs),
        "rejected_entries": sum(d.status == ExecutionStatus.REJECTED for _, d in entry_pairs),
        "spread_cost": spread,
        "slippage_cost": slippage,
        "impact_cost": impact,
        "latency_cost": latency,
        "commissions": commission,
        "total_modeled_execution_cost": spread + slippage + impact + latency + commission,
    })
    return {"metrics": metrics, "fills": fills, "rejected_orders": rejected}


def main(argv: list[str] | None = None) -> Path:
    args = parse_args(argv)
    if args.end < args.start:
        raise ValueError("end date cannot precede start date")
    paths = _data_paths(Path(args.data), args.start, args.end)
    bars = sorted(
        (bar for path in paths for bar in load_csv(str(path))
         if args.start <= bar.timestamp.date() <= args.end),
        key=lambda bar: bar.timestamp,
    )
    calendar = NyseCalendar()
    regular_minutes = sum(
        (session := calendar.session(bar.timestamp.date())) is not None and session.contains(bar.timestamp)
        for bar in bars
    )
    available = _models(args)
    selected = SCENARIOS if args.execution_model == "all" else (args.execution_model,)
    scenarios = []
    assumptions = {}
    for name in selected:
        model, scenario_assumptions = available[name]
        strategy, config = fixed_strategy_components(args.strategy, 0)
        result = BacktestEngine(strategy, config, calendar, model).run(bars)
        scenarios.append(_scenario_result(name, scenario_assumptions, result, regular_minutes))
        assumptions[name] = scenario_assumptions
        print(f"{name}: {scenarios[-1]['metrics']['total_return']:.2%}")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    assumptions["study_period"] = {
        "start": args.start.isoformat(),
        "end": args.end.isoformat(),
        "source_fields": ["timestamp", "open", "high", "low", "close", "volume"],
        "quote_data_available": False,
    }
    output = Path(args.output_root) / args.strategy / run_id
    write_execution_study(
        strategy_name=args.strategy,
        assumptions=assumptions,
        scenarios=scenarios,
        output_dir=output,
    )
    print(f"Wrote {output.resolve()}")
    return output


if __name__ == "__main__":
    main()
