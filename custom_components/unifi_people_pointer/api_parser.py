"""UniFi API response parsing utilities."""

from __future__ import annotations

from typing import Any


def parse_clients(raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse UniFi API client response."""
    # TODO: Implement parsing
    raise NotImplementedError("To be implemented in Phase 1-4")


def normalize_mac(mac: str) -> str:
    """Normalize MAC address to lowercase with colons."""
    # TODO: Implement normalization
    raise NotImplementedError("To be implemented in Phase 1-4")


def extract_oui(mac: str) -> str:
    """Extract OUI prefix from MAC address."""
    # TODO: Implement OUI extraction
    raise NotImplementedError("To be implemented in Phase 1-4")


def filter_wireless_only(clients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to only wireless clients."""
    # TODO: Implement filtering
    raise NotImplementedError("To be implemented in Phase 1-4")


def is_client_online(last_seen: int, threshold_seconds: int = 300) -> bool:
    """Check if client is considered online based on last_seen timestamp."""
    # TODO: Implement online check
    raise NotImplementedError("To be implemented in Phase 1-4")


def categorize_signal(signal: int) -> str:
    """Categorize WiFi signal strength."""
    # TODO: Implement signal categorization
    raise NotImplementedError("To be implemented in Phase 1-4")


def parse_api_error(response: dict[str, Any]) -> dict[str, str]:
    """Parse API error response."""
    # TODO: Implement error parsing
    raise NotImplementedError("To be implemented in Phase 1-4")


def parse_sites(sites_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse UniFi sites response."""
    # TODO: Implement sites parsing
    raise NotImplementedError("To be implemented in Phase 1-4")


def deduplicate_clients(clients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate clients, keeping most recent."""
    # TODO: Implement deduplication
    raise NotImplementedError("To be implemented in Phase 1-4")


def deduplicate_clients_by_signal(
    clients: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove duplicate clients, keeping strongest signal."""
    # TODO: Implement signal-based deduplication
    raise NotImplementedError("To be implemented in Phase 1-4")


def get_wifi_band(channel: int) -> str:
    """Determine WiFi band from channel number."""
    # TODO: Implement band detection
    raise NotImplementedError("To be implemented in Phase 1-4")


def is_private_mac(mac: str) -> bool:
    """Check if MAC address is private/randomized."""
    # TODO: Implement private MAC detection
    raise NotImplementedError("To be implemented in Phase 1-4")
