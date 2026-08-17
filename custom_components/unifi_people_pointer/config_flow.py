"""Config flow for UniFi People Pointer integration."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_API_TOKEN = "api_token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 45
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600

# Hostname: labels of alnum/hyphen, separated by dots (no underscores).
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
    }
)


def _is_valid_host(host: str) -> bool:
    """Return True if host is a valid IPv4/IPv6 address or DNS hostname."""
    host = host.strip()
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    return bool(_HOSTNAME_RE.match(host))


def _host_for_url(host: str) -> str:
    """Return host as an HTTP URL authority, bracketing IPv6 literals."""
    try:
        if ipaddress.ip_address(host).version == 6:
            return f"[{host}]"
    except ValueError:
        pass
    return host


def _map_api_exception_to_flow_error(err: BaseException) -> str:
    """Map API validation exceptions to config-flow error keys."""
    if isinstance(err, PermissionError):
        return "invalid_auth"
    if isinstance(err, TimeoutError):
        return "timeout"
    if isinstance(err, ConnectionError):
        msg = str(err).lower()
        if "certificate" in msg or "ssl" in msg or "tls" in msg:
            return "ssl_error"
        return "cannot_connect"
    # aiohttp SSL failures often surface as ClientConnectorCertificateError
    err_name = type(err).__name__.lower()
    if "ssl" in err_name or "certificate" in err_name:
        return "ssl_error"
    _LOGGER.exception("Unexpected config flow error")
    return "unknown"


async def validate_api_connection(
    host: str, token: str, verify_ssl: bool
) -> dict[str, Any]:
    """Validate the UniFi Integration API connection.

    Calls ``GET /proxy/network/integration/v1/sites`` with ``X-API-KEY``.

    Raises:
        ConnectionError: Controller unreachable or non-auth HTTP error.
        PermissionError: Invalid API token (401/403).
        TimeoutError: Request timed out.
    """
    url = f"https://{_host_for_url(host)}/proxy/network/integration/v1/sites"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": token,
    }
    timeout = aiohttp.ClientTimeout(total=15)

    # Local UniFi gateways almost always present a self-signed cert that does not
    # match the LAN IP/hostname. When verify_ssl is False, disable TLS verification.
    ssl_param: bool | object = verify_ssl
    if not verify_ssl:
        ssl_param = False

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, ssl=ssl_param) as response:
                if response.status in (401, 403):
                    raise PermissionError("Invalid API token")
                if response.status >= 400:
                    raise ConnectionError(f"UniFi API returned HTTP {response.status}")
                payload = await response.json(content_type=None)
    except (PermissionError, ConnectionError, TimeoutError):
        raise
    except asyncio.TimeoutError as err:
        raise TimeoutError("Request timed out") from err
    except aiohttp.ClientConnectorError as err:
        msg = str(err)
        low = msg.lower()
        if "certificate" in low or "ssl" in low or "tls" in low:
            raise ConnectionError(
                f"SSL certificate error (disable SSL verification for local UniFi): {err}"
            ) from err
        raise ConnectionError(f"Cannot connect to UniFi controller: {err}") from err
    except aiohttp.ClientError as err:
        raise ConnectionError(f"Cannot connect to UniFi controller: {err}") from err
    except Exception as err:
        _LOGGER.exception("Unexpected error validating UniFi API")
        raise ConnectionError(str(err)) from err

    sites: list[str] = []
    if isinstance(payload, dict):
        data = payload.get("data", [])
        if isinstance(data, list):
            for site in data:
                if isinstance(site, dict):
                    name = (
                        site.get("internalReference")
                        or site.get("name")
                        or site.get("id")
                    )
                    if name:
                        sites.append(str(name))
    return {"sites": sites or ["default"]}


class UniFiPeoplePointerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UniFi People Pointer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input.get(CONF_HOST, "")).strip()
            # Form schema key is api_token; tests may also pass CONF_TOKEN.
            token = str(
                user_input.get(CONF_API_TOKEN) or user_input.get(CONF_TOKEN) or ""
            ).strip()
            verify_ssl = bool(user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL))

            if not _is_valid_host(host):
                errors["host"] = "invalid_host"
            else:
                # Abort if the same controller host is already configured.
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_HOST) == host:
                        return self.async_abort(reason="already_configured")

                try:
                    await validate_api_connection(host, token, verify_ssl)
                except Exception as err:  # noqa: BLE001
                    errors["base"] = _map_api_exception_to_flow_error(err)
                else:
                    await self.async_set_unique_id(host.lower())
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="UniFi People Pointer",
                        data={
                            CONF_HOST: host,
                            CONF_TOKEN: token,
                            CONF_VERIFY_SSL: verify_ssl,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth when credentials are invalid."""
        entry_id = self.context.get("entry_id")
        if entry_id:
            self._reauth_entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauthentication with a new API token."""
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry is not None:
            token = str(user_input[CONF_TOKEN]).strip()
            host = self._reauth_entry.data[CONF_HOST]
            verify_ssl = bool(
                self._reauth_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            )

            try:
                await validate_api_connection(host, token, verify_ssl)
            except Exception as err:  # noqa: BLE001
                errors["base"] = _map_api_exception_to_flow_error(err)
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_TOKEN: token},
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UniFiPeoplePointerOptionsFlow:
        """Create the options flow."""
        return UniFiPeoplePointerOptionsFlow(config_entry)


class UniFiPeoplePointerOptionsFlow(config_entries.OptionsFlow):
    """Handle options for UniFi People Pointer."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
