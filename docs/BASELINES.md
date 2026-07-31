# Frozen research baselines

- Release designation: **v0.1.0-research-foundation**
- Project version: **0.1.0**

The strategies below are immutable historical research baselines. Experiments
must use a new strategy and version name, such as `ORB-v2`, `ORB-Volume-v1`, or
`ORB-Regime-v1`. Changes to rules, defaults, execution, risk, sizing, direction,
trade limits, commissions, or slippage assumptions must never be made silently
under either baseline name.

Historical results are descriptive and do not support claims of future
profitability.

## ORB-v1

- Status: **FROZEN**
- Release: `v0.1.0-research-foundation`
- Source: `src/trading_lab/strategies/orb.py`
- Specification: [ORB-v1](ORB-v1.md)
- Starting capital: $10,000
- Position sizing: fixed 10 shares, subject to conservative buying-power checks
- Opening range: 09:30–09:44:59 Eastern; 15 one-minute bars
- Direction: long or short; close-based breakout confirmation
- Execution: completed breakout bar emits a signal; entry is first executable at
  the next same-session bar open
- Risk: 0.5% stop and 1.0% target from modeled entry; one trade per session
- Ambiguous bars: stop is applied before target
- Gaps: adverse stop gaps use the worse bar open; favorable target gaps receive
  no invented improvement
- Friction: configurable adverse entry/exit slippage; zero fixed fee in the
  frozen research runs
- Historical evaluation: QQQ one-minute data, 2018–2025
- Purpose: stable benchmark for evaluating future research methods

Continuous 2018–2025 results:

| Scenario | Return | Profit factor | Maximum drawdown |
|---:|---:|---:|---:|
| 0 bps | 19.64% | 1.12 | 4.08% |
| 2 bps | -4.46% | 0.97 | 7.66% |
| 5 bps | -41.52% | 0.78 | 41.68% |

## Reference-ORB-v1

- Status: **FROZEN**
- Release: `v0.1.0-research-foundation`
- Source: `src/trading_lab/strategies/reference_orb.py`
- Specification: [Reference-ORB-v1](Reference-ORB-v1.md)
- Starting capital: $25,000
- Position sizing: risks 1% of the fixed $25,000 reference account subject to a
  4× notional cap, minimum $0.05 per-share risk, integer shares, and conservative
  portfolio buying power
- Setup: direction of the complete first five-minute candle
- Execution: signal after 09:34 bar completion; entry at the 09:35 bar open
- Risk: opposite end of the first five-minute candle as stop, 10R target, and
  exactly one trade per session
- Ambiguous bars and gaps: same conservative engine policy as ORB-v1
- Friction: $0.0005 per share on entry and exit plus configurable adverse
  entry/exit slippage
- Historical evaluation: QQQ one-minute data, 2018–2025
- Purpose: stable interpretation of the external reference setup for comparative
  research

Continuous 2018–2025 results:

| Scenario | Return | Profit factor | Maximum drawdown |
|---:|---:|---:|---:|
| 0 bps | 83.46% | 1.15 | 11.83% |
| 2 bps | -16.61% | 0.96 | 32.10% |
| 5 bps | -74.30% | 0.76 | 76.15% |

Neither baseline survives modest modeled friction consistently. These baselines
exist to make future comparisons reproducible, not to represent deployable or
profitable trading systems.
