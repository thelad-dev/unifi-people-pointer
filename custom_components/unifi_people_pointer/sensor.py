"""Sensor platform for UniFi People Pointer."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AUTO_DISMISS_DAYS, DOMAIN
from .coordinator import UniFiPeoplePointerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UniFi People Pointer sensors from config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: UniFiPeoplePointerCoordinator = runtime["coordinator"]

    entities = [
        UniFiUnknownClientsSensor(coordinator),
        UniFiGuestClientsSensor(coordinator),
    ]

    async_add_entities(entities)
    _LOGGER.info("Added %d sensor entities", len(entities))


class UniFiUnknownClientsSensor(
    CoordinatorEntity[UniFiPeoplePointerCoordinator], SensorEntity
):
    """Sensor for unknown WiFi clients."""

    _attr_name = "Unknown WiFi Clients"
    _attr_unique_id = f"{DOMAIN}_unknown_clients"

    def __init__(self, coordinator: UniFiPeoplePointerCoordinator) -> None:
        """Initialize the unknown clients sensor."""
        super().__init__(coordinator)
        self._unknown_clients: list[dict[str, Any]] = []
        self._first_seen: dict[str, str] = {}

    @property
    def native_value(self) -> int:
        """Return count of unknown clients."""
        return len(self._unknown_clients)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return {
            "clients": [
                {
                    "mac": client.get("mac"),
                    "ip": client.get("ip"),
                    "hostname": client.get("hostname"),
                    "first_seen": client.get("first_seen"),
                    "last_seen": client.get("last_seen"),
                    "signal_strength": client.get("signal")
                    or client.get("signal_strength"),
                    "ap_mac": client.get("ap_mac"),
                }
                for client in self._unknown_clients
            ]
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        now_iso = datetime.now().isoformat()
        clients = list(self.coordinator.get_unknown_clients())
        for client in clients:
            mac = client.get("mac")
            if not mac:
                continue
            if mac not in self._first_seen:
                self._first_seen[mac] = now_iso
            client["first_seen"] = self._first_seen[mac]
        self._unknown_clients = clients
        self._auto_dismiss_old_clients()
        self.async_write_ha_state()

    def _auto_dismiss_old_clients(self) -> None:
        """Auto-dismiss unknown clients after configured days."""
        cutoff = datetime.now() - timedelta(days=AUTO_DISMISS_DAYS)
        original_count = len(self._unknown_clients)
        kept = []
        for client in self._unknown_clients:
            first_seen = client.get("first_seen", datetime.now().isoformat())
            try:
                seen_dt = datetime.fromisoformat(str(first_seen))
            except ValueError:
                kept.append(client)
                continue
            if seen_dt > cutoff:
                kept.append(client)
        self._unknown_clients = kept
        dismissed_count = original_count - len(self._unknown_clients)
        if dismissed_count > 0:
            _LOGGER.info(
                "Auto-dismissed %d unknown clients older than %d days",
                dismissed_count,
                AUTO_DISMISS_DAYS,
            )


class UniFiGuestClientsSensor(
    CoordinatorEntity[UniFiPeoplePointerCoordinator], SensorEntity
):
    """Sensor for guest WiFi clients."""

    _attr_name = "Guest WiFi Clients"
    _attr_unique_id = f"{DOMAIN}_guest_clients"

    def __init__(self, coordinator: UniFiPeoplePointerCoordinator) -> None:
        """Initialize the guest clients sensor."""
        super().__init__(coordinator)
        self._guest_clients: list[dict[str, Any]] = []

    @property
    def native_value(self) -> int:
        """Return count of guest clients."""
        return len(self._guest_clients)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return {
            "clients": [
                {
                    "mac": client.get("mac"),
                    "ip": client.get("ip"),
                    "hostname": client.get("hostname"),
                    "last_seen": client.get("last_seen"),
                    "signal_strength": client.get("signal")
                    or client.get("signal_strength"),
                    "ap_mac": client.get("ap_mac"),
                }
                for client in self._guest_clients
            ]
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._guest_clients = list(self.coordinator.get_guest_clients())
        self.async_write_ha_state()
