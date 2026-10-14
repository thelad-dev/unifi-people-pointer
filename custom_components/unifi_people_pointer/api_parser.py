"""UniFi API response parsing utilities."""

from __future__ import annotations

import re
import time
from typing import Any

_MAC_HEX_RE = re.compile(r"[^0-9a-fA-F]")


def normalize_mac(mac: str) -> str:
    """Normalize MAC address to lowercase with colons."""
    if not mac:
        return ""
    hex_only = _MAC_HEX_RE.sub("", mac).lower()
    if len(hex_only) != 12:
        # Best-effort: return stripped lowercase with colons if already shaped.
        return mac.strip().lower().replace("-", ":")
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))


def extract_oui(mac: str) -> str:
    """Extract OUI prefix from MAC address."""
    normalized = normalize_mac(mac)
    parts = normalized.split(":")
    if len(parts) < 3:
        return normalized
    return ":".join(parts[:3])


def parse_clients(raw_data: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Parse UniFi API client response into a normalized list."""
    if not raw_data:
        return []

    clients: list[dict[str, Any]] = []
    for entry in raw_data:
        if not isinstance(entry, dict):
            continue
        mac_raw = (
            entry.get("mac")
            or entry.get("mac_address")
            or entry.get("macAddress")
        )
        if not mac_raw:
            continue
        mac = normalize_mac(str(mac_raw))
        if not mac or len(mac.split(":")) != 6:
            continue

        hostname = entry.get("hostname")
        if hostname is None:
            hostname = (
                entry.get("name")
                or entry.get("hostName")
                or entry.get("oui")
                or ""
            )

        signal = entry.get("signal")
        if signal is None:
            signal = entry.get("rssi")
        if signal is None:
            signal = entry.get("signalStrength")

        if entry.get("is_wired") is not None:
            is_wired = bool(entry.get("is_wired"))
        elif entry.get("wired") is not None:
            is_wired = bool(entry.get("wired"))
        else:
            client_type = str(entry.get("type") or entry.get("access") or "").upper()
            if client_type in ("WIRED", "WIRE"):
                is_wired = True
            elif client_type in ("WIRELESS", "WIFI", "WLAN"):
                is_wired = False
            else:
                is_wired = False

        last_seen = entry.get("last_seen")
        if last_seen is None:
            last_seen = entry.get("last_seen_epoch")
        if last_seen is None:
            last_seen = entry.get("lastSeen")

        ap_raw = (
            entry.get("ap_mac")
            or entry.get("apMac")
            or entry.get("uplinkDeviceId")
            or entry.get("uplink_device_id")
        )
        ap_mac = normalize_mac(str(ap_raw)) if ap_raw else None

        clients.append(
            {
                "mac": mac,
                "hostname": hostname if hostname is not None else "",
                "ip": entry.get("ip")
                or entry.get("ip_address")
                or entry.get("ipAddress"),
                "last_seen": last_seen,
                "is_wired": is_wired,
                "ap_mac": ap_mac,
                "signal": signal,
                "signal_strength": signal,
                "channel": entry.get("channel"),
                "essid": entry.get("essid")
                or entry.get("ssid")
                or entry.get("wlanNetworkName"),
                "is_guest": bool(
                    entry.get("is_guest", entry.get("isGuest", False))
                ),
                "raw": entry,
            }
        )
    return clients


def filter_wireless_only(clients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to only wireless clients."""
    return [c for c in clients if not c.get("is_wired")]


def is_client_online(last_seen: int | None, threshold_seconds: int = 300) -> bool:
    """Check if client is considered online based on last_seen timestamp."""
    if last_seen is None:
        return False
    try:
        ts = int(last_seen)
    except (TypeError, ValueError):
        return False
    # UniFi sometimes returns milliseconds.
    if ts > 10_000_000_000:
        ts = ts // 1000
    return (time.time() - ts) <= threshold_seconds


def categorize_signal(signal: int) -> str:
    """Categorize WiFi signal strength."""
    if signal >= -40:
        return "excellent"
    if signal >= -60:
        return "good"
    if signal >= -75:
        return "fair"
    return "poor"


def parse_api_error(response: dict[str, Any]) -> dict[str, str]:
    """Parse API error response."""
    err_type = str(response.get("error") or response.get("code") or "unknown")
    message = str(
        response.get("error_description")
        or response.get("message")
        or response.get("msg")
        or err_type
    )
    return {"type": err_type, "message": message}


def parse_sites(sites_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse UniFi sites response."""
    sites: list[dict[str, Any]] = []
    for site in sites_data or []:
        if not isinstance(site, dict):
            continue
        name = (
            site.get("name")
            or site.get("internalReference")
            or site.get("desc")
            or site.get("id")
        )
        if not name:
            continue
        sites.append(
            {
                "name": str(name),
                "desc": site.get("desc") or site.get("name"),
                "role": site.get("role"),
                "id": site.get("id"),
                "internalReference": site.get("internalReference"),
            }
        )
    return sites


def deduplicate_clients(clients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate clients, keeping most recent."""
    best: dict[str, dict[str, Any]] = {}
    for client in clients:
        mac = client.get("mac")
        if not mac:
            continue
        current = best.get(mac)
        if current is None:
            best[mac] = client
            continue
        cur_seen = current.get("last_seen") or 0
        new_seen = client.get("last_seen") or 0
        try:
            if int(new_seen) >= int(cur_seen):
                best[mac] = client
        except (TypeError, ValueError):
            best[mac] = client
    return list(best.values())


def deduplicate_clients_by_signal(
    clients: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove duplicate clients, keeping strongest signal."""
    best: dict[str, dict[str, Any]] = {}
    for client in clients:
        mac = client.get("mac")
        if not mac:
            continue
        current = best.get(mac)
        if current is None:
            best[mac] = client
            continue
        cur_signal = current.get("signal")
        new_signal = client.get("signal")
        if cur_signal is None:
            best[mac] = client
            continue
        if new_signal is None:
            continue
        # Stronger WiFi signal is less negative / higher RSSI.
        if int(new_signal) > int(cur_signal):
            best[mac] = client
    return list(best.values())


def get_wifi_band(channel: int) -> str:
    """Determine WiFi band from channel number."""
    try:
        ch = int(channel)
    except (TypeError, ValueError):
        return "unknown"
    if 1 <= ch <= 14:
        return "2.4GHz"
    if 15 <= ch <= 177:
        return "5GHz"
    return "unknown"


def is_private_mac(mac: str) -> bool:
    """Check if MAC address is private/randomized (locally administered bit)."""
    normalized = normalize_mac(mac)
    parts = normalized.split(":")
    if not parts or len(parts[0]) != 2:
        return False
    try:
        first = int(parts[0], 16)
    except ValueError:
        return False
    return bool(first & 0x02)
