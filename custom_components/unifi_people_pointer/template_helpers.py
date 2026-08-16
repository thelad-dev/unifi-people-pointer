"""Template helpers for UniFi People Pointer."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN, STATE_HOME

_LOGGER = logging.getLogger(__name__)


def setup_template_helpers(hass: HomeAssistant) -> None:
    """Set up Jinja2 template helper functions."""

    def unifi_person_home(person_id: str) -> bool:
        """
        Check if a person is home.

        Usage in templates:
            {{ unifi_person_home('sebastian') }}

        Args:
            person_id: Person identifier (slug)

        Returns:
            True if person is home, False otherwise
        """
        coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
        if not coordinator:
            _LOGGER.warning("UniFi People Pointer coordinator not found")
            return False

        try:
            person_state = coordinator.get_person_state(person_id)
            return person_state == STATE_HOME
        except Exception as err:
            _LOGGER.error("Error checking person state for %s: %s", person_id, err)
            return False

    def unifi_device_connected(mac: str) -> bool:
        """
        Check if a device is connected.

        Usage in templates:
            {{ unifi_device_connected('AA:BB:CC:DD:EE:FF') }}

        Args:
            mac: Device MAC address

        Returns:
            True if device is connected, False otherwise
        """
        coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
        if not coordinator:
            _LOGGER.warning("UniFi People Pointer coordinator not found")
            return False

        try:
            return coordinator.is_device_connected(mac)
        except Exception as err:
            _LOGGER.error("Error checking device state for %s: %s", mac, err)
            return False

    def unifi_person_zone(person_id: str) -> str | None:
        """
        Get the current zone of a person.

        Usage in templates:
            {{ unifi_person_zone('sebastian') }}

        Args:
            person_id: Person identifier (slug)

        Returns:
            Zone name (e.g., 'eg', 'og') or None if not home
        """
        coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
        if not coordinator:
            _LOGGER.warning("UniFi People Pointer coordinator not found")
            return None

        try:
            return coordinator.get_person_zone(person_id)
        except Exception as err:
            _LOGGER.error("Error getting zone for %s: %s", person_id, err)
            return None

    def unifi_device_signal(mac: str) -> int | None:
        """
        Get signal strength of a device in dBm.

        Usage in templates:
            {{ unifi_device_signal('AA:BB:CC:DD:EE:FF') }}

        Args:
            mac: Device MAC address

        Returns:
            Signal strength in dBm (e.g., -45) or None if not connected
        """
        coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
        if not coordinator:
            _LOGGER.warning("UniFi People Pointer coordinator not found")
            return None

        try:
            return coordinator.get_device_signal(mac)
        except Exception as err:
            _LOGGER.error("Error getting signal for %s: %s", mac, err)
            return None

    def unifi_person_devices(person_id: str) -> dict[str, Any]:
        """
        Get all devices for a person.

        Usage in templates:
            {{ unifi_person_devices('sebastian') }}

        Args:
            person_id: Person identifier (slug)

        Returns:
            Dict with 'primary' and 'secondary' device lists
        """
        coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
        if not coordinator:
            _LOGGER.warning("UniFi People Pointer coordinator not found")
            return {"primary": None, "secondary": []}

        try:
            return coordinator.get_person_devices(person_id)
        except Exception as err:
            _LOGGER.error("Error getting devices for %s: %s", person_id, err)
            return {"primary": None, "secondary": []}

    # Register template functions
    hass.data.setdefault("template_functions", {})
    hass.data["template_functions"]["unifi_person_home"] = unifi_person_home
    hass.data["template_functions"]["unifi_device_connected"] = unifi_device_connected
    hass.data["template_functions"]["unifi_person_zone"] = unifi_person_zone
    hass.data["template_functions"]["unifi_device_signal"] = unifi_device_signal
    hass.data["template_functions"]["unifi_person_devices"] = unifi_person_devices

    _LOGGER.info("UniFi People Pointer template helpers registered")


def unregister_template_helpers(hass: HomeAssistant) -> None:
    """Unregister template helper functions."""
    template_functions = hass.data.get("template_functions", {})
    template_functions.pop("unifi_person_home", None)
    template_functions.pop("unifi_device_connected", None)
    template_functions.pop("unifi_person_zone", None)
    template_functions.pop("unifi_device_signal", None)
    template_functions.pop("unifi_person_devices", None)

    _LOGGER.info("UniFi People Pointer template helpers unregistered")
