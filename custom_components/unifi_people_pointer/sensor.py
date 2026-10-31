"""Sensor platform for UniFi People Pointer."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
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

    # Service device on the integration page; its link opens the web UI.
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="UniFi People Pointer",
        manufacturer="UniFi People Pointer",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=runtime.get("webui_url"),
    )
    entities = [
        UniFiUnknownClientsSensor(coordinator),
        UniFiGuestClientsSensor(coordinator),
    ]
    for entity in entities:
        entity._attr_device_info = device_info

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
        domain_data = coordinator.hass.data.setdefault(DOMAIN, {})
        self._first_seen: dict[str, str] = domain_data.setdefault(
            "unknown_first_seen", {}
        )
        self._dismissed: dict[str, str] = domain_data.setdefault(
            "unknown_dismissed", {}
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener and seed from current data."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

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
                    "ap_name": self.coordinator.get_client_ap_name(client),
                }
                for client in self._unknown_clients
            ]
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        now = datetime.now()
        now_iso = now.isoformat()
        cutoff = now - timedelta(days=AUTO_DISMISS_DAYS)
        clients = list(self.coordinator.get_unknown_clients())
        current_macs: set[str] = set()
        kept: list[dict[str, Any]] = []
        dismissed_count = 0

        for client in clients:
            mac = client.get("mac")
            if not mac:
                continue
            current_macs.add(mac)

            # Stay hidden while continuously present after age-dismiss.
            if mac in self._dismissed:
                continue

            if mac not in self._first_seen:
                self._first_seen[mac] = now_iso
            client["first_seen"] = self._first_seen[mac]

            try:
                seen_dt = datetime.fromisoformat(str(self._first_seen[mac]))
            except ValueError:
                kept.append(client)
                continue

            if seen_dt > cutoff:
                kept.append(client)
                continue

            self._dismissed[mac] = now_iso
            dismissed_count += 1

        # MAC left unknown (claimed/matched or offline): allow fresh cycle later.
        for mac in list(self._first_seen):
            if mac not in current_macs:
                self._first_seen.pop(mac, None)
        for mac in list(self._dismissed):
            if mac not in current_macs:
                self._dismissed.pop(mac, None)

        self._unknown_clients = kept
        if dismissed_count > 0:
            _LOGGER.info(
                "Auto-dismissed %d unknown clients older than %d days",
                dismissed_count,
                AUTO_DISMISS_DAYS,
            )
        self.async_write_ha_state()


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

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener and seed from current data."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

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
                    "ap_name": self.coordinator.get_client_ap_name(client),
                }
                for client in self._guest_clients
            ]
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._guest_clients = list(self.coordinator.get_guest_clients())
        self.async_write_ha_state()
