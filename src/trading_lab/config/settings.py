from __future__ import annotations

from dataclasses import dataclass
from datetime import time, timedelta

from trading_lab.models import BreakoutConfirmation, TradeDirection


@dataclass(frozen=True)
class ORBConfig:
    symbol: str = "QQQ"
    opening_range_minutes: int = 15
    market_open: time = time(9, 30)
    trade_direction: TradeDirection = TradeDirection.BOTH
    confirmation: BreakoutConfirmation = BreakoutConfirmation.CLOSE
    maximum_trades_per_day: int = 1

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.opening_range_minutes <= 0:
            raise ValueError("opening_range_minutes must be positive")
        if self.maximum_trades_per_day <= 0:
            raise ValueError("maximum_trades_per_day must be positive")

    @property
    def range_end(self) -> time:
        anchor = timedelta(
            hours=self.market_open.hour,
            minutes=self.market_open.minute + self.opening_range_minutes,
        )
        seconds = int(anchor.total_seconds()) % (24 * 60 * 60)
        return time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)


@dataclass(frozen=True)
class ReferenceORBConfig:
    symbol: str = "QQQ"
    market_open: time = time(9, 30)
    candle_minutes: int = 5
    account_value: float = 25_000.0
    risk_fraction: float = 0.01
    max_leverage: float = 4.0
    minimum_risk_per_share: float = 0.05
    reward_risk_multiple: float = 10.0
    commission_per_share: float = 0.0005
    maximum_trades_per_day: int = 1

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        positive = (
            self.candle_minutes,
            self.account_value,
            self.risk_fraction,
            self.max_leverage,
            self.minimum_risk_per_share,
            self.reward_risk_multiple,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("reference ORB numeric settings must be positive")
        if self.commission_per_share < 0:
            raise ValueError("commission_per_share cannot be negative")
        if self.maximum_trades_per_day != 1:
            raise ValueError("Reference-ORB-v1 permits exactly one trade per day")


@dataclass(frozen=True)
class BacktestConfig:
    starting_capital: float = 10_000.0
    position_size: int = 10
    stop_loss_pct: float = 0.005
    take_profit_pct: float = 0.01
    trading_fee: float = 0.0
    slippage_bps: float = 0.0
    def __post_init__(self) -> None:
        if self.starting_capital <= 0:
            raise ValueError("starting_capital must be positive")
        if self.position_size <= 0:
            raise ValueError("position_size must be positive")
        if self.stop_loss_pct <= 0 or self.take_profit_pct <= 0:
            raise ValueError("stop_loss_pct and take_profit_pct must be positive")
        if self.trading_fee < 0 or self.slippage_bps < 0:
            raise ValueError("fees and slippage cannot be negative")
