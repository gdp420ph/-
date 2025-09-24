"""Realtime pricing utilities for arbitrage monitoring.

The module provides helpers to subscribe to Bybit/Binance book tickers via
WebSocket (with graceful offline fallbacks) and detect actionable spreads.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Sequence

_LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency is checked at runtime
    import websockets
except Exception:  # pragma: no cover - any error leads to offline mode
    websockets = None  # type: ignore


@dataclass(slots=True)
class PriceUpdate:
    """Represents a single best bid/ask update for a symbol on an exchange."""

    exchange: str
    symbol: str
    bid: float
    ask: float
    timestamp: float


@dataclass(slots=True)
class SpreadSignal:
    """An arbitrage opportunity detected between two exchanges."""

    symbol: str
    buy_exchange: str
    sell_exchange: str
    spread: float
    spread_pct: float
    timestamp: float


class RealTimePriceFeed:
    """Stream best bid/ask data from exchanges or an offline simulator."""

    def __init__(
        self,
        symbols: Sequence[str],
        *,
        reconnect_delay: float = 5.0,
        offline: bool = False,
    ) -> None:
        self.symbols = [symbol.upper() for symbol in symbols]
        self.reconnect_delay = max(reconnect_delay, 1.0)
        self.offline = offline or websockets is None

    async def updates(self) -> AsyncIterator[PriceUpdate]:
        if not self.symbols:
            return
        if self.offline:
            async for update in self._offline_stream():
                yield update
            return

        queue: asyncio.Queue[PriceUpdate] = asyncio.Queue()
        tasks = [
            asyncio.create_task(self._run_binance(queue)),
            asyncio.create_task(self._run_bybit(queue)),
        ]
        try:
            while True:
                update = await queue.get()
                yield update
        finally:
            for task in tasks:
                task.cancel()
                with contextlib.suppress(Exception):
                    await task

    async def _offline_stream(self) -> AsyncIterator[PriceUpdate]:
        base_prices = {symbol: 20000.0 + i * 1000 for i, symbol in enumerate(self.symbols)}
        while True:
            now = time.time()
            for exchange in ("binance", "bybit"):
                for idx, symbol in enumerate(self.symbols):
                    drift = math.sin(now / 30 + idx) * 10
                    noise = random.uniform(-2, 2)
                    mid = base_prices[symbol] + drift + noise
                    spread = random.uniform(0.5, 2.5)
                    if exchange == "binance":
                        mid += random.uniform(-1, 1)
                    else:
                        mid += random.uniform(-1, 1)
                    yield PriceUpdate(
                        exchange=exchange,
                        symbol=symbol,
                        bid=mid - spread / 2,
                        ask=mid + spread / 2,
                        timestamp=now,
                    )
            await asyncio.sleep(1.0)

    async def _run_binance(self, queue: asyncio.Queue[PriceUpdate]) -> None:
        if not self.symbols:
            return

        stream_names = "/".join(f"{symbol.lower()}@bookTicker" for symbol in self.symbols)
        url = f"wss://fstream.binance.com/stream?streams={stream_names}"

        while True:
            try:
                if websockets is None:  # pragma: no cover - safety net
                    return
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    async for raw in ws:
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            _LOGGER.debug("Binance WS invalid JSON: %s", raw)
                            continue
                        data = payload.get("data") if isinstance(payload, dict) else None
                        if not isinstance(data, dict):
                            continue
                        symbol = data.get("s") or data.get("symbol")
                        bid = data.get("b") or data.get("bidPrice")
                        ask = data.get("a") or data.get("askPrice")
                        timestamp = data.get("E") or time.time() * 1000
                        try:
                            update = PriceUpdate(
                                exchange="binance",
                                symbol=str(symbol).upper(),
                                bid=float(bid),
                                ask=float(ask),
                                timestamp=float(timestamp) / 1000.0,
                            )
                        except (TypeError, ValueError):
                            continue
                        await queue.put(update)
            except asyncio.CancelledError:  # pragma: no cover - cooperative cancellation
                raise
            except Exception as exc:
                _LOGGER.warning("Binance WS error: %s", exc)
                await asyncio.sleep(self.reconnect_delay)

    async def _run_bybit(self, queue: asyncio.Queue[PriceUpdate]) -> None:
        if not self.symbols:
            return

        url = "wss://stream.bybit.com/v5/public/linear"
        subscribe = {
            "op": "subscribe",
            "args": [f"tickers.{symbol.upper()}" for symbol in self.symbols],
        }

        while True:
            try:
                if websockets is None:  # pragma: no cover
                    return
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(json.dumps(subscribe))
                    async for raw in ws:
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            _LOGGER.debug("Bybit WS invalid JSON: %s", raw)
                            continue
                        topic = payload.get("topic")
                        if not isinstance(topic, str) or not topic.startswith("tickers."):
                            continue
                        data = payload.get("data")
                        if isinstance(data, list):
                            candidates = data
                        elif isinstance(data, dict):
                            candidates = [data]
                        else:
                            continue
                        for entry in candidates:
                            symbol = entry.get("symbol") or topic.split(".")[-1]
                            bid = entry.get("bid1Price") or entry.get("bidPrice")
                            ask = entry.get("ask1Price") or entry.get("askPrice")
                            timestamp = entry.get("ts") or entry.get("timestamp") or time.time() * 1000
                            try:
                                update = PriceUpdate(
                                    exchange="bybit",
                                    symbol=str(symbol).upper(),
                                    bid=float(bid),
                                    ask=float(ask),
                                    timestamp=float(timestamp) / 1000.0,
                                )
                            except (TypeError, ValueError):
                                continue
                            await queue.put(update)
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as exc:
                _LOGGER.warning("Bybit WS error: %s", exc)
                await asyncio.sleep(self.reconnect_delay)


class RealTimeArbitrage:
    """Detect arbitrage spreads from a realtime price feed."""

    def __init__(
        self,
        symbols: Sequence[str],
        *,
        absolute_threshold: float = 0.0,
        pct_threshold: float = 0.0,
        offline: bool = False,
    ) -> None:
        self.feed = RealTimePriceFeed(symbols, offline=offline)
        self.absolute_threshold = max(absolute_threshold, 0.0)
        self.pct_threshold = max(pct_threshold, 0.0)
        self._latest: Dict[str, Dict[str, PriceUpdate]] = {symbol.upper(): {} for symbol in symbols}

    async def signals(self) -> AsyncIterator[SpreadSignal]:
        async for update in self.feed.updates():
            self._latest.setdefault(update.symbol, {})[update.exchange] = update
            opportunities = self._evaluate_symbol(update.symbol)
            for signal in opportunities:
                yield signal

    def _evaluate_symbol(self, symbol: str) -> List[SpreadSignal]:
        symbol_updates = self._latest.get(symbol.upper())
        if not symbol_updates or len(symbol_updates) < 2:
            return []

        results: List[SpreadSignal] = []
        exchanges = list(symbol_updates.keys())
        for buy_exchange in exchanges:
            buy_update = symbol_updates[buy_exchange]
            for sell_exchange in exchanges:
                if buy_exchange == sell_exchange:
                    continue
                sell_update = symbol_updates[sell_exchange]
                spread = sell_update.bid - buy_update.ask
                if spread <= 0:
                    continue
                mid = (sell_update.bid + buy_update.ask) / 2
                spread_pct = spread / mid if mid else 0.0
                if spread < self.absolute_threshold:
                    continue
                if spread_pct < self.pct_threshold:
                    continue
                results.append(
                    SpreadSignal(
                        symbol=symbol.upper(),
                        buy_exchange=buy_exchange,
                        sell_exchange=sell_exchange,
                        spread=spread,
                        spread_pct=spread_pct,
                        timestamp=max(buy_update.timestamp, sell_update.timestamp),
                    )
                )
        return results


__all__ = [
    "PriceUpdate",
    "RealTimeArbitrage",
    "RealTimePriceFeed",
    "SpreadSignal",
]
