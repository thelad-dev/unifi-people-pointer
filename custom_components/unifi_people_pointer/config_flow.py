"""Config flow for UniFi People Pointer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_API_KEY,
    CONF_ENABLE_MOBILE_APP_FALLBACK,
    CONF_ENABLE_OUI_UPDATE,
    CONF_ENABLE_PING_FALLBACK,
    CONF_EVENT_DEBOUNCE,
    CONF_GRACE_PERIOD,
    CONF_OUI_SOURCE,
    CONF_OUI_UPDATE_INTERVAL,
    CONF_POLL_INTERVAL,
    CONF_SITE_ID,
    CONF_VERIFY_SSL,
    DEFAULT_ENABLE_MOBILE_APP_FALLBACK,
    DEFAULT_ENABLE_OUI_UPDATE,
    DEFAULT_ENABLE_PING_FALLBACK,
    DEFAULT_EVENT_DEBOUNCE,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_OUI_SOURCE,
    DEFAULT_OUI_UPDATE_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SITE_ID,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MAX_EVENT_DEBOUNCE,
    MAX_GRACE_PERIOD,
    MAX_POLL_INTERVAL,
    MIN_EVENT_DEBOUNCE,
    MIN_GRACE_PERIOD,
    MIN_POLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class UniFiPeoplePointerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi People Pointer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_unifi(user_input)

    async def async_step_unifi(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle UniFi connection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate URL format
            if not user_input[CONF_HOST].startswith(("http://", "https://")):
                errors[CONF_HOST] = "invalid_url"
            else:
                # Store UniFi connection data
                self.config_data.update(user_input)
                
                # TODO: Test connection to UniFi API
                # For now, proceed to next step
                return await self.async_step_polling()

        # Show form
        return self.async_show_form(
            step_id="unifi",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Optional(CONF_SITE_ID, default=DEFAULT_SITE_ID): str,
                    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle polling settings step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate grace_period >= poll_interval
            if user_input[CONF_GRACE_PERIOD] < user_input[CONF_POLL_INTERVAL]:
                errors[CONF_GRACE_PERIOD] = "must_be_greater_than_poll"
            else:
                # Store polling data
                self.config_data.update(user_input)
                return await self.async_step_oui()

        # Show form
        return self.async_show_form(
            step_id="polling",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): vol.All(
                        cv.positive_int,
                        vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_GRACE_PERIOD, default=DEFAULT_GRACE_PERIOD
                    ): vol.All(
                        cv.positive_int,
                        vol.Range(min=MIN_GRACE_PERIOD, max=MAX_GRACE_PERIOD),
                    ),
                    vol.Optional(
                        CONF_ENABLE_MOBILE_APP_FALLBACK,
                        default=DEFAULT_ENABLE_MOBILE_APP_FALLBACK,
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_PING_FALLBACK, default=DEFAULT_ENABLE_PING_FALLBACK
                    ): bool,
                    vol.Optional(
                        CONF_EVENT_DEBOUNCE, default=DEFAULT_EVENT_DEBOUNCE
                    ): vol.All(
                        cv.positive_int,
                        vol.Range(min=MIN_EVENT_DEBOUNCE, max=MAX_EVENT_DEBOUNCE),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_oui(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle OUI settings step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store OUI data
            self.config_data.update(user_input)

            # Create config entry
            return self.async_create_entry(
                title="UniFi People Pointer",
                data=self.config_data,
            )

        # Show form
        return self.async_show_form(
            step_id="oui",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_OUI_UPDATE, default=DEFAULT_ENABLE_OUI_UPDATE
                    ): bool,
                    vol.Optional(
                        CONF_OUI_UPDATE_INTERVAL, default=DEFAULT_OUI_UPDATE_INTERVAL
                    ): vol.In(["weekly", "monthly", "never"]),
                    vol.Optional(CONF_OUI_SOURCE, default=DEFAULT_OUI_SOURCE): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UniFiPeoplePointerOptionsFlow:
        """Get the options flow for this handler."""
        return UniFiPeoplePointerOptionsFlow(config_entry)


class UniFiPeoplePointerOptionsFlow(config_entries.OptionsFlow):
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

        # Get current values from config entry
        current_poll_interval = self.config_entry.data.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )
        current_grace_period = self.config_entry.data.get(
            CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD
        )
        current_mobile_app_fallback = self.config_entry.data.get(
            CONF_ENABLE_MOBILE_APP_FALLBACK, DEFAULT_ENABLE_MOBILE_APP_FALLBACK
        )
        current_ping_fallback = self.config_entry.data.get(
            CONF_ENABLE_PING_FALLBACK, DEFAULT_ENABLE_PING_FALLBACK
        )
        current_event_debounce = self.config_entry.data.get(
            CONF_EVENT_DEBOUNCE, DEFAULT_EVENT_DEBOUNCE
        )
        current_oui_update = self.config_entry.data.get(
            CONF_ENABLE_OUI_UPDATE, DEFAULT_ENABLE_OUI_UPDATE
        )
        current_oui_interval = self.config_entry.data.get(
            CONF_OUI_UPDATE_INTERVAL, DEFAULT_OUI_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL, default=current_poll_interval
                    ): vol.All(
                        cv.positive_int,
                        vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_GRACE_PERIOD, default=current_grace_period
                    ): vol.All(
                        cv.positive_int,
                        vol.Range(min=MIN_GRACE_PERIOD, max=MAX_GRACE_PERIOD),
                    ),
                    vol.Optional(
                        CONF_ENABLE_MOBILE_APP_FALLBACK,
                        default=current_mobile_app_fallback,
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_PING_FALLBACK, default=current_ping_fallback
                    ): bool,
                    vol.Optional(
                        CONF_EVENT_DEBOUNCE, default=current_event_debounce
                    ): vol.All(
                        cv.positive_int,
                        vol.Range(min=MIN_EVENT_DEBOUNCE, max=MAX_EVENT_DEBOUNCE),
                    ),
                    vol.Optional(
                        CONF_ENABLE_OUI_UPDATE, default=current_oui_update
                    ): bool,
                    vol.Optional(
                        CONF_OUI_UPDATE_INTERVAL, default=current_oui_interval
                    ): vol.In(["weekly", "monthly", "never"]),
                }
            ),
        )
