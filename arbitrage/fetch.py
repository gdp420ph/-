"""Helpers for fetching and combining exchange volume data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional
from urllib.error import URLError

from .exchanges import binance, bybit
from . import offline

_LOGGER = logging.getLogger(__name__)


@dataclass
class ExchangeVolume:
    """24 hour quote volume for a single symbol on an exchange."""

    exchange: str
    symbol: str
    quote_volume: float


ExchangeVolumeMap = Mapping[str, float]


def fetch_exchange_volumes(
    *,
    exchanges: Iterable[str] = ("bybit", "binance"),
    timeout: float = 10.0,
) -> Dict[str, ExchangeVolumeMap]:
    """Fetch symbol volume mappings for the requested exchanges."""

    data: Dict[str, ExchangeVolumeMap] = {}
    for name in exchanges:
        if name.lower() == "bybit":
            data["bybit"] = _load_with_fallback(
                lambda: bybit.get_symbol_volumes(timeout=timeout), offline.BYBIT_SAMPLE
            )
        elif name.lower() == "binance":
            data["binance"] = _load_with_fallback(
                lambda: binance.get_symbol_volumes(timeout=timeout), offline.BINANCE_SAMPLE
            )
        else:
            raise ValueError(f"Unsupported exchange: {name}")
    return data


def _load_with_fallback(loader, fallback: ExchangeVolumeMap) -> ExchangeVolumeMap:
    try:
        return loader()
    except URLError as exc:
        _LOGGER.warning("Falling back to offline sample data due to network error: %s", exc)
        return fallback
