from __future__ import annotations

import argparse

from trading_lab.data.quality import audit_historical_csv, format_quality_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit historical OHLCV data against an exchange calendar"
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--year", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = audit_historical_csv(args.data, year=args.year)
    print(format_quality_report(report))


if __name__ == "__main__":
    main()
