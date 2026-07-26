# Trading Strategy Lab

Trading Strategy Lab is a research-oriented Python project for defining and
backtesting quantitative trading strategies. Milestone 1 provides a trustworthy,
testable intraday backtesting foundation and a configurable QQQ Opening Range
Breakout (ORB) strategy. It deliberately contains no frontend, broker connection,
AI integration, database, paper trading, or live trading.

## Milestone 1 architecture and plan

The package separates the domain into:

- `data`: timezone-aware candle models and strict CSV validation.
- `market`: replaceable exchange calendars and regular-session boundaries.
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
or intrabar high/low breakout can emit a long or short signal after that bar is
complete. The signal is first executable at the next same-session bar's open,
with configured adverse slippage. This prevents a strategy from observing a
completed candle and also receiving its closing price.

Stops and targets are checked against every bar after an opening fill, including
the entry bar because the fill occurs at its open. If both are touched on one bar,
the stop is chosen as a conservative assumption. A stop gapped through fills from
the worse opening price before slippage; a target uses the configured target even
after a favorable gap, avoiding invented price improvement. Any open position is
closed using the final valid regular-session bar supplied for that exchange
session.

These conventions avoid look-ahead: a bar is processed only after all of that
bar's OHLC data is known. This is a bar-based simulator, so it cannot reconstruct
the sequence of prices within a candle. Input timestamps are assumed to identify
the start of each bar. Position size is a fixed share quantity;
fees are fixed per execution and slippage is expressed in basis points. Only one
position may be open at a time. Fixed quantity orders require enough equity for
100% of notional plus the entry fee; the same conservative notional requirement
is used for shorts. Cash is debited for long purchases and credited for short
sale proceeds, while equity adds long market value or subtracts the short
liability.

## Exchange calendar and session policy

The default `NyseCalendar` implementation uses `pandas_market_calendars` and
exposes a small `MarketCalendar` interface so another maintained calendar, such
as a Nasdaq-specific implementation, can be substituted later. Calendar times
returned in UTC are converted to timezone-aware `America/New_York` datetimes.

Only bars whose start timestamps fall within the calendar-provided regular
session interval `[market open, market close)` are processed. Bars on weekends,
exchange holidays, before the open, or at/after the close are ignored. If a
dataset contains no valid regular-session bars, the backtest is rejected.
Out-of-session bars cannot construct an opening range, generate a signal, execute
an order, trigger a stop or target, or affect portfolio equity.

The applicable calendar close replaces a hard-coded 4:00 PM cutoff. Standard
sessions close at 4:00 PM Eastern, while known early-close sessions use the
calendar-provided boundary, such as 1:00 PM Eastern. The final supplied valid bar
for each session is the end-of-day liquidation bar. If the expected final candle
before the close is missing, the engine does not manufacture it: an open position
is conservatively liquidated using the close of the last available valid
regular-session bar. This preserves the no-overnight-position rule.

Exchange calendars improve holiday, daylight-saving, and scheduled early-close
correctness. They do not model unexpected exchange halts, unscheduled closures,
symbol-specific suspensions, data-feed outages, or broker-specific trading
restrictions.

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
limits, fees, slippage, metrics, invalid data, holidays, regular-session
filtering, early closes, and daylight-saving transitions.

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

Timestamps must include a UTC offset or timezone and represent bar-start times.
Rows must be strictly
chronological and unique. OHLC fields cannot be missing, prices must be positive,
volume cannot be negative, `high` must be at least open/close/low, and `low` must
be at most open/close/high. Input is converted to `America/New_York`, then filtered
against the exchange calendar's regular session.

## Important Disclaimer

This project is for research and education only. Historical performance does not
guarantee future performance. Backtests have important limitations, including
data quality, candle granularity, fill assumptions, slippage, fees, and market
regime changes. This software is not financial advice and should not be treated
as such.
