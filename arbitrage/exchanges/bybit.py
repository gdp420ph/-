"""Utilities for retrieving volume data from Bybit's public API."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Dict, Iterable

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://api.bybit.com/v5/market/tickers"


def _request_tickers(timeout: float = 10.0) -> Iterable[dict]:
    """Return the raw ticker payload from Bybit."""

    url = f"{_API_URL}?{urllib.parse.urlencode({'category': 'linear'})}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.load(response)
    if payload.get("retCode") != 0:
        raise RuntimeError(f"Bybit API error: {payload.get('retCode')} {payload.get('retMsg')}")
    result = payload.get("result", {})
    return result.get("list", [])


def get_symbol_volumes(timeout: float = 10.0) -> Dict[str, float]:
    """Fetch 24h quote volume for all linear futures symbols on Bybit.

    Returns a mapping ``symbol -> quote volume``.
    """

    volumes: Dict[str, float] = {}
    for ticker in _request_tickers(timeout=timeout):
        symbol = ticker.get("symbol")
        if not symbol:
            continue
        turnover = ticker.get("turnover24h")
        try:
            volume = float(turnover)
        except (TypeError, ValueError):
            _LOGGER.debug("Skipping Bybit symbol %s with invalid turnover %r", symbol, turnover)
            continue
        volumes[symbol] = volume
    return volumes
