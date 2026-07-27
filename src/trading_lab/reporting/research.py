from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from trading_lab.backtesting.engine import BacktestResult
from trading_lab.models import MarketBar


def annualized_daily_ratios(
    equity_curve: Sequence[tuple[object, float]],
    starting_capital: float,
) -> tuple[float | None, float | None]:
    frame = pd.DataFrame(equity_curve, columns=["timestamp", "equity"])
    if frame.empty:
        return None, None
    frame["date"] = pd.to_datetime(frame["timestamp"], utc=True).dt.date
    daily = frame.groupby("date", sort=True)["equity"].last().to_numpy(dtype=float)
    levels = np.concatenate(([starting_capital], daily))
    returns = levels[1:] / levels[:-1] - 1
    if len(returns) < 2:
        return None, None
    standard_deviation = returns.std(ddof=1)
    downside = returns[returns < 0]
    downside_deviation = downside.std(ddof=1) if len(downside) > 1 else 0.0
    sharpe = (
        float(returns.mean() / standard_deviation * math.sqrt(252))
        if standard_deviation
        else None
    )
    sortino = (
        float(returns.mean() / downside_deviation * math.sqrt(252))
        if downside_deviation
        else None
    )
    return sharpe, sortino


def summarize_backtest(
    result: BacktestResult,
    regular_session_minutes: int,
) -> dict[str, Any]:
    trades = result.trades
    winners = [trade.realized_pnl for trade in trades if trade.realized_pnl > 0]
    losers = [trade.realized_pnl for trade in trades if trade.realized_pnl < 0]
    holding_minutes = [
        (trade.exit_timestamp - trade.entry_timestamp).total_seconds() / 60
        for trade in trades
    ]
    sharpe, sortino = annualized_daily_ratios(
        result.equity_curve,
        float(result.metrics["starting_capital"]),
    )
    maximum_drawdown = float(result.metrics["maximum_drawdown"])
    return {
        **result.metrics,
        "sharpe": sharpe,
        "sortino": sortino,
        "return_over_max_drawdown": (
            float(result.metrics["total_return"]) / maximum_drawdown
            if maximum_drawdown
            else None
        ),
        "average_winner": float(np.mean(winners)) if winners else 0.0,
        "average_loser": float(np.mean(losers)) if losers else 0.0,
        "long_trades": sum(
            trade.direction.value == "long" for trade in trades
        ),
        "short_trades": sum(
            trade.direction.value == "short" for trade in trades
        ),
        "long_pnl": sum(
            trade.realized_pnl
            for trade in trades
            if trade.direction.value == "long"
        ),
        "short_pnl": sum(
            trade.realized_pnl
            for trade in trades
            if trade.direction.value == "short"
        ),
        "stop_exits": sum(
            trade.exit_reason.value == "STOP_LOSS" for trade in trades
        ),
        "target_exits": sum(
            trade.exit_reason.value == "TAKE_PROFIT" for trade in trades
        ),
        "eod_exits": sum(
            trade.exit_reason.value == "END_OF_DAY" for trade in trades
        ),
        "average_holding_minutes": (
            float(np.mean(holding_minutes)) if holding_minutes else 0.0
        ),
        "market_exposure": (
            sum(holding_minutes) / regular_session_minutes
            if regular_session_minutes
            else 0.0
        ),
        "total_fees": sum(trade.fees for trade in trades),
        "modeled_slippage_cost": sum(trade.slippage for trade in trades),
    }


def buy_and_hold_benchmark(
    regular_bars: Sequence[MarketBar],
    starting_capital: float = 10_000,
) -> dict[str, Any]:
    if not regular_bars:
        raise ValueError("benchmark requires regular-session bars")
    entry_price = regular_bars[0].open
    exit_price = regular_bars[-1].close
    shares = starting_capital / entry_price
    intraday_equity = np.array([bar.close * shares for bar in regular_bars])
    equity = np.concatenate(([starting_capital], intraday_equity))
    peaks = np.maximum.accumulate(equity)
    maximum_drawdown = float(np.max((peaks - equity) / peaks))

    frame = pd.DataFrame(
        {
            "timestamp": [bar.timestamp for bar in regular_bars],
            "close": [bar.close for bar in regular_bars],
        }
    )
    frame["date"] = pd.to_datetime(frame["timestamp"], utc=True).dt.date
    daily_close = frame.groupby("date", sort=True)["close"].last().to_numpy()
    daily_levels = np.concatenate(([entry_price], daily_close))
    returns = daily_levels[1:] / daily_levels[:-1] - 1
    realized_volatility = (
        float(returns.std(ddof=1) * math.sqrt(252))
        if len(returns) > 1
        else None
    )
    return {
        "starting_equity": starting_capital,
        "ending_equity": shares * exit_price,
        "total_pnl": shares * exit_price - starting_capital,
        "total_return": exit_price / entry_price - 1,
        "maximum_drawdown": maximum_drawdown,
        "realized_volatility": realized_volatility,
        "entry_timestamp": regular_bars[0].timestamp.isoformat(),
        "entry_price": entry_price,
        "exit_timestamp": regular_bars[-1].timestamp.isoformat(),
        "exit_price": exit_price,
        "fractional_shares": shares,
    }
