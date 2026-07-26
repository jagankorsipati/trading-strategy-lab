from __future__ import annotations

import argparse
from pathlib import Path

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.config.settings import BacktestConfig, ORBConfig
from trading_lab.data.loader import load_csv
from trading_lab.models import BreakoutConfirmation, TradeDirection
from trading_lab.reporting.summary import export_results, format_summary
from trading_lab.strategies.orb import ORBStrategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a QQQ ORB backtest")
    parser.add_argument("--data", required=True, help="Timezone-aware OHLCV CSV")
    parser.add_argument("--output", default="output")
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--opening-range-minutes", type=int, default=15)
    parser.add_argument("--direction", choices=["long", "short", "both"], default="both")
    parser.add_argument("--confirmation", choices=["close", "high_low"], default="close")
    parser.add_argument("--position-size", type=int, default=10)
    parser.add_argument("--starting-capital", type=float, default=10_000)
    parser.add_argument("--stop-loss-pct", type=float, default=0.005)
    parser.add_argument("--take-profit-pct", type=float, default=0.01)
    parser.add_argument("--fee", type=float, default=0.0, help="Fee per execution")
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--max-trades-per-day", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    orb_config = ORBConfig(
        symbol=args.symbol,
        opening_range_minutes=args.opening_range_minutes,
        trade_direction=TradeDirection(args.direction),
        confirmation=BreakoutConfirmation(args.confirmation),
        maximum_trades_per_day=args.max_trades_per_day,
    )
    backtest_config = BacktestConfig(
        starting_capital=args.starting_capital,
        position_size=args.position_size,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        trading_fee=args.fee,
        slippage_bps=args.slippage_bps,
    )
    bars = load_csv(args.data)
    result = BacktestEngine(ORBStrategy(orb_config), backtest_config).run(bars)
    export_results(result, Path(args.output))
    print(format_summary(result, f"{args.symbol} ORB Backtest"))
    print(f"\nResults written to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
