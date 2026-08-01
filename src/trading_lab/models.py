from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


class BreakoutConfirmation(StrEnum):
    CLOSE = "close"
    HIGH_LOW = "high_low"


class ExitReason(StrEnum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    END_OF_DAY = "END_OF_DAY"


@dataclass(frozen=True)
class MarketBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class RiskSizing:
    account_value: float
    risk_fraction: float
    max_leverage: float
    minimum_risk_per_share: float = 0.0
    commission_per_share: float = 0.0


@dataclass(frozen=True)
class Signal:
    symbol: str
    timestamp: datetime
    direction: Direction
    reference_price: float
    stop_price: float | None = None
    reward_risk_multiple: float | None = None
    risk_sizing: RiskSizing | None = None


@dataclass(frozen=True)
class Execution:
    timestamp: datetime
    price: float
    quantity: int
    direction: Direction
    fee: float
    slippage: float
    is_entry: bool
    reference_price: float | None = None
    spread_cost: float = 0.0
    impact_cost: float = 0.0
    latency_cost: float = 0.0
    requested_quantity: int | None = None
    unfilled_quantity: int = 0
    status: str = "fully_filled"
    explanation: str = ""


@dataclass
class Position:
    symbol: str
    direction: Direction
    entry_timestamp: datetime
    entry_price: float
    quantity: int
    stop_price: float
    take_profit_price: float
    entry_fee: float
    entry_slippage: float
    commission_per_share: float = 0.0


@dataclass(frozen=True)
class Trade:
    symbol: str
    direction: Direction
    entry_timestamp: datetime
    entry_price: float
    exit_timestamp: datetime
    exit_price: float
    quantity: int
    stop_price: float
    take_profit_price: float
    fees: float
    slippage: float
    realized_pnl: float
    exit_reason: ExitReason

    @property
    def return_pct(self) -> float:
        notional = self.entry_price * self.quantity
        return self.realized_pnl / notional if notional else 0.0
