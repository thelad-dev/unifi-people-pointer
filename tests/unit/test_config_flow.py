"""Unit tests for config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.unifi_people_pointer.config_flow import (  # isort: skip
    validate_api_connection,
)

# Form schema uses api_token; entry data stores CONF_TOKEN (homeassistant.const).
CONF_API_TOKEN = "api_token"


@pytest.mark.unit
class TestConfigFlow:
    """Test the config flow for UniFi People Pointer."""

    async def test_user_form_display(self, hass: HomeAssistant):
        """Test that the user form is displayed."""
        result = await hass.config_entries.flow.async_init(
            "unifi_people_pointer", context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "host" in result["data_schema"].schema
        assert "api_token" in result["data_schema"].schema

    async def test_user_form_valid_input(self, hass: HomeAssistant):
        """Test successful configuration with valid input."""
        with patch(
            "custom_components.unifi_people_pointer.config_flow.validate_api_connection",
            return_value={"sites": ["default"]},
        ):
            result = await hass.config_entries.flow.async_init(
                "unifi_people_pointer",
                context={"source": config_entries.SOURCE_USER},
                data={
                    CONF_HOST: "192.168.88.1",
                    CONF_API_TOKEN: "valid_token_12345",
                    "verify_ssl": False,
                },
            )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "UniFi People Pointer"
        assert result["data"][CONF_HOST] == "192.168.88.1"
        assert result["data"][CONF_TOKEN] == "valid_token_12345"

    async def test_user_form_invalid_host(self, hass: HomeAssistant):
        """Test configuration with invalid host."""
        result = await hass.config_entries.flow.async_init(
            "unifi_people_pointer",
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_HOST: "not_a_valid_ip",
                CONF_API_TOKEN: "valid_token_12345",
                "verify_ssl": False,
            },
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert "errors" in result
        assert "host" in result["errors"]

    async def test_user_form_connection_error(self, hass: HomeAssistant):
        """Test configuration when UniFi controller is unreachable."""
        with patch(
            "custom_components.unifi_people_pointer.config_flow.validate_api_connection",
            side_effect=ConnectionError("Cannot connect to UniFi controller"),
        ):
            result = await hass.config_entries.flow.async_init(
                "unifi_people_pointer",
                context={"source": config_entries.SOURCE_USER},
                data={
                    CONF_HOST: "192.168.88.1",
                    CONF_API_TOKEN: "valid_token_12345",
                    "verify_ssl": False,
                },
            )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert "errors" in result
        assert result["errors"]["base"] == "cannot_connect"

    async def test_user_form_invalid_auth(self, hass: HomeAssistant):
        """Test configuration with invalid API token."""
        with patch(
            "custom_components.unifi_people_pointer.config_flow.validate_api_connection",
            side_effect=PermissionError("Invalid API token"),
        ):
            result = await hass.config_entries.flow.async_init(
                "unifi_people_pointer",
                context={"source": config_entries.SOURCE_USER},
                data={
                    CONF_HOST: "192.168.88.1",
                    CONF_API_TOKEN: "invalid_token",
                    "verify_ssl": False,
                },
            )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert "errors" in result
        assert result["errors"]["base"] == "invalid_auth"

    async def test_user_form_timeout(self, hass: HomeAssistant):
        """Test configuration when API request times out."""
        with patch(
            "custom_components.unifi_people_pointer.config_flow.validate_api_connection",
            side_effect=TimeoutError("Request timed out"),
        ):
            result = await hass.config_entries.flow.async_init(
                "unifi_people_pointer",
                context={"source": config_entries.SOURCE_USER},
                data={
                    CONF_HOST: "192.168.88.1",
                    CONF_API_TOKEN: "valid_token_12345",
                    "verify_ssl": False,
                },
            )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert "errors" in result
        assert result["errors"]["base"] == "timeout"

    async def test_user_form_duplicate_entry(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that duplicate config entries are prevented."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.unifi_people_pointer.config_flow.validate_api_connection",
            return_value={"sites": ["default"]},
        ):
            result = await hass.config_entries.flow.async_init(
                "unifi_people_pointer",
                context={"source": config_entries.SOURCE_USER},
                data={
                    CONF_HOST: "192.168.88.1",
                    CONF_API_TOKEN: "valid_token_12345",
                    "verify_ssl": False,
                },
            )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    async def test_options_flow(self, hass: HomeAssistant, mock_config_entry):
        """Test options flow for reconfiguration."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_update_scan_interval(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test updating scan interval via options flow."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"scan_interval": 60}
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert mock_config_entry.options.get("scan_interval") == 60

    async def test_reauth_flow(self, hass: HomeAssistant, mock_config_entry):
        """Test reauthentication flow when token expires."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            "unifi_people_pointer",
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": mock_config_entry.entry_id,
            },
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

    async def test_reauth_flow_success(self, hass: HomeAssistant, mock_config_entry):
        """Test successful reauthentication."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.unifi_people_pointer.config_flow.validate_api_connection",
            return_value={"sites": ["default"]},
        ):
            result = await hass.config_entries.flow.async_init(
                "unifi_people_pointer",
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": mock_config_entry.entry_id,
                },
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_TOKEN: "new_valid_token"}
            )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"


def _mock_sites_response() -> AsyncMock:
    """Return an aiohttp response context that yields a sites payload."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"data": [{"name": "default"}]})
    response.__aenter__.return_value = response
    response.__aexit__.return_value = False
    return response


@pytest.mark.unit
class TestValidateApiConnectionUrl:
    """Test UniFi API URL construction for accepted host forms."""

    @pytest.mark.parametrize(
        ("host", "expected_netloc"),
        [
            ("2001:db8::1", "[2001:db8::1]"),
            ("fe80::1", "[fe80::1]"),
            ("192.168.88.1", "192.168.88.1"),
            ("unifi.local", "unifi.local"),
        ],
    )
    async def test_builds_https_url_with_ipv6_brackets(
        self, host: str, expected_netloc: str
    ) -> None:
        """IPv6 hosts are bracketed; IPv4 and hostnames are unchanged."""
        response = _mock_sites_response()
        session = MagicMock()
        session.get.return_value = response
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "custom_components.unifi_people_pointer.config_flow.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await validate_api_connection(host, "token", False)

        session.get.assert_called_once()
        requested_url = session.get.call_args.args[0]
        assert requested_url == (
            f"https://{expected_netloc}/proxy/network/integration/v1/sites"
        )
        assert result == {"sites": ["default"]}
