"""Export Bybit/Binance volume differences to a CSV file."""

from __future__ import annotations

import argparse
import csv
import logging
import pathlib
import sys
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arbitrage import calculate_volume_differences, fetch_exchange_volumes

logger = logging.getLogger(__name__)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("volume_differences.csv"),
        help="Destination CSV file for the exported data.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of rows to export.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum absolute quote volume difference (USDT) to include.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args(argv)


def export_differences(args: argparse.Namespace) -> int:
    try:
        volumes = fetch_exchange_volumes()
    except Exception as exc:
        logger.error("Failed to fetch exchange volumes: %s", exc)
        return 1

    diffs = calculate_volume_differences(
        volumes["bybit"],
        volumes["binance"],
        min_difference=args.threshold,
        limit=args.limit,
    )

    if not diffs:
        logger.warning("No symbols matched the requested criteria.")

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.overwrite:
        logger.error("Output file %s already exists. Use --overwrite to replace it.", output_path)
        return 1

    with output_path.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["symbol", "bybit_quote_volume", "binance_quote_volume", "difference", "ratio"])
        for diff in diffs:
            writer.writerow(
                [
                    diff.symbol,
                    f"{diff.base_volume:.6f}",
                    f"{diff.quote_volume:.6f}",
                    f"{diff.difference:.6f}",
                    f"{diff.ratio:.6f}",
                ]
            )

    logger.info("Exported %d rows to %s", len(diffs), output_path)
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    return export_differences(args)


if __name__ == "__main__":
    raise SystemExit(main())
