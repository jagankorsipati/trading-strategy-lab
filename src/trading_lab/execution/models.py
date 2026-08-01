from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from trading_lab.market.calendar import TradingSession
from trading_lab.models import ExitReason, MarketBar


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class TimeInForce(StrEnum):
    DAY = "day"


class ExecutionStatus(StrEnum):
    FULLY_FILLED = "fully_filled"
    PARTIALLY_FILLED = "partially_filled"
    NOT_FILLED = "not_filled"
    REJECTED = "rejected"


class RejectionReason(StrEnum):
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    PRICE_NOT_REACHED = "price_not_reached"
    AMBIGUOUS_BAR = "ambiguous_bar"
    SESSION_ENDED = "session_ended"
    MINIMUM_VOLUME = "minimum_volume"
    IMPACT_LIMIT = "impact_limit"
    BUYING_POWER = "buying_power"


@dataclass(frozen=True)
class OrderIntent:
    timestamp: object
    side: OrderSide
    order_type: OrderType
    requested_quantity: int
    reference_price: float
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: float | None = None
    stop_price: float | None = None
    is_entry: bool = True
    commission_per_share: float = 0.0
    fixed_commission: float = 0.0

    def __post_init__(self) -> None:
        if self.requested_quantity <= 0:
            raise ValueError("requested quantity must be positive")
        if self.reference_price <= 0:
            raise ValueError("reference price must be positive")
        if self.commission_per_share < 0 or self.fixed_commission < 0:
            raise ValueError("commission cannot be negative")
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit orders require a limit price")
        if self.order_type == OrderType.STOP and self.stop_price is None:
            raise ValueError("stop orders require a stop price")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("limit price must be positive")
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("stop price must be positive")
        if self.order_type == OrderType.MARKET and (
            self.limit_price is not None or self.stop_price is not None
        ):
            raise ValueError("market orders cannot include limit or stop prices")
        if self.order_type == OrderType.LIMIT and self.stop_price is not None:
            raise ValueError("limit orders cannot include a stop price")
        if self.order_type == OrderType.STOP and self.limit_price is not None:
            raise ValueError("stop orders cannot include a limit price")
        if self.order_type == OrderType.MARKET and (
            self.limit_price is not None or self.stop_price is not None
        ):
            raise ValueError("market orders cannot include limit or stop prices")
        if self.order_type == OrderType.LIMIT and self.stop_price is not None:
            raise ValueError("limit orders cannot include a stop price")
        if self.order_type == OrderType.STOP and self.limit_price is not None:
            raise ValueError("stop orders cannot include a limit price")


@dataclass(frozen=True)
class ExecutionContext:
    bar: MarketBar
    session: TradingSession | None
    exit_reason: ExitReason | None = None
    delayed_bars: int = 0


@dataclass(frozen=True)
class ExecutionCostBreakdown:
    spread: float = 0.0
    fixed_slippage: float = 0.0
    market_impact: float = 0.0
    latency: float = 0.0
    commission: float = 0.0

    @property
    def price_cost(self) -> float:
        return self.spread + self.fixed_slippage + self.market_impact + self.latency

    @property
    def total(self) -> float:
        return self.price_cost + self.commission


@dataclass(frozen=True)
class Fill:
    timestamp: object
    reference_price: float
    price: float
    quantity: int
    costs: ExecutionCostBreakdown


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    requested_quantity: int
    filled_quantity: int
    unfilled_quantity: int
    fill: Fill | None
    rejection_reason: RejectionReason | None
    explanation: str

    def __post_init__(self) -> None:
        if min(self.requested_quantity, self.filled_quantity, self.unfilled_quantity) < 0:
            raise ValueError("execution quantities cannot be negative")
        if self.filled_quantity + self.unfilled_quantity != self.requested_quantity:
            raise ValueError("filled and unfilled quantities must reconcile")
        if self.filled_quantity and self.fill is None:
            raise ValueError("a positive fill quantity requires a Fill")
