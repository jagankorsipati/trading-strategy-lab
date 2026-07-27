# Reference-ORB-v1 Strategy Specification

Reference-ORB-v1 is a separate research strategy based on the executable notebook
in [`alfredoberlose/ORB-Day_Trading_Strategy-QQQ`](https://github.com/alfredoberlose/ORB-Day_Trading_Strategy-QQQ).
It does not modify or replace ORB-v1.

## Repository behavior

The repository notebook:

- downloads one-minute QQQ bars and converts their UTC index to US/Eastern;
- filters data with pandas `between_time("09:30", "16:00")`;
- skips a date when fewer than 80 source rows are present;
- resamples each date into five-minute OHLCV candles;
- uses the first candle, labeled 09:30 and covering 09:30–09:34, as the setup;
- skips the date when first-candle open and close are equal after rounding both
  to two decimals;
- goes long when the first candle closes above its open, otherwise short;
- assigns entry to the second five-minute candle's open;
- places a long stop at the first candle's low or a short stop at its high;
- skips risk per share (`R`) below $0.05;
- sets the target to entry plus/minus 10R;
- risks 1% of a fixed `$25,000` `account_value`;
- caps shares at four times that fixed account value divided by entry price;
- truncates fractional shares with `int`;
- evaluates exits only from the third five-minute candle onward;
- checks stop before target, so the stop wins when both occur in one candle;
- exits at the final five-minute close when neither stop nor target is hit;
- permits at most one trade per date;
- charges `$0.0005` per share on entry and again on exit;
- does not model slippage or gap-through-stop degradation.

The notebook never updates `account_value` after a trade, so both its 1% risk
budget and 4× leverage ceiling remain based on `$25,000`, not compounded equity.

## Ambiguities and unusual details

The README says entry occurs at the second candle's open, which matches the code.
However, the code then scans `candles.iloc[2:]`: it ignores all stop and target
touches during the second candle even though the position is considered open.
This creates survivorship/look-ahead optimism.

Pandas `between_time("09:30", "16:00")` includes a bar starting at 16:00 when one
exists, while the repository does not use an exchange calendar. Holidays,
scheduled early closes, incomplete opening candles, and extended-session
boundaries are therefore handled only incidentally by available rows.

The notebook fills stops exactly at the stop after gaps and fills targets exactly
at target. It does not distinguish which price was first available after a gap.
It also embeds placeholder credentials directly in a notebook cell; this project
continues to use environment variables only.

## Our modeling interpretation

Reference-ORB-v1 preserves the economic setup while retaining this project's
audited correctness rules:

1. Only exchange-calendar regular-session one-minute bars are visible.
2. The first five consecutive minutes from the actual session open are aggregated
   deterministically into the setup candle.
3. Once the 09:34 bar completes, direction is known and the signal becomes
   executable at the 09:35 one-minute bar's open.
4. Stop and target checks begin immediately on that entry minute. We do **not**
   ignore the second five-minute candle.
5. The stop wins if both stop and target occur in one OHLC bar.
6. Adverse gaps through a stop fill from the worse opening price; favorable target
   gaps do not receive invented price improvement.
7. Configured adverse slippage applies to entries and exits.
8. The repository's `$0.0005/share` commission applies on both sides.
9. The repository quantity is calculated from 1% of fixed `$25,000`, a minimum
   $0.05 stop distance, and the 4× notional ceiling.
10. The existing portfolio requires 100% notional buying power. If the repository
    quantity exceeds that amount, quantity is capped to available 1× buying power
    rather than weakening cash/margin accounting. This means exact 4× leverage is
    intentionally not reproduced.
11. A position exits on the final available valid regular-session bar, including
    calendar early closes.

The notebook's `len(group) < 80` test uses knowledge of the completed future
session before deciding whether to enter at 09:35. Our interpretation does not
introduce that look-ahead gate: it requires a complete first five-minute candle
and relies on the separate data-quality audit for session completeness. The
validated 2025 dataset has complete coverage, so this difference does not affect
the reported comparison.

Exit detection uses the underlying one-minute bars rather than waiting for
completed five-minute candles. This preserves more available ordering detail
while retaining the same stop-first policy when a single one-minute candle
contains both levels.

These differences favor execution correctness over mechanically reproducing
optimistic notebook behavior. Results from Reference-ORB-v1 are therefore a
conservative interpretation, not byte-for-byte replication of the notebook.
