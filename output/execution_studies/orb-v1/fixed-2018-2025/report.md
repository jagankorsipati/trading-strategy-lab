# Execution sensitivity: orb-v1

These deterministic OHLCV models are assumptions, not reconstructed broker fills. No scenario is selected as a winner.

| Scenario | Return | P&L | Trades attempted | Full | Partial | Unfilled | Rejected | PF | Max DD | Total cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed-0bps | 19.64% | $1,963.82 | 2007 | 2007 | 0 | 0 | 0 | 1.12 | 4.08% | $0.00 |
| fixed-2bps | -4.46% | $-446.41 | 2007 | 2007 | 0 | 0 | 0 | 0.97 | 7.66% | $2,639.64 |
| fixed-5bps | -41.52% | $-4,151.76 | 19456 | 1938 | 0 | 0 | 17518 | 0.78 | 41.68% | $6,176.07 |
| constant-spread | -4.46% | $-446.41 | 2007 | 2007 | 0 | 0 | 0 | 0.97 | 7.66% | $2,639.64 |
| time-of-day-spread | -4.93% | $-493.30 | 2007 | 2007 | 0 | 0 | 0 | 0.97 | 7.65% | $2,563.80 |
| volume-aware | 19.58% | $1,958.50 | 2007 | 2007 | 0 | 0 | 0 | 1.12 | 4.08% | $8.12 |
| one-bar-latency | 13.26% | $1,325.77 | 2007 | 2007 | 0 | 0 | 0 | 1.08 | 5.00% | $659.89 |
| conservative-orders | 23.17% | $2,316.81 | 2109 | 2005 | 0 | 104 | 0 | 1.14 | 4.01% | $0.00 |

The cache contains OHLCV rather than historical quotes or order-book events. Spread, depth, queue priority, impact, latency, routing, and intrabar sequence cannot be recovered exactly. Historical performance does not establish future profitability.
