"""Device tracker platform for UniFi People Pointer."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api_parser import normalize_mac
from .const import DOMAIN
from .coordinator import UniFiPeoplePointerCoordinator
from .presence import person_owns_device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi People Pointer device tracker from config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: UniFiPeoplePointerCoordinator = runtime["coordinator"]

    entities: list[TrackerEntity] = []
    devices_by_id = {d["id"]: d for d in coordinator.devices if d.get("id")}

    for person in coordinator.people:
        person_id = person.get("id")
        if not person_id:
            continue
        device_ids = list(person.get("device_ids") or [])
        primary_mac = ""
        secondary_macs: list[str] = []
        if device_ids:
            primary = devices_by_id.get(device_ids[0])
            if primary:
                primary_mac = normalize_mac(str(primary.get("mac") or ""))
            for device_id in device_ids[1:]:
                device = devices_by_id.get(device_id)
                if device and device.get("mac"):
                    secondary_macs.append(normalize_mac(str(device["mac"])))
        elif person.get("primary_device"):
            primary_mac = normalize_mac(str(person["primary_device"]))
            secondary_macs = [
                normalize_mac(str(m)) for m in person.get("secondary_devices") or []
            ]

        person_data = {
            "id": person_id,
            "name": person.get("name") or person_id,
            "primary_device": primary_mac,
            "secondary_devices": secondary_macs,
            "ha_person": person.get("ha_person"),
            "device_ids": device_ids,
        }
        entities.append(UniFiPersonTracker(coordinator, person_data))

    for device in coordinator.devices:
        device_id = device.get("id")
        mac = normalize_mac(str(device.get("mac") or ""))
        if not device_id and not mac:
            continue
        person_id = None
        for person in coordinator.people:
            if person_owns_device(
                person,
                device_id=device_id,
                device_mac=mac,
                devices=coordinator.devices,
            ):
                person_id = person.get("id")
                break
        entities.append(
            UniFiDeviceTracker(
                coordinator,
                {
                    "id": device_id,
                    "mac": mac,
                    "name": device.get("name") or device_id or mac,
                    "type": device.get("type"),
                    "person": person_id,
                },
            )
        )

    known_people = {
        p.get("id") for p in coordinator.people if p.get("id")
    }
    known_devices = {
        d.get("id") for d in coordinator.devices if isinstance(d, dict) and d.get("id")
    }
    coordinator.register_tracker_platform(
        async_add_entities, known_people, known_devices
    )

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d device tracker entities", len(entities))
    else:
        _LOGGER.warning(
            "No device trackers to add - create %s/people.json and devices.json",
            DOMAIN,
        )


class UniFiPersonTracker(CoordinatorEntity[UniFiPeoplePointerCoordinator], TrackerEntity):
    """Representation of a UniFi Person Tracker."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: UniFiPeoplePointerCoordinator,
        person_data: dict[str, Any],
    ) -> None:
        """Initialize the person tracker."""
        super().__init__(coordinator)
        self._person_id = person_data["id"]
        self._attr_name = person_data["name"]
        self._ha_person = person_data.get("ha_person")
        self._attr_unique_id = f"{DOMAIN}_person_{self._person_id}"

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def latitude(self) -> float | None:
        """Return latitude (not used for router source)."""
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude (not used for router source)."""
        return None

    @property
    def location_name(self) -> str:
        """Return home/not_home from presence."""
        state = self.coordinator.get_person_state(self._person_id)
        return STATE_HOME if state == "home" else STATE_NOT_HOME

    @property
    def state(self) -> str:
        """Return the state."""
        return self.location_name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        presence = self.coordinator.get_person_presence(self._person_id) or {}
        primary, secondary = self._current_device_macs(presence)
        return {
            "person_id": self._person_id,
            "ha_person": self._ha_person,
            "primary_device": {
                "mac": primary,
                "connected": bool(primary)
                and self.coordinator.is_device_online(primary),
            },
            "secondary_devices": [
                {
                    "mac": mac,
                    "connected": self.coordinator.is_device_online(mac),
                }
                for mac in secondary
            ],
            "devices_online": presence.get("devices_online", 0),
            "online_device_ids": presence.get("online_device_ids", []),
            "source": "unifi_people_pointer",
        }

    def _current_device_macs(
        self, presence: dict[str, Any]
    ) -> tuple[str, list[str]]:
        """Resolve primary/secondary MACs from live coordinator config."""
        devices = list(presence.get("devices") or [])
        if not devices:
            person_devices = self.coordinator.get_person_devices(self._person_id)
            primary_dev = person_devices.get("primary")
            secondary_devs = list(person_devices.get("secondary") or [])
            devices = ([primary_dev] if primary_dev else []) + secondary_devs

        macs: list[str] = []
        for device in devices:
            if not isinstance(device, dict):
                continue
            mac = normalize_mac(str(device.get("mac") or ""))
            if mac:
                macs.append(mac)

        if not macs:
            # Fallback: people.json device_ids against current devices list.
            person = next(
                (
                    p
                    for p in self.coordinator.people
                    if p.get("id") == self._person_id
                ),
                None,
            )
            device_ids = list((person or {}).get("device_ids") or [])
            by_id = {
                d.get("id"): d
                for d in self.coordinator.devices
                if isinstance(d, dict) and d.get("id")
            }
            for device_id in device_ids:
                device = by_id.get(device_id)
                if not device:
                    continue
                mac = normalize_mac(str(device.get("mac") or ""))
                if mac:
                    macs.append(mac)

        primary = macs[0] if macs else ""
        secondary = macs[1:] if len(macs) > 1 else []
        return primary, secondary

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class UniFiDeviceTracker(CoordinatorEntity[UniFiPeoplePointerCoordinator], TrackerEntity):
    """Representation of a UniFi Device Tracker."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: UniFiPeoplePointerCoordinator,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._device_id = device_data.get("id")
        self._setup_mac = normalize_mac(str(device_data.get("mac") or ""))
        self._attr_name = device_data["name"]
        uid_key = (
            str(self._device_id)
            if self._device_id
            else self._setup_mac.replace(":", "").lower()
        )
        self._attr_unique_id = f"{DOMAIN}_device_{uid_key}"

    def _current_device(self) -> dict[str, Any] | None:
        """Return the live devices.json record for this tracker."""
        if self._device_id:
            for device in self.coordinator.devices:
                if isinstance(device, dict) and device.get("id") == self._device_id:
                    return device
        if self._setup_mac:
            for device in self.coordinator.devices:
                if not isinstance(device, dict):
                    continue
                if normalize_mac(str(device.get("mac") or "")) == self._setup_mac:
                    return device
        return None

    def _current_mac(self) -> str:
        """Configured MAC from the latest devices.json entry."""
        device = self._current_device()
        if device and device.get("mac"):
            return normalize_mac(str(device["mac"]))
        return self._setup_mac

    def _current_person(self) -> str | None:
        """Person id currently assigned to this device."""
        device = self._current_device()
        device_id = (device or {}).get("id") or self._device_id
        mac = self._current_mac()
        for person in self.coordinator.people:
            if person_owns_device(
                person,
                device_id=device_id,
                device_mac=mac,
                devices=self.coordinator.devices,
            ):
                return person.get("id")
        return None

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def latitude(self) -> float | None:
        """Return latitude."""
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude."""
        return None

    @property
    def location_name(self) -> str:
        """Return home/not_home for the device."""
        return STATE_HOME if self._is_connected() else STATE_NOT_HOME

    @property
    def state(self) -> str:
        """Return the state."""
        return self.location_name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        mac = self._current_mac()
        device = self._current_device() or {}
        client = self.coordinator.async_get_client_by_mac(mac) or {}
        last_seen = client.get("last_seen")
        last_seen_iso = None
        if isinstance(last_seen, (int, float)):
            try:
                last_seen_iso = datetime.fromtimestamp(int(last_seen)).isoformat()
            except (OverflowError, OSError, ValueError):
                last_seen_iso = str(last_seen)
        elif last_seen is not None:
            last_seen_iso = str(last_seen)
        return {
            "mac": mac,
            "device_id": device.get("id") or self._device_id,
            "ip": client.get("ip"),
            "hostname": client.get("hostname"),
            "signal_strength": client.get("signal") or client.get("signal_strength"),
            "ap_mac": client.get("ap_mac"),
            "last_seen": last_seen_iso,
            "person": self._current_person(),
            "device_type": device.get("type"),
            "source": "unifi_people_pointer",
        }

    def _is_connected(self) -> bool:
        """Check if device is connected using the current configured MAC."""
        device = self._current_device()
        if device is None:
            return False
        mac = normalize_mac(str(device.get("mac") or "")) or self._current_mac()
        if mac and self.coordinator.is_device_online(mac):
            return True
        device_id = device.get("id")
        if device_id and device_id in getattr(
            self.coordinator, "_online_device_ids_cache", set()
        ):
            return True
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
