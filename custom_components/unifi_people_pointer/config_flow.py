"""Config flow for UniFi People Pointer integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_POLL_INTERVAL,
    CONF_GRACE_PERIOD,
    CONF_ENABLE_MOBILE_APP_FALLBACK,
    CONF_ENABLE_PING_FALLBACK,
    CONF_EVENT_DEBOUNCE,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_EVENT_DEBOUNCE,
)

_LOGGER = logging.getLogger(__name__)


class UniFiPeoplePointerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi People Pointer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
            )

        # Create the config entry with default values
        return self.async_create_entry(
            title="UniFi People Pointer",
            data={
                CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                CONF_GRACE_PERIOD: DEFAULT_GRACE_PERIOD,
                CONF_EVENT_DEBOUNCE: DEFAULT_EVENT_DEBOUNCE,
                CONF_ENABLE_MOBILE_APP_FALLBACK: True,
                CONF_ENABLE_PING_FALLBACK: True,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UniFi People Pointer."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLL_INTERVAL,
                            self.config_entry.data.get(
                                CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=600)),
                    vol.Optional(
                        CONF_GRACE_PERIOD,
                        default=self.config_entry.options.get(
                            CONF_GRACE_PERIOD,
                            self.config_entry.data.get(
                                CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=1800)),
                    vol.Optional(
                        CONF_EVENT_DEBOUNCE,
                        default=self.config_entry.options.get(
                            CONF_EVENT_DEBOUNCE,
                            self.config_entry.data.get(
                                CONF_EVENT_DEBOUNCE, DEFAULT_EVENT_DEBOUNCE
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
                    vol.Optional(
                        CONF_ENABLE_MOBILE_APP_FALLBACK,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_MOBILE_APP_FALLBACK,
                            self.config_entry.data.get(
                                CONF_ENABLE_MOBILE_APP_FALLBACK, True
                            ),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_ENABLE_PING_FALLBACK,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_PING_FALLBACK,
                            self.config_entry.data.get(CONF_ENABLE_PING_FALLBACK, True),
                        ),
                    ): cv.boolean,
                }
            ),
        )
