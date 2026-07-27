from __future__ import annotations

from trading_lab.config.settings import BacktestConfig
from trading_lab.models import (
    Direction,
    Execution,
    ExitReason,
    MarketBar,
    Position,
    Signal,
    Trade,
)
from trading_lab.risk.position_sizing import FixedQuantitySizer
from trading_lab.risk.rules import stop_and_target


class Portfolio:
    """Tracks actual cash plus long assets or short liabilities."""

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.cash = config.starting_capital
        self.position: Position | None = None
        self.trades: list[Trade] = []
        self.executions: list[Execution] = []
        self.equity_curve: list[tuple[object, float]] = []
        self._sizer = FixedQuantitySizer(config.position_size)

    def _fill_price(
        self, reference: float, direction: Direction, is_entry: bool
    ) -> tuple[float, float]:
        adverse_sign = 1 if direction == Direction.LONG else -1
        if not is_entry:
            adverse_sign *= -1
        slippage = reference * self.config.slippage_bps / 10_000
        return reference + adverse_sign * slippage, slippage

    def open(self, signal: Signal) -> bool:
        if self.position is not None:
            raise RuntimeError("cannot open a second position")
        price, slippage = self._fill_price(
            signal.reference_price, signal.direction, True
        )
        commission_per_share = (
            signal.risk_sizing.commission_per_share
            if signal.risk_sizing is not None
            else 0.0
        )
        if signal.risk_sizing is not None:
            if signal.stop_price is None:
                raise ValueError("risk-sized signals require a stop price")
            risk_per_share = abs(price - signal.stop_price)
            if risk_per_share < signal.risk_sizing.minimum_risk_per_share:
                return False
            risk_quantity = int(
                signal.risk_sizing.account_value
                * signal.risk_sizing.risk_fraction
                / risk_per_share
            )
            leverage_quantity = int(
                signal.risk_sizing.max_leverage
                * signal.risk_sizing.account_value
                / price
            )
            available_equity = self.equity(signal.reference_price)
            buying_power_quantity = int(
                max(0.0, available_equity - self.config.trading_fee)
                / (price + commission_per_share)
            )
            quantity = min(
                risk_quantity,
                leverage_quantity,
                buying_power_quantity,
            )
            if quantity <= 0:
                return False
        else:
            quantity = self._sizer.size(price, self.cash)
        entry_fee = (
            self.config.trading_fee + quantity * commission_per_share
        )
        required_buying_power = price * quantity + entry_fee
        if required_buying_power > self.equity(signal.reference_price):
            return False
        if signal.stop_price is not None:
            stop = signal.stop_price
            if signal.reward_risk_multiple is None:
                raise ValueError("custom stops require a reward/risk multiple")
            risk_per_share = abs(price - stop)
            target = (
                price + signal.reward_risk_multiple * risk_per_share
                if signal.direction == Direction.LONG
                else price - signal.reward_risk_multiple * risk_per_share
            )
        else:
            stop, target = stop_and_target(
                price,
                signal.direction,
                self.config.stop_loss_pct,
                self.config.take_profit_pct,
            )
        self.position = Position(
            signal.symbol,
            signal.direction,
            signal.timestamp,
            price,
            quantity,
            stop,
            target,
            entry_fee,
            slippage * quantity,
            commission_per_share,
        )
        notional = price * quantity
        if signal.direction == Direction.LONG:
            self.cash -= notional + entry_fee
        else:
            self.cash += notional - entry_fee
        self.executions.append(
            Execution(
                signal.timestamp,
                price,
                quantity,
                signal.direction,
                entry_fee,
                slippage * quantity,
                True,
            )
        )
        return True

    def close(
        self, bar: MarketBar, reference_price: float, reason: ExitReason
    ) -> Trade:
        if self.position is None:
            raise RuntimeError("no position to close")
        position = self.position
        exit_price, exit_slippage = self._fill_price(
            reference_price, position.direction, False
        )
        multiplier = 1 if position.direction == Direction.LONG else -1
        gross_pnl = (
            (exit_price - position.entry_price) * position.quantity * multiplier
        )
        exit_notional = exit_price * position.quantity
        exit_fee = (
            self.config.trading_fee
            + position.quantity * position.commission_per_share
        )
        if position.direction == Direction.LONG:
            self.cash += exit_notional - exit_fee
        else:
            self.cash -= exit_notional + exit_fee
        fees = position.entry_fee + exit_fee
        trade = Trade(
            position.symbol,
            position.direction,
            position.entry_timestamp,
            position.entry_price,
            bar.timestamp,
            exit_price,
            position.quantity,
            position.stop_price,
            position.take_profit_price,
            fees,
            position.entry_slippage + exit_slippage * position.quantity,
            gross_pnl - fees,
            reason,
        )
        self.executions.append(
            Execution(
                bar.timestamp,
                exit_price,
                position.quantity,
                position.direction,
                exit_fee,
                exit_slippage * position.quantity,
                False,
            )
        )
        self.trades.append(trade)
        self.position = None
        return trade

    def unrealized_pnl(self, close: float) -> float:
        if self.position is None:
            return 0.0
        multiplier = 1 if self.position.direction == Direction.LONG else -1
        return (
            (close - self.position.entry_price)
            * self.position.quantity
            * multiplier
        )

    def equity(self, close: float) -> float:
        if self.position is None:
            return self.cash
        market_value = close * self.position.quantity
        if self.position.direction == Direction.LONG:
            return self.cash + market_value
        return self.cash - market_value

    def mark(self, bar: MarketBar) -> float:
        equity = self.equity(bar.close)
        self.equity_curve.append((bar.timestamp, equity))
        return equity
