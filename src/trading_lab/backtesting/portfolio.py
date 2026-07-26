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
    """Tracks fills and mark-to-market equity using collateral-neutral cash."""

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

    def open(self, signal: Signal) -> None:
        if self.position is not None:
            raise RuntimeError("cannot open a second position")
        price, slippage = self._fill_price(
            signal.reference_price, signal.direction, True
        )
        quantity = self._sizer.size(price, self.cash)
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
            self.config.trading_fee,
            slippage * quantity,
        )
        self.cash -= self.config.trading_fee
        self.executions.append(
            Execution(
                signal.timestamp,
                price,
                quantity,
                signal.direction,
                self.config.trading_fee,
                slippage * quantity,
                True,
            )
        )

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
        self.cash += gross_pnl - self.config.trading_fee
        fees = position.entry_fee + self.config.trading_fee
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
                self.config.trading_fee,
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

    def mark(self, bar: MarketBar) -> float:
        equity = self.cash + self.unrealized_pnl(bar.close)
        self.equity_curve.append((bar.timestamp, equity))
        return equity
