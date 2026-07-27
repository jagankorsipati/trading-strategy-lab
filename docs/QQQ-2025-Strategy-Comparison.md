# QQQ 2025 Untuned Strategy Comparison

This report compares frozen ORB-v1, Reference-ORB-v1, and buy-and-hold on the
validated Alpaca QQQ one-minute dataset for 2025. No parameter was selected or
changed in response to these results.

## Methodology

- ORB-v1 uses its audited `$10,000`, 10-share, 0.5% stop, 1% target defaults.
- Reference-ORB-v1 uses the public notebook's fixed `$25,000` account basis, 1%
  risk budget, 4× sizing formula, 10R target, and `$0.0005/share` commission.
- The conservative portfolio limits Reference-ORB-v1 to 1× available buying
  power. All 248 executed reference trades were capped by this rule.
- Scenario A uses 0 bps configured slippage per execution.
- Scenario B uses 2 bps adverse slippage per execution.
- Scenario C uses 5 bps adverse slippage per execution.
- Reference per-share commissions remain enabled in every scenario. ORB-v1 uses
  its frozen zero-fee assumption.
- Sharpe and Sortino use calendar-session ending equity returns, zero risk-free
  rate, sample standard deviations, and square-root-of-252 annualization.
- Exposure is the sum of trade timestamp spans divided by 96,960 available
  regular-session minutes. Exact intraminute exit exposure is unknowable.

Starting equity differs between strategies, so ending equity and dollar P&L are
not directly comparable. Returns, drawdowns, and risk ratios are more normalized,
but exposure and sizing still differ materially.

## Zero-slippage comparison

| Metric | ORB-v1 | Reference-ORB-v1 | Buy-and-hold |
|---|---:|---:|---:|
| Starting equity | $10,000.00 | $25,000.00 | $10,000.00 |
| Total return | 3.46% | 2.72% | 19.43% |
| Ending equity | $10,346.12 | $25,679.14 | $11,943.42 |
| Total P&L | $346.12 | $679.14 | $1,943.42 |
| Trades | 250 | 248 | N/A |
| Win rate | 44.00% | 27.02% | N/A |
| Profit factor | 1.108 | 1.064 | N/A |
| Maximum drawdown | 3.04% | 7.15% | 25.44% |
| Average winner | $32.17 | $169.21 | N/A |
| Average loser | -$22.80 | -$58.88 | N/A |
| Long P&L | -$23.86 | -$206.49 | N/A |
| Short P&L | $369.98 | $885.63 | N/A |
| Average holding time | 209.40 min | 129.82 min | N/A |
| Timestamp-span exposure | 53.99% | 33.20% | 100% |
| Daily Sharpe | 0.746 | 0.365 | 0.882 |
| Daily Sortino | 2.660 | 1.466 | 1.158 |
| Return / max drawdown | 1.140 | 0.380 | 0.764 |

Buy-and-hold assumes fractional shares, entry at the January 2 regular-session
open (`$514.325`), exit at the December 31 final regular-session close
(`$614.28`), no fees/slippage, and no dividends. It has continuous overnight
exposure and is not economically equivalent to an intraday strategy.

## Execution-friction sensitivity

| Strategy | Scenario | Return | Ending equity | P&L | Win rate | Profit factor | Max DD | Recorded slippage cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ORB-v1 | A: 0 bps | 3.46% | $10,346.12 | $346.12 | 44.00% | 1.108 | 3.04% | $0.00 |
| ORB-v1 | B: 2 bps | -1.91% | $9,808.90 | -$191.10 | 42.40% | 0.944 | 6.79% | $548.78 |
| ORB-v1 | C: 5 bps | -9.69% | $9,030.81 | -$969.19 | 39.20% | 0.747 | 11.47% | $1,372.05 |
| Reference | A: 0 bps | 2.72% | $25,679.14 | $679.14 | 27.02% | 1.064 | 7.15% | $0.00 |
| Reference | B: 2 bps | -5.95% | $23,511.31 | -$1,488.69 | 26.21% | 0.876 | 11.71% | $2,359.68 |
| Reference | C: 5 bps | -18.16% | $20,459.20 | -$4,540.80 | 23.39% | 0.670 | 21.32% | $5,525.87 |

Recorded slippage cost is the sum of modeled per-fill adverse price adjustments
times quantity. Total P&L differences also reflect changed stop distances,
targets, quantities, and exit paths, so they need not equal that cost.

Reference commissions totaled `$11.33`, `$10.87`, and `$10.22` in scenarios A,
B, and C respectively as friction changed executed quantities. ORB-v1 configured
fees remained zero.

## Reference diagnostics

- January 13 and March 11 were skipped because the first five-minute candle was a
  doji after rounding open and close to two decimals.
- The other 248 sessions executed exactly one trade.
- 120 reference trades were long and 128 were short in scenario A.
- Scenario A exits: 180 stop, 8 target, and 60 end-of-day.
- The notebook formula averaged 163.60 shares, but conservative executed quantity
  averaged 45.69 shares (range 39–61).
- Every reference trade was constrained by 1× buying power rather than the
  notebook's theoretical 4× allowance. This is the largest reproduction gap.
- Reference results are especially sensitive to slippage because quantities are
  much larger than ORB-v1's fixed 10 shares.

## Interpretation limits

This is a single-period diagnostic. It does not establish future profitability.
The reference implementation intentionally differs from the notebook where the
notebook ignores risk during the entry candle, assumes exact stop fills through
gaps, lacks an exchange calendar, and relies on leverage not supported by the
conservative portfolio.
