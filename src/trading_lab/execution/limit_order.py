from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_lab.execution.base import ExecutionModel
from trading_lab.execution.models import (
    ExecutionContext, ExecutionCostBreakdown, ExecutionResult, ExecutionStatus,
    Fill, OrderIntent, OrderSide, OrderType, RejectionReason,
)


class LimitFillPolicy(StrEnum):
    TOUCH_FILLS = "touch_fills"
    TRADE_THROUGH_REQUIRED = "trade_through_required"
    CONSERVATIVE_NO_FILL_ON_AMBIGUITY = "conservative_no_fill_on_ambiguity"


@dataclass(frozen=True)
class LimitOrderExecutionConfig:
    fill_policy: LimitFillPolicy = LimitFillPolicy.CONSERVATIVE_NO_FILL_ON_AMBIGUITY
    adverse_bps: float = 0.0

    def __post_init__(self) -> None:
        if self.adverse_bps < 0:
            raise ValueError("adverse fill penalty cannot be negative")


class LimitOrderExecutionModel(ExecutionModel):
    def __init__(self, config: LimitOrderExecutionConfig | None = None) -> None:
        self.config = config or LimitOrderExecutionConfig()

    def _rejected(self, intent, reason, explanation):
        return ExecutionResult(
            ExecutionStatus.NOT_FILLED, intent.requested_quantity, 0,
            intent.requested_quantity, None, reason, explanation,
        )

    def order_type(self, *, is_entry: bool, exit_reason) -> OrderType:
        if is_entry or (exit_reason is not None and exit_reason.value == "STOP_LOSS"):
            return OrderType.STOP
        if exit_reason is not None and exit_reason.value == "TAKE_PROFIT":
            return OrderType.LIMIT
        return OrderType.MARKET

    def execute(self, intent: OrderIntent, context: ExecutionContext) -> ExecutionResult:
        bar = context.bar
        if intent.order_type == OrderType.MARKET:
            executable = True
            base_price = intent.reference_price
        elif intent.order_type == OrderType.LIMIT:
            level = float(intent.limit_price)
            touched = bar.low <= level if intent.side == OrderSide.BUY else bar.high >= level
            through = bar.low < level if intent.side == OrderSide.BUY else bar.high > level
            if self.config.fill_policy == LimitFillPolicy.TOUCH_FILLS:
                executable = touched
            else:
                executable = through
            if not executable:
                reason = RejectionReason.AMBIGUOUS_BAR if touched else RejectionReason.PRICE_NOT_REACHED
                return self._rejected(intent, reason, "limit did not trade through under conservative policy")
            # Marketable limits use the bar open when it is no worse; otherwise
            # the limit level is the only defensible OHLC fill reference.
            base_price = min(bar.open, level) if intent.side == OrderSide.BUY else max(bar.open, level)
        elif intent.order_type == OrderType.STOP:
            level = float(intent.stop_price)
            touched = bar.high >= level if intent.side == OrderSide.BUY else bar.low <= level
            through = bar.high > level if intent.side == OrderSide.BUY else bar.low < level
            executable = touched if self.config.fill_policy == LimitFillPolicy.TOUCH_FILLS else through
            if not executable:
                reason = RejectionReason.AMBIGUOUS_BAR if touched else RejectionReason.PRICE_NOT_REACHED
                return self._rejected(intent, reason, "stop did not trade through under conservative policy")
            # A stop gapped through cannot improve on the first executable open.
            base_price = max(bar.open, level) if intent.side == OrderSide.BUY else min(bar.open, level)
        else:  # pragma: no cover - enum validation makes this defensive
            raise ValueError(f"unsupported order type: {intent.order_type}")
        quantity = intent.requested_quantity
        penalty = base_price * self.config.adverse_bps / 10_000
        sign = 1 if intent.side == OrderSide.BUY else -1
        costs = ExecutionCostBreakdown(
            fixed_slippage=penalty * quantity,
            commission=intent.fixed_commission + intent.commission_per_share * quantity,
        )
        return ExecutionResult(
            ExecutionStatus.FULLY_FILLED, quantity, quantity, 0,
            Fill(intent.timestamp, intent.reference_price, base_price + sign * penalty, quantity, costs),
            None, f"{intent.order_type.value} executed under {self.config.fill_policy.value}",
        )
