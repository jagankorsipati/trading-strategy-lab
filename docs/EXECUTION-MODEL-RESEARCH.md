# Execution-model research

## Scope and conclusion

Milestone 3B is deterministic historical sensitivity analysis. It does not
reconstruct broker fills and does not select the scenario with the best return.
ORB-v1 and Reference-ORB-v1 remain frozen; execution models adapt around their
existing signals.

Both strategies retain their idealized gross historical edge in some proxy
models, but both lose under the existing 2 bps-per-side model and the documented
4 bps full-spread proxy. The evidence still does not support strategy-driven
paper trading or a claim of future profitability.

## Architecture

```text
Strategy Signal
  -> OrderIntent
  -> ExecutionModel.execute(intent, execution-bar context)
  -> ExecutionResult: full / partial / no fill / rejected
  -> Portfolio cash and position accounting
  -> Trade lifecycle and fill-level reports
```

`ExecutionModel` is injected into `BacktestEngine`. Existing callers receive
`FixedBpsExecutionModel` configured from `BacktestConfig`, preserving historical
behavior. Strategies do not import execution models, and execution models contain
no ORB-specific logic.

Typed records include order side/type, time in force, requested and filled
quantity, execution status, rejection reason, reference and final prices, and a
cost breakdown for spread, fixed slippage, impact, latency, and commission.

The abstract interface is also the extension point for future quote-aware models.
A stronger model would require synchronized historical bid/ask quotes, quote
sizes, trades, consolidated-tape information, and broker paper-fill logs.

## Implemented models

### Fixed bps

For buys, `fill = reference × (1 + bps/10,000)`; for sells, the sign is reversed.
The reference price continues to come from the conservative engine policy:
next-bar entry open, worse opening price after a stop gap, configured target
without invented improvement, or final supplied regular-session close for EOD.
The 0, 2, and 5 bps results reproduce the existing continuous baselines exactly.

### Spread proxy

Buy fills add half the assumed full spread and sells subtract half. No historical
quote is fabricated.

- Constant scenario: 4 bps assumed full spread, or 2 bps per side.
- Time-of-day scenario: 6 bps full spread during the first 30 minutes, 2 bps in
  the middle, and 4 bps during the final 30 minutes.

Optional impact and latency penalties are separate from spread cost.

### Volume-aware proxy

Modeled entry availability is:

```text
floor(bar volume × maximum participation rate)
```

The study uses a 0.1% maximum participation rate, minimum bar volume of 1,000,
partial entries enabled, and linear adverse impact:

```text
impact bps = 100 × filled quantity / bar volume
```

Impact is capped at 5 bps. Reported candle volume is not assumed to have traded
at one price. Entry partial fills are supported; exits remain full-or-unfilled so
the portfolio cannot silently retain a residual or overnight position.

### Historical bar latency

The study delays entries by one additional available same-session bar and applies
1 adverse bps for that delayed bar. It never sleeps or uses wall-clock time. A
pending entry that would cross the exchange-calendar close is rejected. Stop,
target, and EOD policies are not delayed.

### Conservative limit/stop interpretation

This is explicitly hypothetical and is not the original market-entry baseline.
An entry is treated as a one-execution-bar stop order at the completed signal
bar's close. Stop exits use stop orders, targets use limit orders, and EOD remains
a mandatory market liquidation.

The default conservative policy requires a trade through the order level. A bar
that merely touches the level is treated as ambiguous and does not fill. Orders
are immediate-or-cancel for the evaluated execution bar; queue position and
resting-order priority cannot be inferred. Gap-through stops use the worse open.

## Conservative invariants

- A completed strategy bar cannot fill on that same bar.
- Stop is checked before target when both occur within one OHLC candle.
- Gap-through stops use the worse opening price.
- Favorable target gaps receive no invented improvement in the baseline model.
- Latency cannot cross a session boundary silently.
- Early closes use the exchange calendar.
- The final available valid bar forces EOD liquidation even when the expected
  final minute is missing.
- Missing candles are never manufactured.

## Continuous QQQ 2018–2025 sensitivity

### ORB-v1

| Scenario | Return | P&L | Attempts | Full | Partial | Unfilled | Rejected | PF | Max DD | Modeled cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed 0 bps | 19.64% | $1,963.82 | 2,007 | 2,007 | 0 | 0 | 0 | 1.12 | 4.08% | $0.00 |
| Fixed 2 bps | -4.46% | -$446.41 | 2,007 | 2,007 | 0 | 0 | 0 | 0.97 | 7.66% | $2,639.64 |
| Fixed 5 bps | -41.52% | -$4,151.76 | 19,456 | 1,938 | 0 | 0 | 17,518 | 0.78 | 41.68% | $6,176.07 |
| Constant spread | -4.46% | -$446.41 | 2,007 | 2,007 | 0 | 0 | 0 | 0.97 | 7.66% | $2,639.64 |
| Time-of-day spread | -4.93% | -$493.30 | 2,007 | 2,007 | 0 | 0 | 0 | 0.97 | 7.65% | $2,563.80 |
| Volume-aware | 19.58% | $1,958.50 | 2,007 | 2,007 | 0 | 0 | 0 | 1.12 | 4.08% | $8.12 |
| One-bar latency | 13.26% | $1,325.77 | 2,007 | 2,007 | 0 | 0 | 0 | 1.08 | 5.00% | $659.89 |
| Conservative orders | 23.17% | $2,316.81 | 2,109 | 2,005 | 0 | 104 | 0 | 1.14 | 4.01% | $0.00 |

At fixed 5 bps, accumulated losses cause buying-power rejections. Because ORB-v1
may emit another signal after an unexecuted signal, attempted-order count grows;
this is not 19,456 completed trades.

### Reference-ORB-v1

| Scenario | Return | P&L | Attempts | Full | Partial | Unfilled | Rejected | PF | Max DD | Modeled cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed 0 bps | 83.46% | $20,864.79 | 1,995 | 1,995 | 0 | 0 | 0 | 1.15 | 11.83% | $239.29 |
| Fixed 2 bps | -16.61% | -$4,152.10 | 1,998 | 1,998 | 0 | 0 | 0 | 0.96 | 32.10% | $19,305.21 |
| Fixed 5 bps | -74.30% | -$18,574.86 | 1,998 | 1,998 | 0 | 0 | 0 | 0.76 | 76.15% | $28,655.35 |
| Constant spread | -16.61% | -$4,152.10 | 1,998 | 1,998 | 0 | 0 | 0 | 0.96 | 32.10% | $19,305.21 |
| Time-of-day spread | -32.96% | -$8,240.13 | 1,998 | 1,998 | 0 | 0 | 0 | 0.92 | 44.19% | $22,676.15 |
| Volume-aware | 69.78% | $17,446.21 | 1,995 | 1,660 | 335 | 0 | 0 | 1.14 | 12.02% | $880.19 |
| One-bar latency | 47.56% | $11,890.74 | 1,962 | 1,962 | 0 | 0 | 0 | 1.10 | 14.80% | $6,205.00 |
| Conservative orders | 101.26% | $25,314.87 | 1,995 | 1,919 | 0 | 76 | 0 | 1.18 | 10.52% | $242.66 |

The positive conservative-order result is highly interpretation-dependent and
must not be presented as the frozen baseline or selected as an improvement.
Requiring trade-through removes entries and changes the sample of trades.

## Robust and assumption-dependent conclusions

Robust observations:

- Existing 0/2/5 bps baselines remain exactly reproducible.
- Both strategies lose under 2 bps adverse slippage per side.
- Both lose under the economically equivalent 4 bps full-spread proxy.
- Reference-ORB-v1 is more cost-sensitive because risk sizing produces materially
  larger quantities and commissions.
- Neither strategy survives the wider time-of-day spread proxy.

Assumption-dependent observations:

- Volume-aware results depend directly on the chosen participation and impact
  formula; ORB-v1's fixed 10-share size barely stresses this proxy.
- Latency changes both entry price and the subsequent stop/target lifecycle.
- Conservative stop/limit results depend on the chosen order interpretation,
  trade-through rule, and immediate-or-cancel assumption.
- Costs are direct modeled fill costs; differences in total P&L can be larger
  because altered fills change targets, buying power, quantities, and trade paths.

## Data limitations

OHLCV cannot establish historical bid/ask spread, NBBO, order-book depth, queue
priority, partial-fill sequence, exact impact, broker latency, routing, hidden
liquidity, auction behavior, or precise intrabar price order. Stronger validation
would require quotes and quote sizes, trades, consolidated tape data, and broker
paper-fill logs synchronized to strategy decisions.

These limitations prevent any claim that a model reproduces real fills.

## Paper-trading interpretation

Neither frozen strategy appears suitable for **strategy-driven paper trading** as
a candidate trading edge: both fail modest defensible friction assumptions.

An **engineering-only paper integration test** would have a different purpose:
validating authentication, order-state transitions, calendars, logs, and measured
paper fills without asserting profitability. That engineering work is not part of
this milestone and has not been implemented.
