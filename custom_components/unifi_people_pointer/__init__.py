"""UniFi People Pointer integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    CONF_EVENT_DEBOUNCE,
    DEFAULT_EVENT_DEBOUNCE,
)
from .coordinator import UniFiPeoplePointerCoordinator
from .events import UniFiEventManager
from .services import setup_services, unregister_services
from .template_helpers import setup_template_helpers, unregister_template_helpers

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    # Platform.DEVICE_TRACKER,
    # Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi People Pointer from a config entry."""
    _LOGGER.info("Setting up UniFi People Pointer")

    # Get config values
    poll_interval = entry.options.get(
        CONF_POLL_INTERVAL,
        entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
    )
    event_debounce = entry.options.get(
        CONF_EVENT_DEBOUNCE,
        entry.data.get(CONF_EVENT_DEBOUNCE, DEFAULT_EVENT_DEBOUNCE),
    )

    # Create coordinator
    coordinator = UniFiPeoplePointerCoordinator(
        hass,
        update_interval=timedelta(seconds=poll_interval),
    )

    # Create event manager
    event_manager = UniFiEventManager(hass, debounce_seconds=event_debounce)

    # Store coordinator and event manager
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {
        "coordinator": coordinator,
        "event_manager": event_manager,
        "config_entry": entry,
    }

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Set up platforms
    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    setup_services(hass)

    # Register template helpers
    setup_template_helpers(hass)

    _LOGGER.info("UniFi People Pointer setup complete")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading UniFi People Pointer")

    # Unload platforms
    unload_ok = True
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Unregister services
    unregister_services(hass)

    # Unregister template helpers
    unregister_template_helpers(hass)

    # Remove data
    if unload_ok:
        hass.data[DOMAIN].pop("coordinator", None)
        hass.data[DOMAIN].pop("event_manager", None)
        hass.data[DOMAIN].pop("config_entry", None)

    _LOGGER.info("UniFi People Pointer unloaded")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
