# Changelog

## Milestone 3B

- Added typed, deterministic execution-model infrastructure for fixed-bps,
  spread-proxy, OHLCV volume-participation, conservative limit/stop, and
  historical bar-latency assumptions.
- Added dependency-injected engine integration with backward-compatible
  fixed-bps defaults and fill-level cost breakdowns.
- Added execution-sensitivity reports with full, partial, unfilled, and rejected
  order accounting.
- Preserved frozen strategy sources, defaults, calendar rules, stop-first
  ambiguity handling, portfolio cash semantics, and existing research results.

## Milestone 3A

- Added configurable, typed, chronological walk-forward windows.
- Added fixed-strategy rolling research, validation, and out-of-sample evaluation
  without fitting or parameter selection.
- Added per-period exchange-calendar data-quality attribution and 0/2/5 bps
  friction scenarios.
- Added JSON, CSV, and Markdown walk-forward reports plus an immutable-baseline
  CLI and deterministic leakage-prevention tests.

## v0.1.0-research-foundation

- Added an adversarially audited, OHLC-aware backtesting engine with conservative
  ambiguous-bar, gap, stop, target, slippage, fee, cash, and drawdown behavior.
- Added timezone normalization and replaceable NYSE exchange-calendar support,
  including holidays, daylight-saving transitions, and scheduled early closes.
- Added an Alpaca historical equity-data provider with local CSV caching.
- Added deterministic historical-data validation and regular-session coverage
  reporting without manufacturing missing candles.
- Froze ORB-v1 and Reference-ORB-v1 as immutable research baselines.
- Completed QQQ one-minute evaluation for 2018–2025, including independent annual
  resets and continuous simulations.
- Added QQQ buy-and-hold benchmarking, friction sensitivity, market exposure,
  and long/short diagnostics.
- Concluded that neither frozen baseline survives modest modeled friction
  consistently. No claim of future profitability is made.

The annotated Git tag `v0.1.0-research-foundation` identifies the original
research-foundation commit.
