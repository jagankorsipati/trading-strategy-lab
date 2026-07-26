from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from trading_lab.models import Trade


def calculate_metrics(
    trades: Sequence[Trade],
    equity_curve: Sequence[tuple[object, float]],
    starting_capital: float,
) -> dict[str, float | int | None]:
    pnls = np.array([trade.realized_pnl for trade in trades], dtype=float)
    winners = pnls[pnls > 0]
    losers = pnls[pnls < 0]
    ending_capital = (
        float(equity_curve[-1][1])
        if equity_curve
        else starting_capital + float(pnls.sum())
    )
    total_pnl = ending_capital - starting_capital

    if equity_curve:
        equities = np.array([point[1] for point in equity_curve], dtype=float)
        # Starting capital is an observable equity point and must remain the
        # initial high-water mark even if the first bar immediately loses money.
        peaks = np.maximum.accumulate(
            np.concatenate(([float(starting_capital)], equities))
        )[1:]
        drawdowns = np.divide(
            equities - peaks, peaks, out=np.zeros_like(equities), where=peaks != 0
        )
        maximum_drawdown = abs(float(drawdowns.min()))
    else:
        maximum_drawdown = 0.0

    gross_profit = float(winners.sum())
    gross_loss = abs(float(losers.sum()))
    if gross_loss:
        profit_factor: float | None = gross_profit / gross_loss
    elif gross_profit:
        profit_factor = None  # undefined/infinite, represented safely in JSON
    else:
        profit_factor = 0.0

    count = len(trades)
    return {
        "starting_capital": float(starting_capital),
        "ending_capital": ending_capital,
        "total_return": total_pnl / starting_capital if starting_capital else 0.0,
        "total_pnl": total_pnl,
        "total_trades": count,
        "winning_trades": int(len(winners)),
        "losing_trades": int(len(losers)),
        "win_rate": len(winners) / count if count else 0.0,
        "average_winner": float(winners.mean()) if len(winners) else 0.0,
        "average_loser": float(losers.mean()) if len(losers) else 0.0,
        "profit_factor": profit_factor,
        "maximum_drawdown": maximum_drawdown,
        "average_trade_return": (
            float(np.mean([trade.return_pct for trade in trades])) if count else 0.0
        ),
        "largest_winning_trade": float(winners.max()) if len(winners) else 0.0,
        "largest_losing_trade": float(losers.min()) if len(losers) else 0.0,
    }
