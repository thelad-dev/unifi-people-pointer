"""Service handlers for UniFi People Pointer."""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DEVICE_TYPE_PRIMARY,
    DEVICE_TYPE_SECONDARY,
    DOMAIN,
    SERVICE_ASSIGN_DEVICE,
    SERVICE_CLAIM_UNKNOWN_DEVICE,
    SERVICE_FORCE_UPDATE_PERSON,
    SERVICE_REMOVE_DEVICE,
    SERVICE_SCAN_NOW,
    SERVICE_TRACK_DEVICE,
)

_LOGGER = logging.getLogger(__name__)


# Service schemas
ASSIGN_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
        vol.Required("person"): cv.string,
        vol.Required("device_type"): vol.In(
            [DEVICE_TYPE_PRIMARY, DEVICE_TYPE_SECONDARY]
        ),
        vol.Optional("device_name"): cv.string,
    }
)

TRACK_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
        vol.Required("name"): cv.string,
        vol.Optional("device_type"): vol.In(
            ["smartphone", "laptop", "tablet", "desktop", "iot", "other"]
        ),
    }
)

REMOVE_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
    }
)

SCAN_NOW_SCHEMA = vol.Schema(
    {
        vol.Optional("target", default="all"): cv.string,
    }
)

FORCE_UPDATE_PERSON_SCHEMA = vol.Schema(
    {
        vol.Required("person"): cv.string,
    }
)

CLAIM_UNKNOWN_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
        vol.Required("person"): cv.string,
        vol.Required("device_type"): vol.In(
            [DEVICE_TYPE_PRIMARY, DEVICE_TYPE_SECONDARY]
        ),
        vol.Optional("device_name"): cv.string,
    }
)


def setup_services(hass: HomeAssistant) -> None:
    """Set up services for UniFi People Pointer."""

    async def handle_assign_device(call: ServiceCall) -> None:
        """Handle assign_device service call."""
        mac = call.data["mac"]
        person = call.data["person"]
        device_type = call.data["device_type"]
        device_name = call.data.get("device_name")

        _LOGGER.info(
            "Assigning device %s to person %s as %s",
            mac,
            person,
            device_type,
        )

        # Get coordinator from hass.data
        coordinator = hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            raise HomeAssistantError("UniFi People Pointer not initialized")

        try:
            await coordinator.assign_device(mac, person, device_type, device_name)
            _LOGGER.info("Successfully assigned device %s to %s", mac, person)
        except Exception as err:
            _LOGGER.error("Error assigning device: %s", err)
            raise HomeAssistantError(f"Failed to assign device: {err}") from err

    async def handle_track_device(call: ServiceCall) -> None:
        """Handle track_device service call."""
        mac = call.data["mac"]
        name = call.data["name"]
        device_type = call.data.get("device_type", "other")

        _LOGGER.info("Starting to track device %s (%s)", mac, name)

        coordinator = hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            raise HomeAssistantError("UniFi People Pointer not initialized")

        try:
            await coordinator.track_device(mac, name, device_type)
            _LOGGER.info("Successfully tracking device %s", mac)
        except Exception as err:
            _LOGGER.error("Error tracking device: %s", err)
            raise HomeAssistantError(f"Failed to track device: {err}") from err

    async def handle_remove_device(call: ServiceCall) -> None:
        """Handle remove_device service call."""
        mac = call.data["mac"]

        _LOGGER.info("Removing device %s from tracking", mac)

        coordinator = hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            raise HomeAssistantError("UniFi People Pointer not initialized")

        try:
            await coordinator.remove_device(mac)
            _LOGGER.info("Successfully removed device %s", mac)
        except Exception as err:
            _LOGGER.error("Error removing device: %s", err)
            raise HomeAssistantError(f"Failed to remove device: {err}") from err

    async def handle_scan_now(call: ServiceCall) -> None:
        """Handle scan_now service call."""
        target = call.data.get("target", "all")

        _LOGGER.info("Triggering immediate scan (target: %s)", target)

        coordinator = hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            raise HomeAssistantError("UniFi People Pointer not initialized")

        try:
            await coordinator.async_request_refresh()
            _LOGGER.info("Scan completed successfully")
        except Exception as err:
            _LOGGER.error("Error during scan: %s", err)
            raise HomeAssistantError(f"Failed to scan: {err}") from err

    async def handle_force_update_person(call: ServiceCall) -> None:
        """Handle force_update_person service call."""
        person = call.data["person"]

        _LOGGER.info("Forcing update for person %s", person)

        coordinator = hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            raise HomeAssistantError("UniFi People Pointer not initialized")

        try:
            await coordinator.force_update_person(person)
            _LOGGER.info("Successfully updated person %s", person)
        except Exception as err:
            _LOGGER.error("Error updating person: %s", err)
            raise HomeAssistantError(f"Failed to update person: {err}") from err

    async def handle_claim_unknown_device(call: ServiceCall) -> None:
        """Handle claim_unknown_device service call."""
        mac = call.data["mac"]
        person = call.data["person"]
        device_type = call.data["device_type"]
        device_name = call.data.get("device_name")

        _LOGGER.info(
            "Claiming unknown device %s for person %s as %s",
            mac,
            person,
            device_type,
        )

        coordinator = hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            raise HomeAssistantError("UniFi People Pointer not initialized")

        try:
            await coordinator.claim_unknown_device(
                mac, person, device_type, device_name
            )
            _LOGGER.info("Successfully claimed device %s for %s", mac, person)
        except Exception as err:
            _LOGGER.error("Error claiming device: %s", err)
            raise HomeAssistantError(f"Failed to claim device: {err}") from err

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSIGN_DEVICE,
        handle_assign_device,
        schema=ASSIGN_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRACK_DEVICE,
        handle_track_device,
        schema=TRACK_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_DEVICE,
        handle_remove_device,
        schema=REMOVE_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN_NOW,
        handle_scan_now,
        schema=SCAN_NOW_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_UPDATE_PERSON,
        handle_force_update_person,
        schema=FORCE_UPDATE_PERSON_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_UNKNOWN_DEVICE,
        handle_claim_unknown_device,
        schema=CLAIM_UNKNOWN_DEVICE_SCHEMA,
    )

    _LOGGER.info("UniFi People Pointer services registered")


def unregister_services(hass: HomeAssistant) -> None:
    """Unregister services."""
    hass.services.async_remove(DOMAIN, SERVICE_ASSIGN_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_TRACK_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_DEVICE)
    hass.services.async_remove(DOMAIN, SERVICE_SCAN_NOW)
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE_PERSON)
    hass.services.async_remove(DOMAIN, SERVICE_CLAIM_UNKNOWN_DEVICE)
    _LOGGER.info("UniFi People Pointer services unregistered")
