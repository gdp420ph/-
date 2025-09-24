"""Utilities for retrieving futures volume data from Binance's public API."""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Dict, Iterable

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"


def _request_tickers(timeout: float = 10.0) -> Iterable[dict]:
    """Return the raw 24h statistics for all USDT-margined futures symbols."""

    with urllib.request.urlopen(_API_URL, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected response from Binance futures API")
    return payload


def get_symbol_volumes(timeout: float = 10.0) -> Dict[str, float]:
    """Fetch 24h quote volume for USDT-margined perpetual contracts on Binance."""

    volumes: Dict[str, float] = {}
    for ticker in _request_tickers(timeout=timeout):
        symbol = ticker.get("symbol")
        if not symbol:
            continue
        volume = ticker.get("quoteVolume")
        try:
            volumes[symbol] = float(volume)
        except (TypeError, ValueError):
            _LOGGER.debug("Skipping Binance symbol %s with invalid quote volume %r", symbol, volume)
    return volumes
