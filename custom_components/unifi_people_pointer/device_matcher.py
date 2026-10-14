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


def match_device(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Match a client to a configured device (MAC first, then hostname)."""
    client_mac = normalize_mac(str(client.get("mac") or ""))
    if client_mac:
        for device in devices:
            device_mac = normalize_mac(str(device.get("mac") or ""))
            if device_mac and device_mac == client_mac:
                return device

    hostname = client.get("hostname")
    if hostname:
        host_l = str(hostname).lower()
        for device in devices:
            for pattern in normalize_hostname_match(device.get("hostname_match")):
                token = pattern.lower()
                if token == host_l:
                    return device
    return None


def match_device_partial(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Match a client to a device using partial hostname matching."""
    exact = match_device(client, devices)
    if exact is not None:
        return exact

    hostname = client.get("hostname")
    if not hostname:
        return None
    host_l = str(hostname).lower()
    for device in devices:
        for pattern in normalize_hostname_match(device.get("hostname_match")):
            token = pattern.lower()
            if token in host_l:
                return device
    return None


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
