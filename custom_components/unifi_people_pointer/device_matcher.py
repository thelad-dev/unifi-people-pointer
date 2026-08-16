"""Device matching logic."""

from __future__ import annotations

from typing import Any


def match_device(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Match a client to a configured device."""
    # TODO: Implement device matching
    raise NotImplementedError("To be implemented in Phase 1-4")


def match_device_partial(
    client: dict[str, Any], devices: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Match a client to a device using partial hostname matching."""
    # TODO: Implement partial matching
    raise NotImplementedError("To be implemented in Phase 1-4")


def is_tracked(device: dict[str, Any]) -> bool:
    """Check if device should be tracked for presence."""
    # TODO: Implement tracking check
    raise NotImplementedError("To be implemented in Phase 1-4")


def get_manufacturer_hint(
    client: dict[str, Any], manufacturers: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Get manufacturer hint from OUI prefix."""
    # TODO: Implement manufacturer lookup
    raise NotImplementedError("To be implemented in Phase 1-4")
