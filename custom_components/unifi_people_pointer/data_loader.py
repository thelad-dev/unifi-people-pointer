"""Data file loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_manufacturers(path: Path) -> dict[str, Any]:
    """Load manufacturers.json."""
    # TODO: Implement loading
    raise NotImplementedError("To be implemented in Phase 1-4")


def load_devices(path: Path) -> dict[str, Any]:
    """Load devices.json."""
    # TODO: Implement loading
    raise NotImplementedError("To be implemented in Phase 1-4")


def load_people(path: Path) -> dict[str, Any]:
    """Load people.json."""
    # TODO: Implement loading
    raise NotImplementedError("To be implemented in Phase 1-4")


def validate_device(device: dict[str, Any]) -> bool:
    """Validate device schema."""
    # TODO: Implement validation
    raise NotImplementedError("To be implemented in Phase 1-4")


def validate_person(person: dict[str, Any]) -> bool:
    """Validate person schema."""
    # TODO: Implement validation
    raise NotImplementedError("To be implemented in Phase 1-4")


def validate_person_devices(
    person: dict[str, Any], devices: list[dict[str, Any]]
) -> bool:
    """Validate person's device IDs reference existing devices."""
    # TODO: Implement validation
    raise NotImplementedError("To be implemented in Phase 1-4")


def validate_oui_prefix(oui: str) -> bool:
    """Validate OUI prefix format."""
    # TODO: Implement validation
    raise NotImplementedError("To be implemented in Phase 1-4")


def load_with_version_check(path: Path, expected_version: int) -> dict[str, Any]:
    """Load data file with version check."""
    # TODO: Implement version checking
    raise NotImplementedError("To be implemented in Phase 1-4")


class DataLoader:
    """Data file loader with reload support."""

    def __init__(self, manufacturers_path: Path, devices_path: Path, people_path: Path):
        """Initialize data loader."""
        # TODO: Implement initialization
        raise NotImplementedError("To be implemented in Phase 1-4")

    def get_devices(self) -> dict[str, Any]:
        """Get loaded devices."""
        # TODO: Implement getter
        raise NotImplementedError("To be implemented in Phase 1-4")

    def reload(self) -> None:
        """Reload data files."""
        # TODO: Implement reload
        raise NotImplementedError("To be implemented in Phase 1-4")
