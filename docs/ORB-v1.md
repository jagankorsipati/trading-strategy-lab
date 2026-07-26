# ORB-v1 Strategy Specification

ORB-v1 freezes the Opening Range Breakout behavior implemented for Milestone 1.
It is a research specification, not a claim of profitability. Changes to these
rules require a new strategy version.

## Defaults

- Symbol: `QQQ`
- Regular-session calendar: NYSE schedule in `America/New_York`
- Opening range: 09:30 inclusive through 09:45 exclusive (15 minutes)
- Direction: both long and short
- Confirmation: completed-bar close
- Stop loss: 0.5% from the slipped entry price
- Take profit: 1.0% from the slipped entry price
- Maximum entries per session: 1
- Position size: 10 shares
- Starting capital: $10,000
- Fee: $0 per execution
- Slippage: 0 basis points

The configuration and CLI can override the numeric execution/risk assumptions
and select long-only, short-only, or high/low confirmation. Such a run must
report its actual parameters rather than being confused with the defaults above.

## Opening range and breakout

Only calendar-valid regular-session bars are visible to the strategy. Bars whose
start timestamps are at least 09:30 and earlier than 09:45 build the opening
range. Its high is the maximum bar high and its low is the minimum bar low.

After 09:45, the default close-confirmation rule emits:

- a long signal when a completed bar closes strictly above the range high;
- a short signal when a completed bar closes strictly below the range low.

When both directions are enabled, the long condition is evaluated first. The
optional `high_low` confirmation uses a completed bar's high for a long breakout
and low for a short breakout. It does not model an intrabar stop order.

## Signal timing and entry

A signal becomes valid only after its entire candle is complete. It is first
executable at the next available bar's open in the same exchange session. A
signal on the final supplied bar of a session is discarded because no same-
session execution bar exists.

Entry uses the next bar's actual open, not the opening-range boundary or the
signal bar's close. Therefore a gap through the breakout fills at the gapped
opening price. Configured slippage is then applied adversely: upward for a long
entry and downward for a short entry.

## Stops, targets, and OHLC ambiguity

Stops and targets are percentages of the slipped entry price. They are evaluated
on the entry candle and every subsequent candle because entry occurs at the
candle's open.

- A long stop triggers when `low <= stop`; a short stop when `high >= stop`.
- A long target triggers when `high >= target`; a short target when `low <= target`.
- If stop and target occur in the same OHLC candle, the stop wins.
- A stop gapped through uses the worse of the stop and opening price, followed
  by adverse exit slippage.
- A favorably gapped target fills at the target before adverse exit slippage;
  ORB-v1 does not invent price improvement from OHLC data.

The stop-first rule is deliberately conservative because OHLC bars do not reveal
whether the high or low occurred first.

## Costs, sizing, and accounting

Slippage is configured in basis points and applied adversely to every entry and
exit. The configured fixed fee is charged separately on entry and exit and both
fees reduce realized P&L.

Position sizing is a fixed share quantity. An entry requires equity sufficient
for 100% of entry notional plus the entry fee; shorts use the same conservative
notional requirement. Only one position can be open at a time. The maximum-
trades rule counts successfully executed entries, not emitted or rejected
signals, and resets each exchange session.

## End of day

ORB-v1 never holds overnight. The exchange calendar supplies the actual session
close, including scheduled early closes. The position is liquidated at the close
of the final available valid regular-session candle. If the expected final candle
is missing, no candle is manufactured; the last available valid candle is used.
Out-of-session candles cannot affect signals, executions, stops, targets, or
equity.
