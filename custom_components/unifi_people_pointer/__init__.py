"""UniFi People Pointer integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .const import DEFAULT_EVENT_DEBOUNCE, DOMAIN
from .coordinator import UniFiPeoplePointerCoordinator
from .events import UniFiEventManager
from .services import setup_services, unregister_services
from .template_helpers import setup_template_helpers

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi People Pointer from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = UniFiPeoplePointerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    debounce = int(
        entry.options.get("event_debounce", DEFAULT_EVENT_DEBOUNCE)
    )
    event_manager = UniFiEventManager(hass, debounce_seconds=debounce)

    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "coordinator": coordinator,
    }
    # Services and template helpers resolve the active coordinator here.
    hass.data[DOMAIN]["coordinator"] = coordinator
    hass.data[DOMAIN]["event_manager"] = event_manager

    if "services_registered" not in hass.data[DOMAIN]:
        setup_services(hass)
        setup_template_helpers(hass)
        hass.data[DOMAIN]["services_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "UniFi People Pointer ready for host %s (%d people, %d devices)",
        entry.data.get("host"),
        len(coordinator.people),
        len(coordinator.devices),
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        # Drop shared pointers when no entries remain.
        shared_keys = (
            "coordinator",
            "event_manager",
            "services_registered",
            "unknown_first_seen",
        )
        remaining = [
            key
            for key in hass.data.get(DOMAIN, {})
            if key not in shared_keys
        ]
        if not remaining:
            event_manager = hass.data.get(DOMAIN, {}).get("event_manager")
            if event_manager is not None:
                event_manager.cancel_all()
            if hass.data.get(DOMAIN, {}).get("services_registered"):
                unregister_services(hass)
            # Keep unknown_first_seen across config-entry reload.
            first_seen = hass.data.get(DOMAIN, {}).get("unknown_first_seen") or {}
            hass.data[DOMAIN] = {"unknown_first_seen": first_seen}

    return unload_ok
