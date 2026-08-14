"""Data update coordinator for UniFi People Pointer."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_SITE_ID,
    CONF_VERIFY_SSL,
    DEFAULT_SITE_ID,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class UniFiPeoplePointerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching UniFi data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.entry = entry
        self.config = entry.data
        
        # UniFi connection details
        self.host = self.config[CONF_HOST]
        self.api_key = self.config[CONF_API_KEY]
        self.site_id = self.config.get(CONF_SITE_ID, DEFAULT_SITE_ID)
        self.verify_ssl = self.config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        
        # Initialize data storage
        self.clients: list[dict[str, Any]] = []
        self.access_points: list[dict[str, Any]] = []
        self.people_data: dict[str, Any] = {}
        self.devices_data: dict[str, Any] = {}
        
        _LOGGER.info(
            "Initialized coordinator for %s (poll interval: %s)",
            self.host,
            update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from UniFi Controller."""
        try:
            # TODO: Implement actual UniFi API client
            # For now, return mock data structure
            _LOGGER.debug("Fetching data from UniFi Controller: %s", self.host)
            
            # Simulate API call delay
            # await asyncio.sleep(0.1)
            
            # Mock data for initial structure
            data = {
                "clients": [],
                "access_points": [],
                "timestamp": datetime.now(),
            }
            
            self.clients = data["clients"]
            self.access_points = data["access_points"]
            
            _LOGGER.debug(
                "Fetched %d clients and %d access points",
                len(self.clients),
                len(self.access_points),
            )
            
            return data

        except Exception as err:
            _LOGGER.error("Error communicating with UniFi Controller: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_get_client_by_mac(self, mac: str) -> dict[str, Any] | None:
        """Get client by MAC address."""
        for client in self.clients:
            if client.get("mac", "").lower() == mac.lower():
                return client
        return None

    async def async_get_access_point_by_mac(self, mac: str) -> dict[str, Any] | None:
        """Get access point by MAC address."""
        for ap in self.access_points:
            if ap.get("mac", "").lower() == mac.lower():
                return ap
        return None

    def is_device_online(self, mac: str) -> bool:
        """Check if device is currently online in UniFi."""
        for client in self.clients:
            if client.get("mac", "").lower() == mac.lower():
                return True
        return False
