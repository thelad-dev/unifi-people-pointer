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


def exact_matching_devices(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return devices that exact-match a client, with tiered priority.

    Priority for one client across the device list:
    1. configured MAC equality
    2. hostname_match token equality
    3. display-name equality (fallback only when no MAC/hostname_match hits)
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
            return mac_hits

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
        return hostname_hits

    name_hits: list[dict[str, Any]] = []
    for device in candidates:
        if normalize_hostname_match(device.get("hostname_match")):
            continue
        name = str(device.get("name") or "").strip().lower()
        if name and name == host_l:
            name_hits.append(device)
    return name_hits


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
