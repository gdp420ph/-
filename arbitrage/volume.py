"""Utilities for comparing symbol volumes across exchanges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence


@dataclass
class VolumeDifference:
    """Represents the absolute and relative difference between two volumes."""

    symbol: str
    base_volume: float
    quote_volume: float
    difference: float
    ratio: float


def calculate_volume_differences(
    base_volumes: Mapping[str, float],
    quote_volumes: Mapping[str, float],
    *,
    min_difference: float = 0.0,
    limit: int | None = None,
) -> List[VolumeDifference]:
    """Return the top symbols ordered by absolute volume difference."""

    diffs: List[VolumeDifference] = []
    for symbol, base_volume in base_volumes.items():
        quote_volume = quote_volumes.get(symbol)
        if quote_volume is None:
            continue
        diff = abs(base_volume - quote_volume)
        if diff < min_difference:
            continue
        ratio = diff / base_volume if base_volume else float("inf")
        diffs.append(
            VolumeDifference(
                symbol=symbol,
                base_volume=base_volume,
                quote_volume=quote_volume,
                difference=diff,
                ratio=ratio,
            )
        )

    diffs.sort(key=lambda item: item.difference, reverse=True)
    if limit is not None:
        diffs = diffs[:limit]
    return diffs
