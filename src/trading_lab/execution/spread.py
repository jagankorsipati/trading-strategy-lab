from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_lab.execution.base import ExecutionModel
from trading_lab.execution.models import (
    ExecutionContext, ExecutionCostBreakdown, ExecutionResult, ExecutionStatus,
    Fill, OrderIntent, OrderSide,
)


class SpreadMode(StrEnum):
    CONSTANT = "constant"
    TIME_OF_DAY = "time_of_day"


@dataclass(frozen=True)
class SpreadExecutionConfig:
    mode: SpreadMode = SpreadMode.CONSTANT
    constant_spread_bps: float = 2.0
    open_spread_bps: float = 4.0
    middle_spread_bps: float = 1.5
    close_spread_bps: float = 2.5
    open_window_minutes: int = 30
    close_window_minutes: int = 30
    market_impact_bps: float = 0.0
    latency_penalty_bps: float = 0.0

    def __post_init__(self) -> None:
        numeric = (
            self.constant_spread_bps, self.open_spread_bps, self.middle_spread_bps,
            self.close_spread_bps, self.market_impact_bps, self.latency_penalty_bps,
        )
        if any(value < 0 for value in numeric):
            raise ValueError("spread and penalties cannot be negative")
        if self.open_window_minutes < 0 or self.close_window_minutes < 0:
            raise ValueError("session windows cannot be negative")


class SpreadBasedExecutionModel(ExecutionModel):
    def __init__(self, config: SpreadExecutionConfig | None = None) -> None:
        self.config = config or SpreadExecutionConfig()

    def spread_bps(self, context: ExecutionContext) -> float:
        if self.config.mode == SpreadMode.CONSTANT:
            return self.config.constant_spread_bps
        if context.session is None:
            raise ValueError("time-of-day spread requires a trading session")
        elapsed = (context.bar.timestamp - context.session.market_open).total_seconds() / 60
        remaining = (context.session.market_close - context.bar.timestamp).total_seconds() / 60
        if elapsed < self.config.open_window_minutes:
            return self.config.open_spread_bps
        if remaining <= self.config.close_window_minutes:
            return self.config.close_spread_bps
        return self.config.middle_spread_bps

    def execute(self, intent: OrderIntent, context: ExecutionContext) -> ExecutionResult:
        quantity = intent.requested_quantity
        half_spread = intent.reference_price * self.spread_bps(context) / 20_000
        impact = intent.reference_price * self.config.market_impact_bps / 10_000
        latency = (
            intent.reference_price * self.config.latency_penalty_bps
            * context.delayed_bars / 10_000
        )
        per_share = half_spread + impact + latency
        sign = 1 if intent.side == OrderSide.BUY else -1
        costs = ExecutionCostBreakdown(
            spread=half_spread * quantity,
            market_impact=impact * quantity,
            latency=latency * quantity,
            commission=intent.fixed_commission + intent.commission_per_share * quantity,
        )
        return ExecutionResult(
            ExecutionStatus.FULLY_FILLED, quantity, quantity, 0,
            Fill(intent.timestamp, intent.reference_price, intent.reference_price + sign * per_share, quantity, costs),
            None, f"spread proxy {self.spread_bps(context):g} bps",
        )
