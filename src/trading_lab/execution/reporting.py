from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _write_csv(path: Path, rows: list[dict[str, Any]], fallback_fields: list[str]) -> None:
    fields = list(rows[0]) if rows else fallback_fields
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_execution_study(
    *,
    strategy_name: str,
    assumptions: dict[str, Any],
    scenarios: list[dict[str, Any]],
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    config = {
        "strategy": strategy_name,
        "mode": "execution sensitivity analysis",
        "assumptions": assumptions,
    }
    (destination / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    fills = [row for scenario in scenarios for row in scenario["fills"]]
    rejected = [row for scenario in scenarios for row in scenario["rejected_orders"]]
    partial = [row for row in fills if row["status"] == "partially_filled"]
    metrics = [scenario["metrics"] for scenario in scenarios]
    _write_csv(destination / "fills.csv", fills, ["scenario"])
    _write_csv(destination / "rejected_orders.csv", rejected, ["scenario"])
    _write_csv(destination / "partial_fills.csv", partial, ["scenario"])
    _write_csv(destination / "metrics.csv", metrics, ["scenario"])

    summary = {
        "strategy": strategy_name,
        "primary_purpose": "sensitivity analysis; scenarios are not ranked or selected",
        "scenarios": metrics,
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        f"# Execution sensitivity: {strategy_name}",
        "",
        "These deterministic OHLCV models are assumptions, not reconstructed broker fills. "
        "No scenario is selected as a winner.",
        "",
        "| Scenario | Return | P&L | Trades attempted | Full | Partial | Unfilled | Rejected | PF | Max DD | Total cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in metrics:
        pf = "undefined" if item["profit_factor"] is None else f"{item['profit_factor']:.2f}"
        lines.append(
            f"| {item['scenario']} | {item['total_return']:.2%} | ${item['total_pnl']:,.2f} | "
            f"{item['trades_attempted']} | {item['fully_filled_entries']} | "
            f"{item['partially_filled_entries']} | {item['unfilled_entries']} | "
            f"{item['rejected_entries']} | {pf} | {item['maximum_drawdown']:.2%} | "
            f"${item['total_modeled_execution_cost']:,.2f} |"
        )
    lines.extend([
        "",
        "The cache contains OHLCV rather than historical quotes or order-book events. "
        "Spread, depth, queue priority, impact, latency, routing, and intrabar sequence "
        "cannot be recovered exactly. Historical performance does not establish future profitability.",
        "",
    ])
    (destination / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return destination
