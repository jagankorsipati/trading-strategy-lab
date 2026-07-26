# Trading Strategy Lab

Trading Strategy Lab is a research-oriented Python project for defining and
backtesting quantitative trading strategies. Milestone 1 provides a trustworthy,
testable intraday backtesting foundation and a configurable QQQ Opening Range
Breakout (ORB) strategy. It deliberately contains no frontend, broker connection,
AI integration, database, paper trading, or live trading.

## Milestone 1 architecture and plan

The package separates the domain into:

- `data`: timezone-aware candle models and strict CSV validation.
- `strategies`: a reusable stateful strategy interface and the ORB implementation.
- `risk`: position sizing and stop/take-profit rules.
- `backtesting`: the chronological event loop, executions, portfolio, and metrics.
- `reporting`: terminal summaries plus CSV and JSON exports.
- `config`: immutable, validated configuration.

The engine only consumes `TradingStrategy` signals; it has no ORB-specific logic.
This lets later strategies reuse execution, risk, portfolio, and reporting code.
The milestone is implemented incrementally through domain/configuration models,
data validation, strategy behavior, execution/accounting, metrics/reporting, and
deterministic tests.

## How ORB works

By default, bars from 09:30 inclusive to 09:45 exclusive (US Eastern) establish
the opening high and low. Starting with the 09:45 bar, a configured close-based
or intrabar high/low breakout can emit a long or short signal. Entries are filled
at the signal bar's close with configured slippage. Stops and targets are checked
from the next bar onward. If both are touched on one bar, the stop is chosen as a
conservative assumption. Any open position is closed on the first bar at or after
the configured end-of-day time, and state resets each session.

These conventions avoid look-ahead: a bar is processed only after all of that
bar's OHLC data is known. This is a bar-based simulator, so it cannot reconstruct
the sequence of prices within a candle. Position size is a fixed share quantity;
fees are fixed per execution and slippage is expressed in basis points. Only one
position may be open at a time.

## Installation

Python 3.12 or newer is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

On macOS/Linux, activate with `source .venv/bin/activate`.

## Tests

```bash
python -m pytest
```

Tests use small synthetic datasets and cover range construction, signal timing,
look-ahead protection, both directions, risk exits, EOD liquidation, daily trade
limits, fees, slippage, metrics, and invalid data.

## Running a backtest

```bash
python scripts/run_backtest.py --data path/to/qqq.csv
```

Optional arguments expose the main ORB, execution, and capital assumptions; run
with `--help` for details. Results are printed and written to
`output/trades.csv` and `output/summary.json`.

Expected CSV columns:

```text
timestamp,open,high,low,close,volume
2025-01-02T09:30:00-05:00,500.00,500.40,499.80,500.20,120000
```

Timestamps must include a UTC offset or timezone. Rows must be strictly
chronological and unique. OHLC fields cannot be missing, prices must be positive,
volume cannot be negative, `high` must be at least open/close/low, and `low` must
be at most open/close/high. Input is converted to `America/New_York`.

## Important Disclaimer

This project is for research and education only. Historical performance does not
guarantee future performance. Backtests have important limitations, including
data quality, candle granularity, fill assumptions, slippage, fees, and market
regime changes. This software is not financial advice and should not be treated
as such.
