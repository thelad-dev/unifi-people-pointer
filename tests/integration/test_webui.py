"""Built-in web UI: API on top of the coordinator, auth, server, panel."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import frontend
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_people_pointer.const import (
    DOMAIN,
    PANEL_URL_PATH,
    STORAGE_DIR,
)
from custom_components.unifi_people_pointer.webui import WebUIServer, slugify_person_id

pytestmark = pytest.mark.integration

COORD = (
    "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator"
)
AP_NAMES = {"24:5a:4c:aa:bb:cc": "EG-Diele", "24:5a:4c:aa:bb:dd": "OG-Flur"}
UNKNOWN = {
    "mac": "aa:aa:aa:00:00:01",
    "hostname": "stranger",
    "ip": "192.168.88.150",
    "is_wired": False,
    "ap_mac": "24:5a:4c:aa:bb:dd",
    "signal": -70,
}


@pytest.fixture
async def setup_entry(hass, devices_data, people_data, mock_unifi_api_clients_online):
    """Loaded config entry with clients online and AP names known."""
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.88.1", "token": "test-token", "verify_ssl": False},
        options={"event_debounce": 0},
        title="UniFi People Pointer",
        unique_id="webui",
    )
    entry.add_to_hass(hass)
    clients = [*mock_unifi_api_clients_online, UNKNOWN]
    with patch(f"{COORD}._fetch_clients", new=AsyncMock(return_value=clients)), patch(
        f"{COORD}._fetch_access_points", new=AsyncMock(return_value=dict(AP_NAMES))
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry


@pytest.fixture
async def client(hass, setup_entry, aiohttp_client, socket_enabled):
    """HTTP client against the web UI app."""
    # Writes request a refresh; a failing fetch keeps the last client snapshot.
    coordinator = hass.data[DOMAIN]["coordinator"]
    return await aiohttp_client(WebUIServer(hass, coordinator).build_app())


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_slugify_person_id():
    """Person ids are lower-case slugs of the name."""
    assert slugify_person_id("Jane Doe") == "jane_doe"
    assert slugify_person_id("  Ölaf! ") == "laf"


async def test_api_requires_ha_token(client, hass_access_token):
    """No or bad token: 401; health stays open for probes."""
    assert (await client.get("/api/health")).status == 200
    assert (await client.get("/api/devices")).status == 401
    assert (await client.get("/api/devices", headers=_auth("nope"))).status == 401
    assert (
        await client.get("/api/devices", headers=_auth(hass_access_token))
    ).status == 200


async def test_read_only_user_cannot_change(client, hass_read_only_access_token):
    """Non-admin users can read but not write."""
    headers = _auth(hass_read_only_access_token)
    assert (await client.get("/api/persons", headers=headers)).status == 200
    resp = await client.post("/api/persons", headers=headers, json={"name": "Eve"})
    assert resp.status == 403


async def test_devices_and_overview_show_ap_names(client, hass_access_token):
    """Device rows carry AP names; overview counts presence."""
    headers = _auth(hass_access_token)
    devices = await (await client.get("/api/devices", headers=headers)).json()
    phone = next(d for d in devices if d["id"] == "iphone-skhl")
    assert phone["online"] is True
    assert phone["ap_name"] == "EG-Diele"
    assert phone["person"] == "sebastian"

    overview = await (await client.get("/api/overview", headers=headers)).json()
    assert overview["persons_home"] >= 1
    assert overview["unknown_clients"] == 1
    sebastian = next(p for p in overview["persons"] if p["id"] == "sebastian")
    assert sebastian["ap_name"] == "EG-Diele"

    unknown = await (await client.get("/api/clients/unknown", headers=headers)).json()
    assert unknown == [
        {
            "mac": "aa:aa:aa:00:00:01",
            "hostname": "stranger",
            "ip": "192.168.88.150",
            "signal": -70,
            "ap_mac": "24:5a:4c:aa:bb:dd",
            "ap_name": "OG-Flur",
            "last_seen": None,
        }
    ]

    aps = await (await client.get("/api/access-points", headers=headers)).json()
    assert {ap["name"] for ap in aps} == {"EG-Diele", "OG-Flur"}


async def test_person_crud_writes_people_json(hass, client, hass_access_token):
    """Create, rename and delete a person through the API."""
    headers = _auth(hass_access_token)
    resp = await client.post(
        "/api/persons",
        headers=headers,
        json={"name": "Eve Doe", "ha_person": "person.eve"},
    )
    assert resp.status == 201
    assert (await resp.json())["id"] == "eve_doe"
    await hass.async_block_till_done()
    assert hass.states.get("device_tracker.eve_doe") is not None

    assert (
        await client.post("/api/persons", headers=headers, json={"name": "Eve Doe"})
    ).status == 409
    bad = await client.post(
        "/api/persons", headers=headers, json={"name": "X", "ha_person": "zone.x"}
    )
    assert bad.status == 400

    resp = await client.put(
        "/api/persons/eve_doe", headers=headers, json={"name": "Eve"}
    )
    assert resp.status == 200
    storage = Path(hass.config.path(STORAGE_DIR))
    people = json.loads((storage / "people.json").read_text(encoding="utf-8"))["people"]
    eve = next(p for p in people if p["id"] == "eve_doe")
    assert eve["name"] == "Eve"
    assert "ha_person" not in eve

    assert (await client.delete("/api/persons/eve_doe", headers=headers)).status == 204
    assert (await client.delete("/api/persons/eve_doe", headers=headers)).status == 404


async def test_device_create_assign_unassign_delete(hass, client, hass_access_token):
    """Devices: add with owner, move owner, unassign, remove."""
    headers = _auth(hass_access_token)
    resp = await client.post(
        "/api/devices",
        headers=headers,
        json={
            "mac": "AA-BB-CC-00-11-22",
            "name": "Kindle",
            "type": "tablet",
            "person": "janine",
        },
    )
    assert resp.status == 201
    devices = await (await client.get("/api/devices", headers=headers)).json()
    kindle = next(d for d in devices if d["mac"] == "aa:bb:cc:00:11:22")
    assert kindle["person"] == "janine"
    assert kindle["type"] == "tablet"

    resp = await client.put(
        f"/api/devices/{kindle['id']}",
        headers=headers,
        json={"name": "Kindle 2", "type": "tablet", "person": "sebastian"},
    )
    assert resp.status == 200
    devices = await (await client.get("/api/devices", headers=headers)).json()
    kindle = next(d for d in devices if d["id"] == kindle["id"])
    assert (kindle["name"], kindle["person"]) == ("Kindle 2", "sebastian")

    resp = await client.put(
        f"/api/devices/{kindle['id']}",
        headers=headers,
        json={"name": "Kindle 2", "type": "tablet", "person": ""},
    )
    assert resp.status == 200
    devices = await (await client.get("/api/devices", headers=headers)).json()
    assert next(d for d in devices if d["id"] == kindle["id"])["person"] is None

    assert (
        await client.post(
            "/api/devices", headers=headers, json={"mac": "nope", "name": "x"}
        )
    ).status == 400
    assert (
        await client.put(
            "/api/devices/missing", headers=headers, json={"name": "x", "type": "other"}
        )
    ).status == 404
    assert (
        await client.delete(f"/api/devices/{kindle['id']}", headers=headers)
    ).status == 204
    devices = await (await client.get("/api/devices", headers=headers)).json()
    assert all(d["id"] != kindle["id"] for d in devices)


async def test_claim_unknown_client(hass, client, hass_access_token):
    """Claiming an unknown client assigns it and removes it from the list."""
    headers = _auth(hass_access_token)
    resp = await client.post(
        "/api/clients/aa:aa:aa:00:00:01/claim",
        headers=headers,
        json={"person": "janine", "name": "Janine Laptop", "role": "secondary"},
    )
    assert resp.status == 201
    unknown = await (await client.get("/api/clients/unknown", headers=headers)).json()
    assert unknown == []
    devices = await (await client.get("/api/devices", headers=headers)).json()
    laptop = next(d for d in devices if d["mac"] == "aa:aa:aa:00:00:01")
    assert (laptop["name"], laptop["person"], laptop["ap_name"]) == (
        "Janine Laptop",
        "janine",
        "OG-Flur",
    )

    resp = await client.post(
        "/api/clients/aa:aa:aa:00:00:02/claim",
        headers=headers,
        json={"person": "ghost"},
    )
    assert resp.status == 400


async def test_static_bundle_and_spa_fallback(client):
    """Bundle is served without auth; unknown paths fall back to index.html."""
    index = await client.get("/")
    assert index.status == 200
    assert '<div id="root">' in await index.text()
    assert (await client.get("/persons")).status == 200
    traversal = await client.get("/..%2fmanifest.json")
    assert "unifi_people_pointer" not in await traversal.text()
    assert (await client.get("/api/nope", headers={})).status == 401


@pytest.mark.real_webui
async def test_server_binds_and_reports_port_conflict(hass, socket_enabled):
    """Server starts on host:port; a taken port is logged, not raised."""
    coordinator = MagicMock()
    first = WebUIServer(hass, coordinator, port=0, host="127.0.0.1")
    assert await first.async_start()
    port = first._runner.addresses[0][1]
    second = WebUIServer(hass, coordinator, port=port, host="127.0.0.1")
    assert not await second.async_start()
    assert not second.running
    await first.async_stop()
    assert not first.running


async def test_panel_registered_and_removed(hass, devices_data, people_data):
    """With the frontend loaded, setup adds the sidebar panel; unload removes it."""
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.88.1", "token": "test-token", "verify_ssl": False},
        options={"webui_port": 8799},
        unique_id="panel",
    )
    entry.add_to_hass(hass)
    # Real http first; marking the frontend as loaded afterwards does not start
    # the HA web server (no sockets in tests).
    assert await async_setup_component(hass, "http", {})
    hass.config.components.add("frontend")

    with patch(f"{COORD}._fetch_clients", new=AsyncMock(return_value=[])), patch(
        "custom_components.unifi_people_pointer.webui.WebUIServer.async_start",
        new=AsyncMock(return_value=True),
    ), patch(
        "custom_components.unifi_people_pointer.webui.WebUIServer.running", new=True
    ), patch(
        "custom_components.unifi_people_pointer.webui.WebUIServer.async_stop",
        new=AsyncMock(),
    ), patch.object(
        hass.http, "register_static_path", create=True
    ) as legacy_static, patch.object(
        hass.http, "async_register_static_paths", new=AsyncMock(), create=True
    ) as static_paths:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH]
        assert panel.config["_panel_custom"]["name"] == "unifi-people-pointer-panel"
        assert panel.config["port"] == 8799
        assert panel.config["_panel_custom"]["module_url"].startswith(
            "/unifi_people_pointer_static/upp-panel.js?v="
        )
        assert panel.config_panel_domain == DOMAIN
        assert panel.require_admin is True
        assert static_paths.await_count + legacy_static.call_count == 1

        runtime = hass.data[DOMAIN][entry.entry_id]
        assert runtime["webui_url"] is None or runtime["webui_url"].endswith(":8799/")

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]
