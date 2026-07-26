from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from trading_lab.data.cache import HistoricalDataCache
from trading_lab.data.providers.alpaca import AlpacaHistoricalDataProvider
from trading_lab.data.providers.base import HistoricalDataProviderError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and cache historical US equity bars from Alpaca"
    )
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--timeframe", default="1Min")
    parser.add_argument("--cache-dir", default="data/historical")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache = HistoricalDataCache(args.cache_dir)
    try:
        provider = AlpacaHistoricalDataProvider.from_env(cache=cache)
        bars = provider.get_bars(
            args.symbol,
            args.start,
            args.end,
            args.timeframe,
        )
    except (HistoricalDataProviderError, ValueError) as exc:
        raise SystemExit(f"Historical data download failed: {exc}") from exc
    path = cache.find_covering(
        args.symbol.upper(),
        args.timeframe,
        args.start,
        args.end,
    )
    if path is None:
        raise SystemExit("Historical data download completed but no cache file exists")
    print(f"Cached {len(bars):,} bars at {Path(path).resolve()}")


if __name__ == "__main__":
    main()
