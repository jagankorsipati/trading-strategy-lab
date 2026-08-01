# Execution sensitivity: reference-orb-v1

These deterministic OHLCV models are assumptions, not reconstructed broker fills. No scenario is selected as a winner.

| Scenario | Return | P&L | Trades attempted | Full | Partial | Unfilled | Rejected | PF | Max DD | Total cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed-0bps | 83.46% | $20,864.79 | 1995 | 1995 | 0 | 0 | 0 | 1.15 | 11.83% | $239.29 |
| fixed-2bps | -16.61% | $-4,152.10 | 1998 | 1998 | 0 | 0 | 0 | 0.96 | 32.10% | $19,305.21 |
| fixed-5bps | -74.30% | $-18,574.86 | 1998 | 1998 | 0 | 0 | 0 | 0.76 | 76.15% | $28,655.35 |
| constant-spread | -16.61% | $-4,152.10 | 1998 | 1998 | 0 | 0 | 0 | 0.96 | 32.10% | $19,305.21 |
| time-of-day-spread | -32.96% | $-8,240.13 | 1998 | 1998 | 0 | 0 | 0 | 0.92 | 44.19% | $22,676.15 |
| volume-aware | 69.78% | $17,446.21 | 1995 | 1660 | 335 | 0 | 0 | 1.14 | 12.02% | $880.19 |
| one-bar-latency | 47.56% | $11,890.74 | 1962 | 1962 | 0 | 0 | 0 | 1.10 | 14.80% | $6,205.00 |
| conservative-orders | 101.26% | $25,314.87 | 1995 | 1919 | 0 | 76 | 0 | 1.18 | 10.52% | $242.66 |

The cache contains OHLCV rather than historical quotes or order-book events. Spread, depth, queue priority, impact, latency, routing, and intrabar sequence cannot be recovered exactly. Historical performance does not establish future profitability.
