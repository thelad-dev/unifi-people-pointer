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
        if not device.get("mac"):
            continue
        person_id = None
        for person in coordinator.people:
            if device.get("id") in (person.get("device_ids") or []):
                person_id = person.get("id")
                break
        entities.append(
            UniFiDeviceTracker(
                coordinator,
                {
                    "mac": normalize_mac(str(device["mac"])),
                    "name": device.get("name") or device.get("id") or device["mac"],
                    "type": device.get("type"),
                    "person": person_id,
                },
            )
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
        self._primary_device = person_data.get("primary_device") or ""
        self._secondary_devices = person_data.get("secondary_devices") or []
        self._device_ids = person_data.get("device_ids") or []
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
        return {
            "person_id": self._person_id,
            "ha_person": self._ha_person,
            "primary_device": self._get_primary_device_info(),
            "secondary_devices": self._get_secondary_devices_info(),
            "devices_online": presence.get("devices_online", 0),
            "online_device_ids": presence.get("online_device_ids", []),
            "source": "unifi_people_pointer",
        }

    def _get_primary_device_info(self) -> dict[str, Any]:
        """Get primary device info."""
        return {
            "mac": self._primary_device,
            "connected": bool(self._primary_device)
            and self.coordinator.is_device_online(self._primary_device),
        }

    def _get_secondary_devices_info(self) -> list[dict[str, Any]]:
        """Get secondary devices info."""
        return [
            {
                "mac": mac,
                "connected": self.coordinator.is_device_online(mac),
            }
            for mac in self._secondary_devices
        ]

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
        self._mac = normalize_mac(str(device_data["mac"]))
        self._attr_name = device_data["name"]
        self._person: str | None = device_data.get("person")
        self._device_type: str | None = device_data.get("type")
        self._attr_unique_id = f"{DOMAIN}_device_{self._mac.replace(':', '').lower()}"

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
        client = self.coordinator.async_get_client_by_mac(self._mac) or {}
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
            "mac": self._mac,
            "ip": client.get("ip"),
            "hostname": client.get("hostname"),
            "signal_strength": client.get("signal") or client.get("signal_strength"),
            "ap_mac": client.get("ap_mac"),
            "last_seen": last_seen_iso,
            "person": self._person,
            "device_type": self._device_type,
            "source": "unifi_people_pointer",
        }

    def _is_connected(self) -> bool:
        """Check if device is connected."""
        return self.coordinator.is_device_online(self._mac)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
