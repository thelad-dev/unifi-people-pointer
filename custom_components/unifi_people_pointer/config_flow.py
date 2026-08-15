"""Config flow for UniFi People Pointer integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN


async def validate_api_connection(host: str, token: str, verify_ssl: bool) -> dict[str, Any]:
    """Validate the UniFi API connection."""
    # TODO: Implement actual API validation
    raise NotImplementedError("To be implemented in Phase 1-4")


class UniFiPeoplePointerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi People Pointer."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        # TODO: Implement config flow
        raise NotImplementedError("To be implemented in Phase 1-4")

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle reauth flow."""
        # TODO: Implement reauth
        raise NotImplementedError("To be implemented in Phase 1-4")
