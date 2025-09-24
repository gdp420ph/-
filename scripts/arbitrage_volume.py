"""Command line utility for inspecting volume differences."""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arbitrage import calculate_volume_differences, fetch_exchange_volumes

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="Number of symbols to display")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum absolute difference in quote volume",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        volumes = fetch_exchange_volumes()
    except Exception as exc:
        logging.error("Failed to fetch volumes: %s", exc)
        return 1
    diffs = calculate_volume_differences(
        volumes["bybit"],
        volumes["binance"],
        min_difference=args.threshold,
        limit=args.limit,
    )

    for item in diffs:
        print(
            f"{item.symbol:15s} Bybit: {item.base_volume:15.2f} | Binance: {item.quote_volume:15.2f} | "
            f"Diff: {item.difference:12.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
