# Walk-forward research methodology

## Purpose

Milestone 3A provides reusable, leakage-resistant chronological evaluation. Its
current mode is **Fixed-strategy rolling out-of-sample evaluation**. ORB-v1 and
Reference-ORB-v1 have no fitting or parameter-selection procedure, so research
and validation periods are reported descriptively and never used to alter the
strategies.

## Period roles

- Research: historical observations that a future experiment may use to develop
  a hypothesis.
- Validation: later observations that may eventually support a predeclared model
  selection procedure.
- Out-of-sample: strictly later observations used for the primary conclusion.

All date boundaries are inclusive. Within a window, research ends before
validation begins and validation ends before out-of-sample testing begins.
Overlapping roles, reversed ranges, non-positive steps, windows outside available
data, and duplicate windows are rejected.

The illustrative defaults produce:

| Window | Research | Validation | Out-of-sample |
|---:|---|---|---|
| 1 | 2018–2020 | 2021 | 2022 |
| 2 | 2019–2021 | 2022 | 2023 |
| 3 | 2020–2022 | 2023 | 2024 |
| 4 | 2021–2023 | 2024 | 2025 |

Each period is an independent backtest with the baseline starting-equity and
strategy state reset. Windows intentionally overlap across rolling iterations,
but roles never overlap within a window. No result from a validation or
out-of-sample period is visible to an earlier period.

## Fixed-strategy evaluation

The strategy factory constructs only the exact frozen defaults. The CLI exposes
window and friction settings, but no baseline strategy parameters. The same
strategy configuration is used at 0, 2, and 5 bps, and Reference-ORB-v1 retains
its per-share commission.

Every period reports capital, return, P&L, trades, win rate, profit factor,
drawdown, Sharpe, Sortino, return/drawdown, long and short P&L, exposure, and exit
counts. Reports prominently aggregate the non-overlapping rolling out-of-sample
years; research-period returns are not the primary conclusion.

## Data quality

Annual inputs pass through the existing exchange-calendar validator. Each period
records expected and represented sessions, absent or truncated sessions, missing
regular-session minutes, malformed candles, and duplicate timestamps. Missing
candles are never manufactured. The May 2018 truncated sessions and March 2020
gaps therefore remain visible in any research period that contains them.

## Outputs

Each run writes beneath `output/walk_forward/<strategy>/<run-id>/`:

- `config.json`
- `windows.csv`
- `period_metrics.csv`
- `summary.json`
- `report.md`

## Future extension points

Typed windows and period results can later support a separately named strategy
experiment with an explicit, predeclared selection callback. Milestone 3A does
not implement parameter search, automatic optimization, winner selection, or a
regime filter. Such functionality must preserve chronology and must never mutate
a frozen baseline.

## Limitations

Rolling evaluation does not remove OHLC ambiguity, execution-model risk,
survivorship or data-source bias, missing-bar limitations, or the possibility of
researcher overfitting across repeated studies. Overlapping research windows also
make their descriptive results statistically dependent. Historical results do
not establish future profitability.
