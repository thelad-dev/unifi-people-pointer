"""Data file loading and validation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .api_parser import normalize_mac
from .device_matcher import normalize_hostname_match

_LOGGER = logging.getLogger(__name__)


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from path."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


def load_manufacturers(path: Path) -> dict[str, Any]:
    """Load manufacturers.json."""
    if not path.exists():
        raise FileNotFoundError(path)
    return _read_json(path)


def load_devices(path: Path) -> dict[str, Any]:
    """Load devices.json."""
    if not path.exists():
        raise FileNotFoundError(path)
    data = _read_json(path)
    devices = data.get("devices", [])
    if not isinstance(devices, list):
        raise ValueError("devices must be a list")
    valid: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            _LOGGER.warning("Ignoring non-object device entry in %s", path)
            continue
        if device.get("mac"):
            device["mac"] = normalize_mac(str(device["mac"]))
        device["hostname_match"] = normalize_hostname_match(
            device.get("hostname_match")
        )
        if not validate_device(device):
            _LOGGER.warning(
                "Ignoring invalid device entry in %s (need id + mac): %s",
                path,
                device.get("id") or device.get("mac") or device,
            )
            continue
        valid.append(device)
    data["devices"] = valid
    return data


def load_people(path: Path) -> dict[str, Any]:
    """Load people.json."""
    if not path.exists():
        raise FileNotFoundError(path)
    data = _read_json(path)
    people = data.get("people", [])
    if not isinstance(people, list):
        raise ValueError("people must be a list")
    valid: list[dict[str, Any]] = []
    for person in people:
        if not isinstance(person, dict) or not validate_person(person):
            _LOGGER.warning(
                "Ignoring invalid person entry in %s: %s",
                path,
                person if not isinstance(person, dict) else person.get("id") or person,
            )
            continue
        valid.append(person)
    data["people"] = valid
    return data


def validate_device(device: dict[str, Any]) -> bool:
    """Validate device schema (fixture / datenmodell shape)."""
    if not isinstance(device, dict):
        return False
    mac = device.get("mac")
    device_id = device.get("id")
    if not device_id or not isinstance(device_id, str):
        return False
    if not mac or not isinstance(mac, str):
        return False
    normalized = normalize_mac(mac)
    if len(normalized.split(":")) != 6:
        return False
    return True


def validate_person(person: dict[str, Any]) -> bool:
    """Validate person schema (fixture / datenmodell shape)."""
    if not isinstance(person, dict):
        return False
    if not person.get("id"):
        return False
    ha_person = person.get("ha_person")
    if ha_person is not None:
        if not isinstance(ha_person, str) or not ha_person.startswith("person."):
            return False
    device_ids = person.get("device_ids")
    if device_ids is not None and not isinstance(device_ids, list):
        return False
    secondaries = person.get("secondary_devices")
    if secondaries is not None and not isinstance(secondaries, list):
        return False
    # id is enough; ownership lists may be empty after exclusive moves.
    return True


def validate_person_devices(
    person: dict[str, Any], devices: list[dict[str, Any]]
) -> bool:
    """Validate person's device IDs reference existing devices."""
    known = {d.get("id") for d in devices if isinstance(d, dict)}
    device_ids = person.get("device_ids") or []
    if not isinstance(device_ids, list):
        return False
    return all(device_id in known for device_id in device_ids)


def validate_oui_prefix(oui: str) -> bool:
    """Validate OUI prefix format."""
    normalized = normalize_mac(oui)
    parts = normalized.split(":")
    return len(parts) == 3 and all(len(p) == 2 for p in parts)


def load_with_version_check(path: Path, expected_version: int) -> dict[str, Any]:
    """Load data file with version check."""
    data = _read_json(path)
    version = data.get("version")
    if version != expected_version:
        raise ValueError(
            f"version mismatch in {path}: got {version}, expected {expected_version}"
        )
    return data


class DataLoader:
    """Data file loader with reload support."""

    def __init__(
        self,
        manufacturers_path: Path | None,
        devices_path: Path,
        people_path: Path,
    ) -> None:
        """Initialize data loader."""
        self._manufacturers_path = manufacturers_path
        self._devices_path = devices_path
        self._people_path = people_path
        self._manufacturers: dict[str, Any] = {"manufacturers": []}
        self._devices: dict[str, Any] = {"devices": []}
        self._people: dict[str, Any] = {"people": []}
        self.reload()

    def get_devices(self) -> dict[str, Any]:
        """Get loaded devices."""
        return self._devices

    def get_people(self) -> dict[str, Any]:
        """Get loaded people."""
        return self._people

    def get_manufacturers(self) -> dict[str, Any]:
        """Get loaded manufacturers."""
        return self._manufacturers

    def reload(self) -> None:
        """Reload data files."""
        try:
            if self._manufacturers_path and self._manufacturers_path.exists():
                self._manufacturers = load_manufacturers(self._manufacturers_path)
            else:
                self._manufacturers = {"manufacturers": []}
        except (OSError, ValueError, json.JSONDecodeError) as err:
            _LOGGER.warning(
                "Keeping previous manufacturers data after reload failure: %s", err
            )

        try:
            if self._devices_path.exists():
                self._devices = load_devices(self._devices_path)
            else:
                _LOGGER.warning("devices.json missing at %s", self._devices_path)
                self._devices = {"version": 1, "devices": []}
        except (OSError, ValueError, json.JSONDecodeError) as err:
            _LOGGER.warning(
                "Keeping previous devices data after reload failure: %s", err
            )

        try:
            if self._people_path.exists():
                self._people = load_people(self._people_path)
            else:
                _LOGGER.warning("people.json missing at %s", self._people_path)
                self._people = {"version": 1, "people": []}
        except (OSError, ValueError, json.JSONDecodeError) as err:
            _LOGGER.warning(
                "Keeping previous people data after reload failure: %s", err
            )
