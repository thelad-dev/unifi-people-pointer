"""Entities show the access point a device is connected to."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_people_pointer.api_parser import (
    parse_access_point_names,
    parse_clients,
)
from custom_components.unifi_people_pointer.const import DOMAIN, STORAGE_DIR
from custom_components.unifi_people_pointer.coordinator import (
    UniFiPeoplePointerCoordinator,
)
from custom_components.unifi_people_pointer.device_tracker import name_with_ap

pytestmark = pytest.mark.integration

COORD = (
    "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator"
)
AP_NAMES = {"24:5a:4c:aa:bb:cc": "EG-Diele", "24:5a:4c:aa:bb:dd": "OG-Flur"}


async def _setup(hass, devices_data, people_data, clients, ap_names=AP_NAMES):
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.88.1", "token": "test-token", "verify_ssl": False},
        options={"event_debounce": 0},
        title="UniFi People Pointer",
        unique_id="ap-names",
    )
    entry.add_to_hass(hass)
    fetch_clients = AsyncMock(return_value=clients)
    fetch_aps = AsyncMock(return_value=dict(ap_names))
    with patch(f"{COORD}._fetch_clients", new=fetch_clients), patch(
        f"{COORD}._fetch_access_points", new=fetch_aps
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry, fetch_clients, fetch_aps


async def _refresh(hass, clients, ap_names=AP_NAMES):
    coordinator = hass.data[DOMAIN]["coordinator"]
    fetch_aps = AsyncMock(return_value=dict(ap_names))
    with patch(f"{COORD}._fetch_clients", new=AsyncMock(return_value=clients)), patch(
        f"{COORD}._fetch_access_points", new=fetch_aps
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
    return fetch_aps


def test_name_with_ap_format():
    """Format matches the requested display: '<name> AP: <ap>'."""
    assert name_with_ap("iPhone-SKHL", "EG-Diele") == "iPhone-SKHL AP: EG-Diele"
    assert name_with_ap("iPhone-SKHL", None) == "iPhone-SKHL"
    assert name_with_ap(None, "EG-Diele") is None


def test_parse_access_point_names_classic_and_integration_rows():
    """Classic rows key by MAC; integration rows also by device id."""
    names = parse_access_point_names(
        [
            {"mac": "24:5A:4C:AA:BB:CC", "name": "EG-Diele", "type": "uap"},
            {"id": "6A1B-UUID", "macAddress": "24-5a-4c-aa-bb-dd", "name": "OG-Flur"},
            {"mac": "24:5a:4c:aa:bb:ee", "name": ""},
            "garbage",
        ]
    )
    assert names == {
        "24:5a:4c:aa:bb:cc": "EG-Diele",
        "24:5a:4c:aa:bb:dd": "OG-Flur",
        "6a1b-uuid": "OG-Flur",
    }


async def test_tracker_names_show_ap_and_follow_roaming(
    hass, devices_data, people_data, mock_unifi_api_clients_online
):
    """Device and person trackers carry ' AP: <name>' and update on AP change."""
    await _setup(hass, devices_data, people_data, mock_unifi_api_clients_online)

    phone = hass.states.get("device_tracker.iphone_skhl")
    assert phone is not None
    assert phone.attributes["friendly_name"] == "iPhone-SKHL AP: EG-Diele"
    assert phone.attributes["ap_name"] == "EG-Diele"
    assert phone.attributes["ap_mac"] == "24:5a:4c:aa:bb:cc"

    sebastian = hass.states.get("device_tracker.sebastian")
    assert sebastian.attributes["friendly_name"] == "Sebastian AP: EG-Diele"
    assert sebastian.attributes["ap_name"] == "EG-Diele"

    roamed = copy.deepcopy(mock_unifi_api_clients_online)
    for client in roamed:
        if client["hostname"] == "iPhone-SKHL":
            client["ap_mac"] = "24:5a:4c:aa:bb:dd"
    await _refresh(hass, roamed)
    phone = hass.states.get("device_tracker.iphone_skhl")
    assert phone.attributes["friendly_name"] == "iPhone-SKHL AP: OG-Flur"
    assert phone.attributes["ap_name"] == "OG-Flur"


async def test_tracker_name_drops_ap_when_away(
    hass, devices_data, people_data, mock_unifi_api_clients_online
):
    """Away devices show their plain name and no AP."""
    await _setup(hass, devices_data, people_data, mock_unifi_api_clients_online)
    await _refresh(hass, [])

    phone = hass.states.get("device_tracker.iphone_skhl")
    assert phone.state == "not_home"
    assert phone.attributes["friendly_name"] == "iPhone-SKHL"
    assert phone.attributes["ap_name"] is None
    sebastian = hass.states.get("device_tracker.sebastian")
    assert sebastian.attributes["friendly_name"] == "Sebastian"


async def test_entity_ids_do_not_include_ap_name(
    hass, devices_data, people_data, mock_unifi_api_clients_online
):
    """New registrations use the base name for the object id."""
    await _setup(hass, devices_data, people_data, mock_unifi_api_clients_online)
    registry = er.async_get(hass)
    ids = {
        entry.entity_id
        for entry in registry.entities.values()
        if entry.platform == DOMAIN and entry.domain == "device_tracker"
    }
    assert "device_tracker.iphone_skhl" in ids
    assert "device_tracker.sebastian" in ids
    assert not any("_ap_" in entity_id for entity_id in ids)


async def test_unknown_sensor_lists_ap_name(hass, devices_data, people_data):
    """Unknown clients carry the AP name next to the AP MAC."""
    clients = [
        {
            "mac": "aa:aa:aa:00:00:01",
            "hostname": "stranger",
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:dd",
            "signal": -70,
        }
    ]
    await _setup(hass, devices_data, people_data, clients)
    sensor = hass.states.get("sensor.unknown_wifi_clients")
    assert sensor.attributes["clients"][0]["ap_name"] == "OG-Flur"
    assert sensor.attributes["clients"][0]["ap_mac"] == "24:5a:4c:aa:bb:dd"


async def test_last_uplink_name_is_fallback(hass, devices_data, people_data):
    """Without a device list entry the client's own uplink name is used."""
    clients = [
        {
            "mac": "38:7f:8b:da:18:20",
            "hostname": "iPhone-SKHL",
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:99",
            "last_uplink_name": "Garten-AP",
        }
    ]
    await _setup(hass, devices_data, people_data, clients, ap_names={})
    phone = hass.states.get("device_tracker.iphone_skhl")
    assert phone.attributes["friendly_name"] == "iPhone-SKHL AP: Garten-AP"


async def test_ap_list_refetch_policy(
    hass, devices_data, people_data, mock_unifi_api_clients_online
):
    """Fetch on unknown AP only; nameless APs and fetch errors do not loop."""
    _, _, first_fetch = await _setup(
        hass, devices_data, people_data, mock_unifi_api_clients_online
    )
    assert first_fetch.await_count == 1

    # Same APs: no new fetch.
    fetch = await _refresh(hass, mock_unifi_api_clients_online)
    assert fetch.await_count == 0

    # New AP appears: fetch once; still unnamed afterwards: no further fetch.
    new_ap = copy.deepcopy(mock_unifi_api_clients_online)
    new_ap[0]["ap_mac"] = "24:5a:4c:aa:bb:ff"
    fetch = await _refresh(hass, new_ap)
    assert fetch.await_count == 1
    fetch = await _refresh(hass, new_ap)
    assert fetch.await_count == 0

    # Errors keep the previous names.
    coordinator = hass.data[DOMAIN]["coordinator"]
    coordinator._ap_names_fetched_at = 0.0
    with patch(
        f"{COORD}._fetch_clients",
        new=AsyncMock(return_value=mock_unifi_api_clients_online),
    ), patch(f"{COORD}._fetch_access_points", new=AsyncMock(side_effect=OSError)):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
    assert coordinator.get_ap_name("24:5a:4c:aa:bb:cc") == "EG-Diele"


@pytest.mark.real_ap_fetch
async def test_fetch_access_points_classic_then_integration(hass, mock_config_entry):
    """Classic device list first; integration API devices as fallback."""
    mock_config_entry.add_to_hass(hass)
    coordinator = UniFiPeoplePointerCoordinator(hass, mock_config_entry)
    # DataUpdateCoordinator picks the entry from the setup context.
    coordinator.config_entry = mock_config_entry
    base = "https://192.168.88.1/proxy/network"

    with aioresponses() as mocked:
        mocked.get(
            f"{base}/api/s/default/stat/device-basic",
            payload={
                "meta": {"rc": "ok"},
                "data": [{"mac": "24:5a:4c:aa:bb:cc", "name": "EG-Diele"}],
            },
        )
        assert await coordinator._fetch_access_points() == {
            "24:5a:4c:aa:bb:cc": "EG-Diele"
        }

    with aioresponses() as mocked:
        mocked.get(f"{base}/api/s/default/stat/device-basic", status=404)
        mocked.get(f"{base}/api/s/default/stat/device", status=404)
        mocked.get(
            f"{base}/integration/v1/sites",
            payload={"data": [{"id": "site-uuid", "internalReference": "default"}]},
        )
        mocked.get(
            f"{base}/integration/v1/sites/site-uuid/devices?limit=200",
            payload={
                "data": [
                    {
                        "id": "DEV-1",
                        "macAddress": "24:5a:4c:aa:bb:dd",
                        "name": "OG-Flur",
                    }
                ]
            },
        )
        names = await coordinator._fetch_access_points()
    assert names == {"24:5a:4c:aa:bb:dd": "OG-Flur", "dev-1": "OG-Flur"}

    # Integration API clients reference the AP by device id.
    client = parse_clients(
        [
            {
                "macAddress": "38:7f:8b:da:18:20",
                "type": "WIRELESS",
                "uplinkDeviceId": "DEV-1",
            }
        ]
    )[0]
    coordinator._ap_names = names
    assert coordinator.get_client_ap_name(client) == "OG-Flur"
