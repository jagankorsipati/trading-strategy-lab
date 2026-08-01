from __future__ import annotations

from dataclasses import dataclass

from trading_lab.execution.base import ExecutionModel
from trading_lab.execution.models import (
    ExecutionContext, ExecutionCostBreakdown, ExecutionResult, ExecutionStatus,
    Fill, OrderIntent, OrderSide,
)


@dataclass(frozen=True)
class FixedBpsExecutionConfig:
    slippage_bps: float = 0.0

    def __post_init__(self) -> None:
        if self.slippage_bps < 0:
            raise ValueError("slippage cannot be negative")


class FixedBpsExecutionModel(ExecutionModel):
    def __init__(self, config: FixedBpsExecutionConfig | None = None) -> None:
        self.config = config or FixedBpsExecutionConfig()

    def execute(self, intent: OrderIntent, context: ExecutionContext) -> ExecutionResult:
        per_share = intent.reference_price * self.config.slippage_bps / 10_000
        sign = 1 if intent.side == OrderSide.BUY else -1
        price = intent.reference_price + sign * per_share
        quantity = intent.requested_quantity
        costs = ExecutionCostBreakdown(
            fixed_slippage=per_share * quantity,
            commission=intent.fixed_commission + intent.commission_per_share * quantity,
        )
        return ExecutionResult(
            ExecutionStatus.FULLY_FILLED, quantity, quantity, 0,
            Fill(intent.timestamp, intent.reference_price, price, quantity, costs),
            None, f"market fill with {self.config.slippage_bps:g} bps adverse slippage",
        )
