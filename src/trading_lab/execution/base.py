from __future__ import annotations

from abc import ABC, abstractmethod

from trading_lab.execution.models import ExecutionContext, ExecutionResult, OrderIntent, OrderType
from trading_lab.models import ExitReason


class ExecutionModel(ABC):
    """Quote-aware extension point for historical fills.

    Implementations receive only information available on the execution bar.
    """

    entry_delay_bars: int = 0

    def order_type(self, *, is_entry: bool, exit_reason: ExitReason | None) -> OrderType:
        return OrderType.MARKET

    @abstractmethod
    def execute(self, intent: OrderIntent, context: ExecutionContext) -> ExecutionResult:
        """Return a typed fill, partial fill, no-fill, or rejection decision."""
