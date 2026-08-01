from __future__ import annotations

from dataclasses import dataclass
from math import floor

from trading_lab.execution.base import ExecutionModel
from trading_lab.execution.models import (
    ExecutionContext, ExecutionCostBreakdown, ExecutionResult, ExecutionStatus,
    Fill, OrderIntent, OrderSide, RejectionReason,
)


@dataclass(frozen=True)
class VolumeAwareExecutionConfig:
    maximum_participation_rate: float = 0.01
    minimum_bar_volume: int = 1_000
    impact_coefficient_bps: float = 10.0
    maximum_impact_bps: float = 20.0
    allow_partial_fills: bool = True

    def __post_init__(self) -> None:
        if not 0 < self.maximum_participation_rate <= 1:
            raise ValueError("maximum participation rate must be in (0, 1]")
        if self.minimum_bar_volume < 0:
            raise ValueError("minimum bar volume cannot be negative")
        if self.impact_coefficient_bps < 0 or self.maximum_impact_bps < 0:
            raise ValueError("impact assumptions cannot be negative")


class VolumeAwareExecutionModel(ExecutionModel):
    """OHLCV liquidity proxy; candle volume is not assumed available at one price."""

    def __init__(self, config: VolumeAwareExecutionConfig | None = None) -> None:
        self.config = config or VolumeAwareExecutionConfig()

    def execute(self, intent: OrderIntent, context: ExecutionContext) -> ExecutionResult:
        requested = intent.requested_quantity
        volume = context.bar.volume
        if intent.is_entry and volume < self.config.minimum_bar_volume:
            return ExecutionResult(
                ExecutionStatus.REJECTED, requested, 0, requested, None,
                RejectionReason.MINIMUM_VOLUME, "bar volume is below configured minimum",
            )
        # Exits remain full-or-unfilled so a partial exit cannot weaken the
        # no-overnight invariant or create an untracked residual position.
        availability = floor(volume * self.config.maximum_participation_rate)
        if intent.is_entry and availability < requested:
            if not self.config.allow_partial_fills or availability <= 0:
                return ExecutionResult(
                    ExecutionStatus.REJECTED, requested, 0, requested, None,
                    RejectionReason.INSUFFICIENT_LIQUIDITY,
                    "modeled available quantity is below requested quantity",
                )
            filled = availability
            status = ExecutionStatus.PARTIALLY_FILLED
        else:
            filled = requested
            status = ExecutionStatus.FULLY_FILLED
        participation = filled / volume if volume > 0 else 1.0
        impact_bps = self.config.impact_coefficient_bps * participation
        if impact_bps > self.config.maximum_impact_bps:
            if not intent.is_entry:
                impact_bps = self.config.maximum_impact_bps
            else:
                return ExecutionResult(
                    ExecutionStatus.REJECTED, requested, 0, requested, None,
                    RejectionReason.IMPACT_LIMIT, "modeled impact exceeds configured maximum",
                )
        impact_per_share = intent.reference_price * impact_bps / 10_000
        sign = 1 if intent.side == OrderSide.BUY else -1
        costs = ExecutionCostBreakdown(
            market_impact=impact_per_share * filled,
            commission=intent.fixed_commission + intent.commission_per_share * filled,
        )
        return ExecutionResult(
            status, requested, filled, requested - filled,
            Fill(intent.timestamp, intent.reference_price,
                 intent.reference_price + sign * impact_per_share, filled, costs),
            None,
            f"{participation:.6f} participation; linear impact {impact_bps:.6f} bps",
        )
