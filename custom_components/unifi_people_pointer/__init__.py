"""UniFi People Pointer integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Platforms stay disabled until coordinator + entity wiring is ready.
# Forwarding too early crashes setup (missing coordinator / stub entities).
PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi People Pointer from a config entry.

    Stores entry runtime data so services/helpers can resolve the integration.
    Platforms are not forwarded yet (Phase 3).
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "coordinator": None,
    }
    _LOGGER.info(
        "UniFi People Pointer configured for host %s (platforms deferred)",
        entry.data.get("host"),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_ok = True

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if DOMAIN in hass.data and not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
