from __future__ import annotations

import argparse
from pathlib import Path

from trading_lab.backtesting.engine import BacktestEngine
from trading_lab.config.settings import BacktestConfig, ReferenceORBConfig
from trading_lab.data.loader import load_csv
from trading_lab.reporting.summary import export_results, format_summary
from trading_lab.strategies.reference_orb import ReferenceORBStrategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the frozen Reference-ORB-v1 interpretation"
    )
    parser.add_argument("--data", required=True, help="Timezone-aware OHLCV CSV")
    parser.add_argument("--output", default="output/reference_orb")
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strategy = ReferenceORBStrategy(ReferenceORBConfig())
    config = BacktestConfig(
        starting_capital=25_000,
        position_size=1,  # unused by risk-sized reference signals
        trading_fee=0,
        slippage_bps=args.slippage_bps,
    )
    result = BacktestEngine(strategy, config).run(load_csv(args.data))
    export_results(result, Path(args.output))
    print(format_summary(result, "Reference-ORB-v1 Backtest"))
    print(f"\nResults written to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
