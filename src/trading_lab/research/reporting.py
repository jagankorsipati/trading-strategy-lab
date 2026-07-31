from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date
from math import prod
from pathlib import Path
from typing import Any

from trading_lab.research.models import PeriodPurpose, WalkForwardResult


def _json_default(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _period_row(period) -> dict[str, Any]:
    quality = period.data_quality
    return {
        "window_id": period.window_id,
        "purpose": period.purpose.value,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
        "strategy_name": period.strategy_name,
        "friction_bps": period.friction_bps,
        **dict(period.metrics),
        "quality_clean": quality.is_clean,
        "expected_sessions": quality.expected_sessions,
        "represented_sessions": quality.represented_sessions,
        "missing_sessions": ";".join(map(str, quality.missing_sessions)),
        "truncated_sessions": ";".join(map(str, quality.truncated_sessions)),
        "missing_regular_session_bars": quality.missing_regular_session_bars,
        "malformed_bars": quality.malformed_bars,
        "duplicate_timestamps": quality.duplicate_timestamps,
    }


def _summary(result: WalkForwardResult) -> dict[str, Any]:
    scenarios: dict[str, Any] = {}
    for friction in result.config.slippage_bps:
        oos = [
            period
            for period in result.periods
            if period.purpose == PeriodPurpose.OUT_OF_SAMPLE
            and period.friction_bps == friction
        ]
        returns = [float(period.metrics["total_return"]) for period in oos]
        scenarios[str(friction)] = {
            "out_of_sample_periods": len(oos),
            "profitable_periods": sum(value > 0 for value in returns),
            "losing_periods": sum(value < 0 for value in returns),
            "compounded_out_of_sample_return": prod(1 + value for value in returns) - 1,
            "sum_out_of_sample_pnl": sum(
                float(period.metrics["total_pnl"]) for period in oos
            ),
            "periods_with_quality_findings": sum(
                not period.data_quality.is_clean for period in oos
            ),
        }
    return {
        "mode": result.mode,
        "strategy_name": result.strategy_name,
        "primary_basis": "out_of_sample periods",
        "scenarios": scenarios,
    }


def _markdown(result: WalkForwardResult, summary: dict[str, Any]) -> str:
    def metric(value: Any, format_spec: str) -> str:
        return "undefined" if value is None else format(float(value), format_spec)

    lines = [
        f"# Walk-forward report: {result.strategy_name}",
        "",
        f"Mode: **{result.mode}**",
        "",
        "The frozen strategy is not fitted or selected in research or validation periods. "
        "The primary conclusion is based only on rolling out-of-sample periods.",
        "",
        "## Out-of-sample summary",
        "",
        "| Slippage | OOS periods | Profitable | Compounded return | Sum P&L | Quality findings |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for friction, item in summary["scenarios"].items():
        lines.append(
            f"| {float(friction):g} bps | {item['out_of_sample_periods']} | "
            f"{item['profitable_periods']} | {item['compounded_out_of_sample_return']:.2%} | "
            f"${item['sum_out_of_sample_pnl']:,.2f} | {item['periods_with_quality_findings']} |"
        )
    lines.extend(
        [
            "",
            "## Period metrics",
            "",
            "| Window | Role | Dates | bps | Return | P&L | Trades | PF | Max DD | Long P&L | Short P&L | Quality |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for period in result.periods:
        metrics = period.metrics
        lines.append(
            f"| {period.window_id} | {period.purpose.value} | "
            f"{period.start_date}–{period.end_date} | {period.friction_bps:g} | "
            f"{float(metrics['total_return']):.2%} | ${float(metrics['total_pnl']):,.2f} | "
            f"{metrics['total_trades']} | {metric(metrics['profit_factor'], '.2f')} | "
            f"{float(metrics['maximum_drawdown']):.2%} | ${float(metrics['long_pnl']):,.2f} | "
            f"${float(metrics['short_pnl']):,.2f} | "
            f"{'clean' if period.data_quality.is_clean else 'findings'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation limitations",
            "",
            "Research and validation results are descriptive only; no parameters were selected. "
            "OHLC bars cannot reveal intrabar price order, missing bars are not manufactured, "
            "and modeled slippage is not a guarantee of executable fills. Historical results "
            "do not establish future profitability.",
            "",
        ]
    )
    return "\n".join(lines)


def write_walk_forward_reports(result: WalkForwardResult, output_dir: str | Path) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    config = asdict(result.config)
    config.update({"strategy_name": result.strategy_name, "mode": result.mode})
    (destination / "config.json").write_text(
        json.dumps(config, indent=2, default=_json_default), encoding="utf-8"
    )

    window_rows = [
        {
            "window_id": window.window_id,
            "research_start": window.research.start,
            "research_end": window.research.end,
            "validation_start": window.validation.start,
            "validation_end": window.validation.end,
            "out_of_sample_start": window.out_of_sample.start,
            "out_of_sample_end": window.out_of_sample.end,
        }
        for window in result.windows
    ]
    with (destination / "windows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(window_rows[0]))
        writer.writeheader()
        writer.writerows(window_rows)

    period_rows = [_period_row(period) for period in result.periods]
    with (destination / "period_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(period_rows[0]))
        writer.writeheader()
        writer.writerows(period_rows)

    summary = _summary(result)
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (destination / "report.md").write_text(
        _markdown(result, summary), encoding="utf-8"
    )
    return destination
