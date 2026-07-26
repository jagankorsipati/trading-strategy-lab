from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from trading_lab.backtesting.engine import BacktestResult


def _money(value: float) -> str:
    return f"${value:,.2f}"


def format_summary(result: BacktestResult, title: str = "QQQ ORB Backtest") -> str:
    metrics = result.metrics
    profit_factor = metrics["profit_factor"]
    pf_text = "N/A" if profit_factor is None else f"{profit_factor:.2f}"
    return "\n".join(
        [
            title,
            "",
            f"Period: {result.start_timestamp.date()} -> {result.end_timestamp.date()}",
            f"Starting Capital: {_money(metrics['starting_capital'])}",
            f"Ending Capital: {_money(metrics['ending_capital'])}",
            f"Total P&L: {_money(metrics['total_pnl'])}",
            f"Total Return: {metrics['total_return']:.2%}",
            f"Trades: {metrics['total_trades']}",
            f"Win Rate: {metrics['win_rate']:.2%}",
            f"Profit Factor: {pf_text}",
            f"Maximum Drawdown: {metrics['maximum_drawdown']:.2%}",
        ]
    )


def export_results(result: BacktestResult, output_dir: str | Path = "output") -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    trade_fields = [
        "symbol",
        "direction",
        "entry_timestamp",
        "entry_price",
        "exit_timestamp",
        "exit_price",
        "quantity",
        "stop_price",
        "take_profit_price",
        "fees",
        "slippage",
        "realized_pnl",
        "exit_reason",
    ]
    with (output / "trades.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=trade_fields)
        writer.writeheader()
        for trade in result.trades:
            row = asdict(trade)
            row["direction"] = trade.direction.value
            row["exit_reason"] = trade.exit_reason.value
            row["entry_timestamp"] = trade.entry_timestamp.isoformat()
            row["exit_timestamp"] = trade.exit_timestamp.isoformat()
            writer.writerow(row)
    with (output / "summary.json").open("w", encoding="utf-8") as handle:
        # Limit serialized precision to what a bar-based simulation can justify.
        serialized = {
            key: round(value, 10) if isinstance(value, float) else value
            for key, value in result.metrics.items()
        }
        json.dump(serialized, handle, indent=2, allow_nan=False)
