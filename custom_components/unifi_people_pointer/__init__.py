"""UniFi People Pointer integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_WEBUI_PORT, DEFAULT_EVENT_DEBOUNCE, DEFAULT_WEBUI_PORT, DOMAIN
from .coordinator import UniFiPeoplePointerCoordinator
from .events import UniFiEventManager
from .services import setup_services, unregister_services
from .webui import (
    WebUIServer,
    async_register_panel,
    async_remove_panel,
    async_webui_url,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi People Pointer from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = UniFiPeoplePointerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    debounce = int(entry.options.get("event_debounce", DEFAULT_EVENT_DEBOUNCE))
    event_manager = UniFiEventManager(hass, debounce_seconds=debounce)

    port = int(entry.options.get(CONF_WEBUI_PORT, DEFAULT_WEBUI_PORT))
    webui = WebUIServer(hass, coordinator, port)
    await webui.async_start()

    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "coordinator": coordinator,
        "webui": webui,
        "webui_url": await async_webui_url(hass, port) if webui.running else None,
    }
    # Services resolve the active coordinator here.
    hass.data[DOMAIN]["coordinator"] = coordinator
    hass.data[DOMAIN]["event_manager"] = event_manager

    if "services_registered" not in hass.data[DOMAIN]:
        setup_services(hass)
        hass.data[DOMAIN]["services_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if webui.running:
        await _async_setup_panel(hass, port)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(
        "UniFi People Pointer ready for host %s (%d people, %d devices)",
        entry.data.get("host"),
        len(coordinator.people),
        len(coordinator.devices),
    )
    return True


async def _async_setup_panel(hass: HomeAssistant, port: int) -> None:
    """Add the sidebar panel once the frontend is up (it always is in a real HA)."""
    if hass.http is None or "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded; skipping UniFi People Pointer panel")
        return
    try:
        await async_register_panel(hass, port)
    except Exception:  # noqa: BLE001 - the UI stays reachable on its own port
        _LOGGER.exception("Could not register the UniFi People Pointer panel")


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None) or {}
        webui = runtime.get("webui")
        if webui is not None:
            if webui.running:
                async_remove_panel(hass)
            await webui.async_stop()
        # Drop shared pointers when no entries remain.
        shared_keys = (
            "coordinator",
            "event_manager",
            "services_registered",
            "unknown_first_seen",
            "unknown_dismissed",
            "panel_static_registered",
        )
        remaining = [key for key in hass.data.get(DOMAIN, {}) if key not in shared_keys]
        if not remaining:
            event_manager = hass.data.get(DOMAIN, {}).get("event_manager")
            if event_manager is not None:
                event_manager.cancel_all()
            if hass.data.get(DOMAIN, {}).get("services_registered"):
                unregister_services(hass)
            # Keep unknown client bookkeeping across config-entry reload.
            first_seen = hass.data.get(DOMAIN, {}).get("unknown_first_seen") or {}
            dismissed = hass.data.get(DOMAIN, {}).get("unknown_dismissed") or {}
            static_registered = hass.data.get(DOMAIN, {}).get("panel_static_registered")
            hass.data[DOMAIN] = {
                "unknown_first_seen": first_seen,
                "unknown_dismissed": dismissed,
            }
            # A static path cannot be unregistered; remember it across reloads.
            if static_registered:
                hass.data[DOMAIN]["panel_static_registered"] = True

    return unload_ok
