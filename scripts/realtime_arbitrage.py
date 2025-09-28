"""リアルタイムで裁定機会を通知するCLIツール."""

from __future__ import annotations

import argparse
import asyncio
import logging
import pathlib
import sys
import textwrap
from datetime import datetime
from typing import Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arbitrage import RealTimeArbitrage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _parse_symbols(value: str) -> Sequence[str]:
    symbols = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not symbols:
        raise argparse.ArgumentTypeError("少なくとも1つのシンボルを指定してください")
    return symbols


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bybit/Binance の最良気配を WebSocket 経由で取得し、裁定シグナルを通知します。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """例:
              python scripts/realtime_arbitrage.py --symbols BTCUSDT,ETHUSDT --spread 5 --percent 0.05
            """
        ),
    )
    parser.add_argument(
        "--symbols",
        type=_parse_symbols,
        default=["BTCUSDT", "ETHUSDT"],
        help="監視する通貨ペアをカンマ区切りで指定します (例: BTCUSDT,ETHUSDT)",
    )
    parser.add_argument(
        "--spread",
        type=float,
        default=1.0,
        help="売り買いの差額がこのUSDT以上でシグナルを通知します",
    )
    parser.add_argument(
        "--percent",
        type=float,
        default=0.0,
        help="利幅がこの割合(%)以上の場合に通知します",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="ネットワークに接続できない環境向けのシミュレーションモード",
    )
    return parser


def format_signal(signal) -> str:
    timestamp = datetime.fromtimestamp(signal.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    pct = signal.spread_pct * 100
    return (
        f"[{timestamp}] {signal.symbol}: {signal.buy_exchange}で買い {signal.sell_exchange}で売り"
        f" | 差額 {signal.spread:.4f} USDT ({pct:.3f}%)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.info(
        "監視開始: シンボル=%s, 最小差額=%.4f, 最小利幅=%.3f%% (%s)",
        ",".join(args.symbols),
        args.spread,
        args.percent,
        "オフライン" if args.offline else "リアルタイム",
    )

    engine = RealTimeArbitrage(
        args.symbols,
        absolute_threshold=args.spread,
        pct_threshold=args.percent / 100,
        offline=args.offline,
    )

    async def runner() -> None:
        async for signal in engine.signals():
            logging.info("シグナル検出: %s", format_signal(signal))

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        logging.info("ユーザーにより終了しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
