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

from .const import DOMAIN
from .coordinator import UniFiPeoplePointerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi People Pointer device tracker from config entry."""
    # Coordinator is registered at setup; entity creation lands in Phase 3.
    _ = hass.data[DOMAIN][entry.entry_id]

    # TODO: Load people and devices from JSON files
    # For now, create empty lists
    entities: list[TrackerEntity] = []

    # Example: Create a person tracker (will be populated from people.json later)
    # person_data = {
    #     "id": "example_person",
    #     "name": "Example Person",
    #     "primary_device": "AA:BB:CC:DD:EE:FF",
    #     "secondary_devices": [],
    # }
    # entities.append(UniFiPersonTracker(coordinator, person_data))

    # Example: Create a device tracker (will be populated from devices.json later)
    # device_data = {
    #     "mac": "AA:BB:CC:DD:EE:FF",
    #     "name": "Example Device",
    # }
    # entities.append(UniFiDeviceTracker(coordinator, device_data))

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d device tracker entities", len(entities))
    else:
        _LOGGER.info(
            "No device trackers to add (people.json/devices.json not yet created)"
        )


class UniFiPersonTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a UniFi Person Tracker."""

    def __init__(
        self,
        coordinator: UniFiPeoplePointerCoordinator,
        person_data: dict[str, Any],
    ) -> None:
        """Initialize the person tracker."""
        super().__init__(coordinator)
        self._person_id = person_data["id"]
        self._name = person_data["name"]
        self._primary_device = person_data["primary_device"]
        self._secondary_devices = person_data.get("secondary_devices", [])
        self._state = STATE_NOT_HOME
        self._current_zone: str | None = None
        self._last_location: str | None = None
        self._fallback_source: str = "unifi"
        self._grace_period_start: datetime | None = None

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_person_{self._person_id}"

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def state(self) -> str:
        """Return the state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return {
            "primary_device": self._get_primary_device_info(),
            "secondary_devices": self._get_secondary_devices_info(),
            "current_zone": self._current_zone,
            "last_location": self._last_location,
            "fallback_source": self._fallback_source,
        }

    def _get_primary_device_info(self) -> dict[str, Any]:
        """Get primary device info."""
        # TODO: Get actual device info from coordinator
        return {
            "mac": self._primary_device,
            "connected": self.coordinator.is_device_online(self._primary_device),
        }

    def _get_secondary_devices_info(self) -> list[dict[str, Any]]:
        """Get secondary devices info."""
        # TODO: Get actual device info from coordinator
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
        # Check if primary device is online
        primary_online = self.coordinator.is_device_online(self._primary_device)

        if primary_online:
            self._state = STATE_HOME
            self._fallback_source = "unifi"
            self._grace_period_start = None
        else:
            # TODO: Implement grace period and fallback logic
            self._state = STATE_NOT_HOME

        self.async_write_ha_state()


class UniFiDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a UniFi Device Tracker."""

    def __init__(
        self,
        coordinator: UniFiPeoplePointerCoordinator,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._mac = device_data["mac"]
        self._name = device_data["name"]
        self._ip: str | None = None
        self._hostname: str | None = None
        self._manufacturer: str | None = None
        self._signal_strength: int | None = None
        self._ap_name: str | None = None
        self._ap_mac: str | None = None
        self._last_seen: datetime | None = None
        self._person: str | None = device_data.get("person")
        self._device_type: str | None = device_data.get("type")

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{DOMAIN}_device_{self._mac.replace(':', '').lower()}"

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def state(self) -> str:
        """Return the state."""
        return STATE_HOME if self._is_connected() else STATE_NOT_HOME

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return {
            "mac": self._mac,
            "ip": self._ip,
            "hostname": self._hostname,
            "manufacturer": self._manufacturer,
            "signal_strength": self._signal_strength,
            "ap_name": self._ap_name,
            "ap_mac": self._ap_mac,
            "last_seen": self._last_seen.isoformat() if self._last_seen else None,
            "person": self._person,
            "device_type": self._device_type,
        }

    def _is_connected(self) -> bool:
        """Check if device is connected."""
        return self.coordinator.is_device_online(self._mac)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Get device info from coordinator
        client = self.hass.loop.run_in_executor(
            None, self.coordinator.async_get_client_by_mac, self._mac
        )

        if client:
            self._ip = client.get("ip")
            self._hostname = client.get("hostname")
            self._signal_strength = client.get("signal_strength")
            self._ap_name = client.get("ap_name")
            self._ap_mac = client.get("ap_mac")
            self._last_seen = datetime.now()

        self.async_write_ha_state()
