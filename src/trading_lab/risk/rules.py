from trading_lab.models import Direction


def stop_and_target(
    entry_price: float,
    direction: Direction,
    stop_loss_pct: float,
    take_profit_pct: float,
) -> tuple[float, float]:
    if direction == Direction.LONG:
        return (
            entry_price * (1 - stop_loss_pct),
            entry_price * (1 + take_profit_pct),
        )
    return (
        entry_price * (1 + stop_loss_pct),
        entry_price * (1 - take_profit_pct),
    )
