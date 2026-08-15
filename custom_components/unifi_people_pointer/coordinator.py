"""Data update coordinator for UniFi People Pointer."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, STATE_HOME, STATE_AWAY

_LOGGER = logging.getLogger(__name__)


class UniFiPeoplePointerCoordinator(DataUpdateCoordinator):
    """Coordinator to manage UniFi People Pointer data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._people: dict[str, dict] = {}
        self._devices: dict[str, dict] = {}
        self._unknown_devices: list[dict] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from UniFi."""
        try:
            # Stub implementation - would normally fetch from UniFi API
            _LOGGER.debug("Updating UniFi People Pointer data")
            
            return {
                "people": self._people,
                "devices": self._devices,
                "unknown_devices": self._unknown_devices,
            }
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error communicating with UniFi: {err}") from err

    # Service handler methods (stubs for now)
    
    async def assign_device(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None = None,
    ) -> None:
        """Assign a device to a person."""
        _LOGGER.info(
            "Assigning device %s to person %s as %s (stub)",
            mac,
            person,
            device_type,
        )
        # Stub: Would write to people.json and devices.json
        if person not in self._people:
            self._people[person] = {
                "id": person,
                "name": person.title(),
                "primary_device": None,
                "secondary_devices": [],
            }
        
        if device_type == "primary":
            self._people[person]["primary_device"] = mac
        else:
            if mac not in self._people[person]["secondary_devices"]:
                self._people[person]["secondary_devices"].append(mac)
        
        await self.async_request_refresh()

    async def track_device(
        self,
        mac: str,
        name: str,
        device_type: str = "other",
    ) -> None:
        """Start tracking a device."""
        _LOGGER.info("Tracking device %s as %s (stub)", mac, name)
        # Stub: Would write to devices.json
        self._devices[mac] = {
            "mac": mac,
            "name": name,
            "type": device_type,
            "connected": False,
        }
        await self.async_request_refresh()

    async def remove_device(self, mac: str) -> None:
        """Remove a device from tracking."""
        _LOGGER.info("Removing device %s (stub)", mac)
        # Stub: Would remove from people.json and devices.json
        self._devices.pop(mac, None)
        
        # Remove from people assignments
        for person_data in self._people.values():
            if person_data.get("primary_device") == mac:
                person_data["primary_device"] = None
            if mac in person_data.get("secondary_devices", []):
                person_data["secondary_devices"].remove(mac)
        
        await self.async_request_refresh()

    async def force_update_person(self, person: str) -> None:
        """Force update a specific person's state."""
        _LOGGER.info("Force updating person %s (stub)", person)
        await self.async_request_refresh()

    async def claim_unknown_device(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None = None,
    ) -> None:
        """Claim an unknown device."""
        _LOGGER.info(
            "Claiming unknown device %s for person %s (stub)",
            mac,
            person,
        )
        # Stub: Would remove from unknown_devices and add to person
        self._unknown_devices = [d for d in self._unknown_devices if d.get("mac") != mac]
        
        await self.assign_device(mac, person, device_type, device_name)

    # Template helper methods (stubs for now)
    
    def get_person_state(self, person_id: str) -> str:
        """Get state of a person."""
        person_data = self._people.get(person_id)
        if not person_data:
            return STATE_AWAY
        
        # Stub: Would check actual device connection status
        primary_device = person_data.get("primary_device")
        if primary_device and self._devices.get(primary_device, {}).get("connected"):
            return STATE_HOME
        
        return STATE_AWAY

    def is_device_connected(self, mac: str) -> bool:
        """Check if device is connected."""
        device = self._devices.get(mac)
        return device.get("connected", False) if device else False

    def get_person_zone(self, person_id: str) -> str | None:
        """Get current zone of a person."""
        if self.get_person_state(person_id) != STATE_HOME:
            return None
        
        # Stub: Would return actual zone from AP mapping
        return "home"

    def get_device_signal(self, mac: str) -> int | None:
        """Get signal strength of a device."""
        device = self._devices.get(mac)
        if not device or not device.get("connected"):
            return None
        
        # Stub: Would return actual signal from UniFi
        return device.get("signal_strength")

    def get_person_devices(self, person_id: str) -> dict[str, Any]:
        """Get all devices for a person."""
        person_data = self._people.get(person_id)
        if not person_data:
            return {"primary": None, "secondary": []}
        
        return {
            "primary": person_data.get("primary_device"),
            "secondary": person_data.get("secondary_devices", []),
        }
