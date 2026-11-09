"""Network filter end to end: web UI API, options flow, entities and events."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from homeassistant import data_entry_flow
from homeassistant.const import STATE_UNAVAILABLE
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.unifi_people_pointer.const import (
    DOMAIN,
    EVENT_UNKNOWN_DEVICE,
    STORAGE_DIR,
)
from custom_components.unifi_people_pointer.coordinator import (
    UniFiPeoplePointerCoordinator,
)
from custom_components.unifi_people_pointer.network_filter import UniFiNetwork
from custom_components.unifi_people_pointer.webui import WebUIServer

pytestmark = pytest.mark.integration

COORD = (
    "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator"
)
MAIN_NET = "192.0.2.0/24"
# Example MACs (RFC 7042 documentation range) and a documentation network.
AP_1 = "00:00:5e:00:53:f1"
AP_2 = "00:00:5e:00:53:f2"
FOREIGN = {
    "mac": "00:00:5e:00:53:51",
    "hostname": "neighbour-phone",
    "ip": "198.51.100.20",
    "is_wired": False,
    "ap_mac": AP_2,
    "signal": -80,
}
HOME_UNKNOWN = {
    "mac": "00:00:5e:00:53:01",
    "hostname": "stranger",
    "ip": "192.0.2.150",
    "is_wired": False,
    "ap_mac": AP_2,
    "signal": -70,
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def devices_data():
    """Two tracked phones."""
    return {
        "version": 1,
        "devices": [
            {
                "id": "phone-a",
                "name": "Phone A",
                "type": "smartphone",
                "mac": "00:00:5e:00:53:a1",
                "hostname_match": ["Phone-A"],
                "track": True,
            },
            {
                "id": "phone-b",
                "name": "Phone B",
                "type": "smartphone",
                "mac": "00:00:5e:00:53:a2",
                "hostname_match": ["Phone-B"],
                "track": True,
            },
        ],
    }


@pytest.fixture
def people_data():
    """One person per phone."""
    return {
        "version": 1,
        "people": [
            {"id": "alex", "name": "Alex", "device_ids": ["phone-a"]},
            {"id": "sam", "name": "Sam", "device_ids": ["phone-b"]},
        ],
    }


@pytest.fixture
def clients():
    """Both phones at home plus one unknown client per network."""
    return [
        {
            "mac": "00:00:5e:00:53:a1",
            "hostname": "Phone-A",
            "ip": "192.0.2.101",
            "is_wired": False,
            "ap_mac": AP_1,
            "signal": -50,
        },
        {
            "mac": "00:00:5e:00:53:a2",
            "hostname": "Phone-B",
            "ip": "192.0.2.102",
            "is_wired": False,
            "ap_mac": AP_2,
            "signal": -55,
        },
        HOME_UNKNOWN,
        FOREIGN,
    ]


@pytest.fixture
def entry_options():
    """Options the config entry starts with (no network filter)."""
    return {"event_debounce": 0}


@pytest.fixture
async def setup_entry(hass, devices_data, people_data, clients, entry_options):
    """Loaded config entry; the client list can be swapped via ``clients``."""
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.1", "token": "test-token", "verify_ssl": False},
        options=entry_options,
        title="UniFi People Pointer",
        unique_id="network-filter",
    )
    entry.add_to_hass(hass)
    with patch(f"{COORD}._fetch_clients", new=AsyncMock(side_effect=lambda: clients)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry


@pytest.fixture
async def client(hass, setup_entry, aiohttp_client, socket_enabled):
    """HTTP client against the web UI app."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    return await aiohttp_client(WebUIServer(hass, coordinator).build_app())


def _unknown_macs(hass) -> set[str]:
    state = hass.states.get("sensor.unknown_wifi_clients")
    return {c["mac"] for c in state.attributes["clients"]}


async def test_foreign_client_disappears_with_main_net_filter(
    hass, setup_entry, client, hass_access_token
):
    """Reproduction: a client of another network is listed until filtered."""
    headers = _auth(hass_access_token)
    coordinator = hass.data[DOMAIN]["coordinator"]

    unknown = await (await client.get("/api/clients/unknown", headers=headers)).json()
    assert {c["mac"] for c in unknown} == {FOREIGN["mac"], HOME_UNKNOWN["mac"]}
    assert _unknown_macs(hass) == {FOREIGN["mac"], HOME_UNKNOWN["mac"]}

    resp = await client.put(
        "/api/networks", headers=headers, json={"networks": ["192.0.2.7/24"]}
    )
    assert resp.status == 200
    body = await resp.json()
    assert body["selected"] == [MAIN_NET]
    assert body["active"] is True
    await hass.async_block_till_done()

    unknown = await (await client.get("/api/clients/unknown", headers=headers)).json()
    assert [c["mac"] for c in unknown] == [HOME_UNKNOWN["mac"]]
    assert _unknown_macs(hass) == {HOME_UNKNOWN["mac"]}
    overview = await (await client.get("/api/overview", headers=headers)).json()
    assert overview["unknown_clients"] == 1
    assert overview["network_filter"] == [MAIN_NET]
    aps = await (await client.get("/api/access-points", headers=headers)).json()
    # The AP keeps the configured phone and the home stranger, not the foreigner.
    assert {ap["mac"]: ap["clients"] for ap in aps}[AP_2] == 2

    # Stored in the entry options and applied live, without a reload.
    assert setup_entry.options["networks"] == [MAIN_NET]
    assert setup_entry.options["include_unassigned_clients"] is True
    assert setup_entry.options["event_debounce"] == 0
    assert hass.data[DOMAIN]["coordinator"] is coordinator


async def test_networks_endpoint_lists_detected_networks(
    hass, setup_entry, client, hass_access_token
):
    """GET /api/networks: observed ranges with counts, nothing selected."""
    body = await (
        await client.get("/api/networks", headers=_auth(hass_access_token))
    ).json()
    assert body["active"] is False
    assert body["selected"] == []
    rows = {row["key"]: row for row in body["networks"]}
    assert rows[MAIN_NET]["clients"] == 3
    assert rows["198.51.100.0/24"]["clients"] == 1
    assert body["unassigned_clients"] == 0


async def test_networks_endpoint_uses_unifi_networks(
    hass, setup_entry, client, hass_access_token
):
    """Known UniFi networks are offered as ``network:<id>`` with counts."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    import ipaddress

    coordinator._networks = [
        UniFiNetwork("net-main", "Main", None, (ipaddress.ip_network(MAIN_NET),))
    ]
    headers = _auth(hass_access_token)
    resp = await client.put(
        "/api/networks", headers=headers, json={"networks": ["network:net-main"]}
    )
    body = await resp.json()
    main = next(r for r in body["networks"] if r["key"] == "network:net-main")
    assert main["selected"] is True
    assert main["clients"] == 3
    overview = await (await client.get("/api/overview", headers=headers)).json()
    assert overview["network_filter"] == ["Main"]
    assert overview["unknown_clients"] == 1


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"networks": ["192.0.2.0/33"]}, "not a valid subnet"),
        ({"networks": "192.0.2.0/24"}, "must be a list"),
        (
            {"networks": [MAIN_NET], "include_unassigned_clients": "yes"},
            "must be a boolean",
        ),
    ],
)
async def test_save_networks_rejects_invalid_input(
    hass, setup_entry, client, hass_access_token, payload, message
):
    """Invalid input is refused with a readable message and changes nothing."""
    resp = await client.put(
        "/api/networks", headers=_auth(hass_access_token), json=payload
    )
    assert resp.status == 400
    assert message in await resp.text()
    assert "networks" not in setup_entry.options


async def test_device_outside_filter_is_unavailable_and_keeps_owner(
    hass, setup_entry, client, hass_access_token
):
    """A tracked device seen only outside the filter: unavailable, not lost."""
    headers = _auth(hass_access_token)
    storage = Path(hass.config.path(STORAGE_DIR))
    people_before = (storage / "people.json").read_text(encoding="utf-8")
    assert hass.states.get("device_tracker.alex").state == "home"

    # Phone A is online at .101; this range keeps only .102 and .103.
    await client.put(
        "/api/networks", headers=headers, json={"networks": ["192.0.2.102/31"]}
    )
    await hass.async_block_till_done()

    assert hass.states.get("device_tracker.phone_a").state == STATE_UNAVAILABLE
    assert hass.states.get("device_tracker.alex").state == "not_home"
    assert hass.states.get("device_tracker.phone_b").state == "home"
    devices = await (await client.get("/api/devices", headers=headers)).json()
    phone = next(d for d in devices if d["id"] == "phone-a")
    assert phone["filtered"] is True
    assert phone["online"] is False
    assert phone["person"] == "alex"
    overview = await (await client.get("/api/overview", headers=headers)).json()
    assert overview["devices_total"] == 1
    assert overview["devices_online"] == 1

    await client.put("/api/networks", headers=headers, json={"networks": []})
    await hass.async_block_till_done()
    assert hass.states.get("device_tracker.phone_a").state == "home"
    assert hass.states.get("device_tracker.alex").state == "home"
    assert (storage / "people.json").read_text(encoding="utf-8") == people_before


@pytest.mark.parametrize(
    "entry_options",
    [{"event_debounce": 0, "networks": [MAIN_NET]}],
)
async def test_no_unknown_device_event_outside_filter(
    hass, setup_entry, clients, entry_options
):
    """New unknown clients fire events only inside the selected networks."""
    events = async_capture_events(hass, EVENT_UNKNOWN_DEVICE)
    newcomers = [
        {**FOREIGN, "mac": "00:00:5e:00:53:52", "ip": "198.51.100.21"},
        {**HOME_UNKNOWN, "mac": "00:00:5e:00:53:02", "ip": "192.0.2.151"},
    ]
    clients.extend(newcomers)
    coordinator = hass.data[DOMAIN]["coordinator"]
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert [e.data["mac"] for e in events] == ["00:00:5e:00:53:02"]
    assert FOREIGN["mac"] not in _unknown_macs(hass)


@pytest.mark.parametrize(
    "entry_options",
    [
        {
            "event_debounce": 0,
            "networks": [MAIN_NET],
            "include_unassigned_clients": False,
        }
    ],
)
async def test_clients_without_network_follow_the_option(
    hass, setup_entry, clients, entry_options
):
    """A client with neither IP nor network shows only when allowed."""
    clients.append({"mac": "00:00:5e:00:53:60", "hostname": "no-ip", "is_wired": False})
    coordinator = hass.data[DOMAIN]["coordinator"]
    await coordinator.async_refresh()
    assert "00:00:5e:00:53:60" not in _unknown_macs(hass)

    hass.config_entries.async_update_entry(
        setup_entry, options={**setup_entry.options, "include_unassigned_clients": True}
    )
    await hass.async_block_till_done()
    assert hass.data[DOMAIN]["coordinator"] is coordinator
    assert "00:00:5e:00:53:60" in _unknown_macs(hass)


async def test_options_flow_selects_networks(hass, setup_entry):
    """Options flow offers detected networks, validates and applies live."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    result = await hass.config_entries.options.async_init(setup_entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    schema = result["data_schema"].schema
    networks_key = next(k for k in schema if k == "networks")
    choices = schema[networks_key].config["options"]
    labels = {c["value"]: c["label"] for c in choices}
    assert labels[MAIN_NET] == f"{MAIN_NET} - 3 clients"
    assert labels["198.51.100.0/24"] == "198.51.100.0/24 - 1 clients"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"networks": ["lan"]}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"networks": "invalid_network"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"networks": [MAIN_NET]}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert setup_entry.options["networks"] == [MAIN_NET]
    assert hass.data[DOMAIN]["coordinator"] is coordinator
    assert FOREIGN["mac"] not in _unknown_macs(hass)


async def test_other_option_change_still_reloads(hass, setup_entry):
    """Changing anything besides the network filter reloads the entry."""
    with patch.object(
        hass.config_entries, "async_reload", AsyncMock(return_value=True)
    ) as reload:
        hass.config_entries.async_update_entry(
            setup_entry, options={**setup_entry.options, "scan_interval": 60}
        )
        await hass.async_block_till_done()
    reload.assert_awaited_once_with(setup_entry.entry_id)


@pytest.mark.real_network_fetch
async def test_fetch_networks_classic_then_integration(hass):
    """Classic networkconf first; integration API networks as fallback."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.1", "token": "test-token", "verify_ssl": False},
    )
    entry.add_to_hass(hass)
    coordinator = UniFiPeoplePointerCoordinator(hass, entry)
    coordinator.config_entry = entry
    base = "https://192.0.2.1/proxy/network"

    with aioresponses() as mocked:
        mocked.get(
            f"{base}/api/s/default/rest/networkconf",
            payload={
                "meta": {"rc": "ok"},
                "data": [{"_id": "n1", "name": "Main", "ip_subnet": "192.0.2.1/24"}],
            },
        )
        (network,) = await coordinator._fetch_networks()
    assert network.id == "n1"
    assert [str(s) for s in network.subnets] == [MAIN_NET]

    with aioresponses() as mocked:
        mocked.get(f"{base}/api/s/default/rest/networkconf", status=403)
        mocked.get(
            f"{base}/integration/v1/sites",
            payload={"data": [{"id": "site-uuid", "internalReference": "default"}]},
        )
        mocked.get(
            f"{base}/integration/v1/sites/site-uuid/networks?limit=200",
            payload={"data": [{"id": "n2", "name": "IoT", "vlanId": 20}]},
        )
        (network,) = await coordinator._fetch_networks()
    assert network.id == "n2"
    assert network.vlan == 20

    with aioresponses() as mocked:
        mocked.get(f"{base}/api/s/default/rest/networkconf", status=500)
        mocked.get(
            f"{base}/integration/v1/sites/site-uuid/networks?limit=200", status=404
        )
        with pytest.raises(ConnectionError):
            await coordinator._fetch_networks()
