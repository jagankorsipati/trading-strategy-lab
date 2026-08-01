from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


class ArtifactLoadError(RuntimeError):
    def __init__(self, path: Path, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.message = message


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactLoadError(path, f"unable to parse JSON artifact: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactLoadError(path, "JSON artifact must contain an object")
    return value


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        raise ArtifactLoadError(path, f"unable to parse CSV artifact: {exc}") from exc


def parse_trade(row: dict[str, str], trade_id: int) -> dict[str, Any]:
    try:
        entry = datetime.fromisoformat(row["entry_timestamp"])
        exit_at = datetime.fromisoformat(row["exit_timestamp"])
        entry_price = float(row["entry_price"])
        quantity = int(float(row["quantity"]))
        pnl = float(row["realized_pnl"])
        fees = float(row.get("fees", 0) or 0)
        slippage = float(row.get("slippage", 0) or 0)
        notional = entry_price * quantity
        return {
            "id": trade_id,
            "symbol": row["symbol"],
            "direction": row["direction"],
            "entry_timestamp": entry.isoformat(),
            "entry_price": entry_price,
            "exit_timestamp": exit_at.isoformat(),
            "exit_price": float(row["exit_price"]),
            "quantity": quantity,
            "stop_price": float(row["stop_price"]),
            "take_profit_price": float(row["take_profit_price"]),
            "fees": fees,
            "slippage": slippage,
            "realized_pnl": pnl,
            "return_pct": pnl / notional if notional else 0.0,
            "exit_reason": row["exit_reason"],
            "holding_minutes": (exit_at - entry).total_seconds() / 60,
            "modeled_execution_cost": fees + slippage,
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed trade row {trade_id}: {exc}") from exc


def load_trades(path: Path) -> list[dict[str, Any]]:
    return [parse_trade(row, index) for index, row in enumerate(load_csv_rows(path), 1)]


def realized_equity_series(
    trades: Iterable[dict[str, Any]], starting_equity: float
) -> list[dict[str, Any]]:
    equity = starting_equity
    points: list[dict[str, Any]] = []
    for trade in sorted(trades, key=lambda item: item["exit_timestamp"]):
        equity += trade["realized_pnl"]
        points.append({"timestamp": trade["exit_timestamp"], "value": equity})
    return points


def drawdown_series(points: list[dict[str, Any]], starting_equity: float) -> list[dict[str, Any]]:
    peak = starting_equity
    result = []
    for point in points:
        peak = max(peak, point["value"])
        drawdown = point["value"] / peak - 1 if peak else 0.0
        result.append({"timestamp": point["timestamp"], "value": drawdown})
    return result
