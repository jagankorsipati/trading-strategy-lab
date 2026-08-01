from __future__ import annotations

from dataclasses import dataclass

from trading_lab.execution.base import ExecutionModel
from trading_lab.execution.fixed_bps import FixedBpsExecutionModel
from trading_lab.execution.models import (
    ExecutionContext, ExecutionCostBreakdown, ExecutionResult, Fill, OrderIntent, OrderSide,
)


@dataclass(frozen=True)
class LatencyExecutionConfig:
    delay_bars: int = 1
    adverse_bps_per_delayed_bar: float = 0.0
    reject_at_session_end: bool = True

    def __post_init__(self) -> None:
        if self.delay_bars < 0:
            raise ValueError("latency cannot be negative")
        if self.adverse_bps_per_delayed_bar < 0:
            raise ValueError("latency penalty cannot be negative")
        if self.delay_bars and not self.reject_at_session_end:
            raise ValueError("delayed execution requires a session-end rejection policy")


class LatencyExecutionModel(ExecutionModel):
    def __init__(
        self,
        config: LatencyExecutionConfig | None = None,
        delegate: ExecutionModel | None = None,
    ) -> None:
        self.config = config or LatencyExecutionConfig()
        self.delegate = delegate or FixedBpsExecutionModel()
        self.entry_delay_bars = self.config.delay_bars

    def execute(self, intent: OrderIntent, context: ExecutionContext) -> ExecutionResult:
        result = self.delegate.execute(intent, context)
        if result.fill is None or context.delayed_bars <= 0:
            return result
        fill = result.fill
        per_share = (
            intent.reference_price * self.config.adverse_bps_per_delayed_bar
            * context.delayed_bars / 10_000
        )
        sign = 1 if intent.side == OrderSide.BUY else -1
        costs = ExecutionCostBreakdown(
            spread=fill.costs.spread,
            fixed_slippage=fill.costs.fixed_slippage,
            market_impact=fill.costs.market_impact,
            latency=fill.costs.latency + per_share * fill.quantity,
            commission=fill.costs.commission,
        )
        delayed_fill = Fill(
            fill.timestamp, fill.reference_price, fill.price + sign * per_share,
            fill.quantity, costs,
        )
        return ExecutionResult(
            result.status, result.requested_quantity, result.filled_quantity,
            result.unfilled_quantity, delayed_fill, result.rejection_reason,
            result.explanation + f"; delayed {context.delayed_bars} bar(s)",
        )
