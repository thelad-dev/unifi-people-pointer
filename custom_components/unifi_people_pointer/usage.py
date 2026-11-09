"""Compact per-AP usage history for the floor plan heatmap.

Every poll adds one sample: the number of wireless clients per access point
and, when UniFi reports client rates, an estimate of the data moved through
each AP since the previous poll. Samples are summed into 5-minute buckets for
24 hours and hourly buckets for 7 days; older buckets are dropped. Only
counters per AP MAC are kept: no client, device or person identifiers.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .api_parser import filter_wireless_only
from .const import (
    DOMAIN,
    USAGE_COARSE_BUCKET_S,
    USAGE_COARSE_KEEP_S,
    USAGE_FINE_BUCKET_S,
    USAGE_FINE_KEEP_S,
    USAGE_MAX_GAP_FACTOR,
    USAGE_SAVE_DELAY_S,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
# Rate fields of the classic client list (bytes per second).
RATE_FIELDS = ("tx_bytes-r", "rx_bytes-r")
PERIODS = {
    "1h": (3600, "fine"),
    "24h": (24 * 3600, "fine"),
    "7d": (7 * 24 * 3600, "coarse"),
}
# Per AP and bucket: [client sum, client max, bytes].
_SUM, _MAX, _BYTES = range(3)


def client_rate(client: dict[str, Any]) -> float | None:
    """Bytes per second of one client, or None when UniFi does not report it."""
    raw = client.get("raw")
    if not isinstance(raw, dict):
        return None
    total, seen = 0.0, False
    for key in RATE_FIELDS:
        try:
            value = float(raw[key])
        except (KeyError, TypeError, ValueError):
            continue
        if value >= 0:
            total += value
            seen = True
    return total if seen else None


def usage_sample(
    clients: Iterable[dict[str, Any]], ap_mac_for_key: Any
) -> tuple[dict[str, int], dict[str, float], bool]:
    """Clients and bytes per second per AP MAC from a parsed client list."""
    counts: dict[str, int] = {}
    rates: dict[str, float] = {}
    has_rates = False
    for client in filter_wireless_only(list(clients)):
        key = client.get("ap_mac")
        if not key:
            continue
        mac = ap_mac_for_key(str(key))
        counts[mac] = counts.get(mac, 0) + 1
        rate = client_rate(client)
        if rate is not None:
            has_rates = True
            rates[mac] = rates.get(mac, 0.0) + rate
    return counts, rates, has_rates


def _empty() -> dict[str, Any]:
    return {"fine": {}, "coarse": {}, "has_bytes": False, "last": None}


class ApUsageHistory:
    """Bucketed client counts and data estimates per access point."""

    def __init__(self, hass: HomeAssistant, entry_id: str, interval_s: float) -> None:
        """Initialize; call ``async_load`` before recording."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.ap_usage.{entry_id}"
        )
        self._interval = max(float(interval_s), 1.0)
        self._data = _empty()
        # Live view: last sample (counts and rates) in memory only.
        self.current_counts: dict[str, int] = {}
        self.current_rates: dict[str, float] = {}

    @property
    def has_bytes(self) -> bool:
        """True once UniFi has reported client rates."""
        return bool(self._data["has_bytes"])

    async def async_load(self) -> None:
        """Read the stored history; a broken file starts empty."""
        try:
            stored = await self._store.async_load()
        except (ValueError, OSError) as err:  # pragma: no cover - defensive
            _LOGGER.warning("Discarding unreadable AP usage history: %s", err)
            stored = None
        data = _empty()
        if isinstance(stored, dict):
            for tier in ("fine", "coarse"):
                buckets = stored.get(tier)
                if isinstance(buckets, dict):
                    data[tier] = {
                        str(k): v for k, v in buckets.items() if _valid_bucket(v)
                    }
            data["has_bytes"] = stored.get("has_bytes") is True
        self._data = data
        self._prune(time.time())

    async def async_flush(self) -> None:
        """Write pending changes now (unload)."""
        await self._store.async_save(self._data)

    @callback
    def record(
        self,
        now: float,
        counts: dict[str, int],
        rates: dict[str, float],
        has_rates: bool,
    ) -> None:
        """Add one poll; schedule a delayed save."""
        last = self._data.get("last")
        gap = self._interval if last is None else max(0.0, now - float(last))
        # After downtime, do not stretch the last rates over the whole gap.
        gap = min(gap, self._interval * USAGE_MAX_GAP_FACTOR)
        self._data["last"] = now
        if has_rates:
            self._data["has_bytes"] = True
        self.current_counts = dict(counts)
        self.current_rates = dict(rates) if has_rates else {}
        for tier, size in (
            ("fine", USAGE_FINE_BUCKET_S),
            ("coarse", USAGE_COARSE_BUCKET_S),
        ):
            key = str(int(now // size * size))
            bucket = self._data[tier].setdefault(key, {"n": 0, "aps": {}})
            bucket["n"] += 1
            for mac in set(counts) | set(rates):
                row = bucket["aps"].setdefault(mac, [0, 0, 0.0])
                count = int(counts.get(mac, 0))
                row[_SUM] += count
                row[_MAX] = max(row[_MAX], count)
                row[_BYTES] = round(row[_BYTES] + rates.get(mac, 0.0) * gap, 1)
        self._prune(now)
        self._store.async_delay_save(lambda: self._data, USAGE_SAVE_DELAY_S)

    def _prune(self, now: float) -> None:
        for tier, keep in (
            ("fine", USAGE_FINE_KEEP_S),
            ("coarse", USAGE_COARSE_KEEP_S),
        ):
            size = USAGE_FINE_BUCKET_S if tier == "fine" else USAGE_COARSE_BUCKET_S
            oldest = now - keep - size
            self._data[tier] = {
                k: v for k, v in self._data[tier].items() if float(k) > oldest
            }

    def summary(self, period: str, now: float | None = None) -> dict[str, Any]:
        """Average and peak clients plus bytes per AP over a period."""
        now = time.time() if now is None else now
        span, tier = PERIODS[period]
        size = USAGE_FINE_BUCKET_S if tier == "fine" else USAGE_COARSE_BUCKET_S
        start = now - span
        samples = 0
        first: float | None = None
        totals: dict[str, list[float]] = {}
        for key, bucket in self._data[tier].items():
            begin = float(key)
            # A bucket counts when it ends inside the period.
            if begin + size <= start:
                continue
            samples += int(bucket["n"])
            first = begin if first is None else min(first, begin)
            for mac, row in bucket["aps"].items():
                total = totals.setdefault(mac, [0, 0, 0.0])
                total[_SUM] += row[_SUM]
                total[_MAX] = max(total[_MAX], row[_MAX])
                total[_BYTES] += row[_BYTES]
        aps = {
            mac: {
                "clients": round(total[_SUM] / samples, 2) if samples else 0.0,
                "clients_max": int(total[_MAX]),
                "bytes": round(total[_BYTES]) if self.has_bytes else None,
            }
            for mac, total in totals.items()
        }
        return {"samples": samples, "since": first, "aps": aps}


def _valid_bucket(value: Any) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("n"), int):
        return False
    aps = value.get("aps")
    if not isinstance(aps, dict):
        return False
    return all(
        isinstance(row, list)
        and len(row) == 3
        and all(isinstance(x, (int, float)) for x in row)
        for row in aps.values()
    )
