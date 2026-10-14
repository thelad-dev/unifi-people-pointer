"""Device matching logic."""

from __future__ import annotations

from typing import Any

from .api_parser import extract_oui, normalize_mac


def normalize_hostname_match(value: Any) -> list[str]:
    """Normalize hostname_match to a list of non-empty string tokens."""
    if value is None:
        return []
    if isinstance(value, str):
        token = value.strip()
        return [token] if token else []
    if isinstance(value, (list, tuple)):
        tokens: list[str] = []
        for item in value:
            token = str(item).strip()
            if token:
                tokens.append(token)
        return tokens
    return []


def _dedupe_devices_by_id(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve order while dropping duplicate device ids."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for device in devices:
        device_id = str(device.get("id") or "")
        key = device_id or str(id(device))
        if key in seen:
            continue
        seen.add(key)
        out.append(device)
    return out


def _exclusive_exact_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One client maps to at most one exact device via a stable device-id winner."""
    uniq = _dedupe_devices_by_id(hits)
    if not uniq:
        return []
    if len(uniq) == 1:
        return uniq
    winner = sorted(uniq, key=lambda d: str(d.get("id") or ""))[0]
    return [winner]


def _prefer_tracked_mac_hit(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve duplicate MAC rows to a single preferred device."""
    uniq = _dedupe_devices_by_id(hits)
    if not uniq:
        return []
    tracked = [d for d in uniq if is_tracked(d)]
    pool = tracked or uniq
    if len(pool) == 1:
        return pool
    pool_sorted = sorted(pool, key=lambda d: str(d.get("id") or ""))
    return [pool_sorted[0]]


def exact_matching_devices(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return devices that exact-match a client, with tiered priority.

    Priority for one client across the device list:
    1. configured MAC equality
    2. hostname_match token equality
    3. display-name equality (fallback only when no MAC/hostname_match hits)

    Hostname and name tiers keep a single stable winner when multiple devices
    share the same exact identity so one live client cannot dual-home two people.
    """
    candidates = [d for d in devices if isinstance(d, dict)]
    client_mac = normalize_mac(str(client.get("mac") or ""))
    if client_mac:
        mac_hits = [
            d
            for d in candidates
            if normalize_mac(str(d.get("mac") or "")) == client_mac
        ]
        if mac_hits:
            return _prefer_tracked_mac_hit(mac_hits)

    hostname = client.get("hostname")
    if not hostname:
        return []
    host_l = str(hostname).lower()

    hostname_hits: list[dict[str, Any]] = []
    for device in candidates:
        for pattern in normalize_hostname_match(device.get("hostname_match")):
            if pattern.lower() == host_l:
                hostname_hits.append(device)
                break
    if hostname_hits:
        return _exclusive_exact_hits(hostname_hits)

    name_hits: list[dict[str, Any]] = []
    for device in candidates:
        if normalize_hostname_match(device.get("hostname_match")):
            continue
        name = str(device.get("name") or "").strip().lower()
        if name and name == host_l:
            name_hits.append(device)
    return _exclusive_exact_hits(name_hits)


def partial_matching_devices(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return devices whose hostname_match tokens are substrings of client hostname.

    Does not consider display name and does not fall back to exact matches.
    """
    hostname = client.get("hostname")
    if not hostname:
        return []
    host_l = str(hostname).lower()
    hits: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        for pattern in normalize_hostname_match(device.get("hostname_match")):
            token = pattern.lower()
            if token and token in host_l:
                hits.append(device)
                break
    return hits


def match_device(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Match a client to a configured device (MAC, hostname_match, then name)."""
    hits = exact_matching_devices(client, devices)
    return hits[0] if hits else None


def match_device_partial(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Match a client to a device using exact first, then partial hostname tokens."""
    exact = match_device(client, devices)
    if exact is not None:
        return exact
    partials = partial_matching_devices(client, devices)
    return partials[0] if partials else None


def is_tracked(device: dict[str, Any]) -> bool:
    """Check if device should be tracked for presence."""
    return bool(device.get("track", True)) and not bool(device.get("disabled", False))


def get_manufacturer_hint(
    client: dict[str, Any], manufacturers: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Get manufacturer hint from OUI prefix."""
    mac = client.get("mac")
    if not mac:
        return None
    oui = extract_oui(str(mac))
    for manufacturer in manufacturers:
        prefixes = manufacturer.get("oui_prefixes") or []
        for prefix in prefixes:
            if normalize_mac(str(prefix)) == oui or str(prefix).lower() == oui:
                return manufacturer
    return None
