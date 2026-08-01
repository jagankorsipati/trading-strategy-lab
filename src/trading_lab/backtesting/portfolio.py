from __future__ import annotations

from trading_lab.config.settings import BacktestConfig
from trading_lab.execution import (
    ExecutionContext,
    ExecutionModel,
    ExecutionResult,
    ExecutionStatus,
    FixedBpsExecutionConfig,
    FixedBpsExecutionModel,
    OrderIntent,
    OrderSide,
    OrderType,
    RejectionReason,
)
from trading_lab.market.calendar import TradingSession
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

    def __init__(
        self,
        config: BacktestConfig,
        execution_model: ExecutionModel | None = None,
    ) -> None:
        self.config = config
        self.cash = config.starting_capital
        self.position: Position | None = None
        self.trades: list[Trade] = []
        self.executions: list[Execution] = []
        self.order_results: list[ExecutionResult] = []
        self.order_intents: list[OrderIntent | None] = []
        self.equity_curve: list[tuple[object, float]] = []
        self._sizer = FixedQuantitySizer(config.position_size)
        self.execution_model = execution_model or FixedBpsExecutionModel(
            FixedBpsExecutionConfig(config.slippage_bps)
        )

    @staticmethod
    def _side(direction: Direction, is_entry: bool) -> OrderSide:
        if direction == Direction.LONG:
            return OrderSide.BUY if is_entry else OrderSide.SELL
        return OrderSide.SELL if is_entry else OrderSide.BUY

    @staticmethod
    def _fallback_bar(signal: Signal) -> MarketBar:
        price = signal.reference_price
        return MarketBar(signal.timestamp, price, price, price, price, 1_000_000_000)

    def _intent(
        self,
        *,
        signal: Signal,
        quantity: int,
        is_entry: bool,
        reference_price: float,
        exit_reason: ExitReason | None,
        order_level: float | None,
        commission_per_share: float,
    ) -> OrderIntent:
        order_type = self.execution_model.order_type(
            is_entry=is_entry, exit_reason=exit_reason
        )
        return OrderIntent(
            timestamp=signal.timestamp,
            side=self._side(signal.direction, is_entry),
            order_type=order_type,
            requested_quantity=quantity,
            reference_price=reference_price,
            limit_price=order_level if order_type == OrderType.LIMIT else None,
            stop_price=order_level if order_type == OrderType.STOP else None,
            is_entry=is_entry,
            commission_per_share=commission_per_share,
            fixed_commission=self.config.trading_fee,
        )

    def _append_execution(
        self, signal: Signal, result: ExecutionResult, *, is_entry: bool
    ) -> None:
        fill = result.fill
        if fill is None:
            return
        costs = fill.costs
        self.executions.append(
            Execution(
                signal.timestamp,
                fill.price,
                fill.quantity,
                signal.direction,
                costs.commission,
                costs.fixed_slippage,
                is_entry,
                reference_price=fill.reference_price,
                spread_cost=costs.spread,
                impact_cost=costs.market_impact,
                latency_cost=costs.latency,
                requested_quantity=result.requested_quantity,
                unfilled_quantity=result.unfilled_quantity,
                status=result.status.value,
                explanation=result.explanation,
            )
        )

    def open(
        self,
        signal: Signal,
        bar: MarketBar | None = None,
        session: TradingSession | None = None,
        *,
        order_reference_price: float | None = None,
        delayed_bars: int = 0,
    ) -> bool:
        if self.position is not None:
            raise RuntimeError("cannot open a second position")
        execution_bar = bar or self._fallback_bar(signal)
        context = ExecutionContext(execution_bar, session, delayed_bars=delayed_bars)
        commission_per_share = (
            signal.risk_sizing.commission_per_share
            if signal.risk_sizing is not None
            else 0.0
        )
        level = order_reference_price or signal.reference_price
        provisional_intent = self._intent(
            signal=signal,
            quantity=1,
            is_entry=True,
            reference_price=signal.reference_price,
            exit_reason=None,
            order_level=level,
            commission_per_share=commission_per_share,
        )
        provisional = self.execution_model.execute(provisional_intent, context)
        price = (
            provisional.fill.price
            if provisional.fill is not None
            else signal.reference_price
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
        intent = self._intent(
            signal=signal,
            quantity=quantity,
            is_entry=True,
            reference_price=signal.reference_price,
            exit_reason=None,
            order_level=level,
            commission_per_share=commission_per_share,
        )
        result = self.execution_model.execute(intent, context)
        self.order_intents.append(intent)
        self.order_results.append(result)
        if result.fill is None:
            return False
        fill = result.fill
        quantity = fill.quantity
        price = fill.price
        entry_fee = fill.costs.commission
        required_buying_power = price * quantity + entry_fee
        if required_buying_power > self.equity(signal.reference_price):
            self.order_results[-1] = ExecutionResult(
                ExecutionStatus.REJECTED,
                result.requested_quantity,
                0,
                result.requested_quantity,
                None,
                RejectionReason.BUYING_POWER,
                "insufficient portfolio buying power",
            )
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
            fill.costs.price_cost,
            commission_per_share,
        )
        notional = price * quantity
        if signal.direction == Direction.LONG:
            self.cash -= notional + entry_fee
        else:
            self.cash += notional - entry_fee
        self._append_execution(signal, result, is_entry=True)
        return True

    def reject_pending(self, reason: RejectionReason, explanation: str) -> None:
        quantity = self.config.position_size
        self.order_intents.append(None)
        self.order_results.append(
            ExecutionResult(
                ExecutionStatus.REJECTED,
                quantity,
                0,
                quantity,
                None,
                reason,
                explanation,
            )
        )

    def close(
        self,
        bar: MarketBar,
        reference_price: float,
        reason: ExitReason,
        session: TradingSession | None = None,
    ) -> Trade | None:
        if self.position is None:
            raise RuntimeError("no position to close")
        position = self.position
        signal = Signal(
            position.symbol,
            bar.timestamp,
            position.direction,
            reference_price,
        )
        context = ExecutionContext(bar, session, exit_reason=reason)
        intent = self._intent(
            signal=signal,
            quantity=position.quantity,
            is_entry=False,
            reference_price=reference_price,
            exit_reason=reason,
            order_level=reference_price,
            commission_per_share=position.commission_per_share,
        )
        result = self.execution_model.execute(intent, context)
        self.order_intents.append(intent)
        self.order_results.append(result)
        if result.fill is None:
            return None
        fill = result.fill
        exit_price = fill.price
        multiplier = 1 if position.direction == Direction.LONG else -1
        gross_pnl = (
            (exit_price - position.entry_price) * position.quantity * multiplier
        )
        exit_notional = exit_price * position.quantity
        exit_fee = fill.costs.commission
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
            position.entry_slippage + fill.costs.price_cost,
            gross_pnl - fees,
            reason,
        )
        self._append_execution(signal, result, is_entry=False)
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
