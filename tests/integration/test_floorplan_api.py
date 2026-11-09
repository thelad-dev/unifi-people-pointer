"""Floor plan endpoints of the web UI: floors, images, AP placement, persons."""

from __future__ import annotations

import io
import json
import logging
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from PIL import Image
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_people_pointer.const import DOMAIN, STORAGE_DIR
from custom_components.unifi_people_pointer.floorplan import ImportedFloor
from custom_components.unifi_people_pointer.innerspace import InnerSpaceResult

pytestmark = pytest.mark.integration

COORD = (
    "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator"
)
FETCH = "custom_components.unifi_people_pointer.webui.async_fetch_innerspace"
AP_HALL = "24:5a:4c:aa:bb:cc"
AP_UP = "24:5a:4c:aa:bb:dd"
AP_NAMES = {AP_HALL: "AP Hall", AP_UP: "AP Upstairs"}


def png(width: int = 40, height: int = 60) -> bytes:
    """PNG of the given size."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (230, 230, 220)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
async def client(
    hass,
    devices_data,
    people_data,
    mock_unifi_api_clients_online,
    aiohttp_client,
    socket_enabled,
):
    """Web UI app of a loaded entry with clients online and AP names known."""
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    _clear_floorplans(storage)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.10.1", "token": "test-token", "verify_ssl": False},
        options={"event_debounce": 0},
        title="UniFi People Pointer",
        unique_id="floorplan",
    )
    entry.add_to_hass(hass)
    with patch(
        f"{COORD}._fetch_clients",
        new=AsyncMock(return_value=mock_unifi_api_clients_online),
    ), patch(f"{COORD}._fetch_access_points", new=AsyncMock(return_value=AP_NAMES)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        # Import after setup: conftest re-imports the integration per test, and
        # patches below target that fresh module.
        from custom_components.unifi_people_pointer.webui import WebUIServer

        coordinator = hass.data[DOMAIN]["coordinator"]
        yield await aiohttp_client(WebUIServer(hass, coordinator).build_app())
    # The harness config directory outlives the test.
    _clear_floorplans(storage)


def _clear_floorplans(storage: Path) -> None:
    (storage / "floorplans.json").unlink(missing_ok=True)
    shutil.rmtree(storage / "floorplans", ignore_errors=True)


@pytest.fixture
def headers(hass_access_token):
    """Admin authorization header."""
    return {"Authorization": f"Bearer {hass_access_token}"}


def _form(image: bytes | None = None, **fields) -> aiohttp.FormData:
    data = aiohttp.FormData()
    for key, value in fields.items():
        data.add_field(key, str(value))
    if image is not None:
        data.add_field("image", image, filename="plan.png", content_type="image/png")
    return data


async def _add_floor(client, headers, name="EG", level=0, image=None, **extra):
    resp = await client.post(
        "/api/floorplan/floors",
        headers=headers,
        data=_form(png() if image is None else image, name=name, level=level, **extra),
    )
    return resp


async def test_floorplan_requires_admin(client, hass_read_only_access_token):
    """Floor plan data and images are admin-only like the rest of the API."""
    assert (await client.get("/api/floorplan")).status == 401
    ro = {"Authorization": f"Bearer {hass_read_only_access_token}"}
    assert (await client.get("/api/floorplan", headers=ro)).status == 403
    assert (await client.get("/api/floorplan/floors/eg/image")).status == 401


async def test_empty_floorplan_lists_aps(client, headers):
    """Without floors every known AP is listed as unplaced; no persons."""
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["floors"] == []
    assert data["persons"] == []
    assert data["privacy"] == {"locate_persons": False, "persons": []}
    assert {
        ap["mac"]: (ap["name"], ap["clients"], ap["floor"]) for ap in data["aps"]
    } == {
        AP_HALL: ("AP Hall", 2, None),
        AP_UP: ("AP Upstairs", 1, None),
    }


async def test_floor_upload_image_and_edit(client, headers):
    """Upload, read the image back, edit, replace and delete a floor."""
    resp = await _add_floor(client, headers, name="Ground floor", width_m="12.5")
    assert resp.status == 201
    floor = await resp.json()
    assert (floor["id"], floor["width"], floor["height"], floor["width_m"]) == (
        "ground-floor",
        40,
        60,
        12.5,
    )
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    listed = data["floors"][0]
    assert listed["image_url"].startswith("/api/floorplan/floors/ground-floor/image?v=")

    image = await client.get(listed["image_url"], headers=headers)
    assert image.status == 200
    assert image.headers["Content-Type"] == "image/png"
    assert "private" in image.headers["Cache-Control"]
    assert await image.read() == png()

    resp = await client.put(
        "/api/floorplan/floors/ground-floor",
        headers=headers,
        json={"name": "EG", "level": 1, "width_m": None},
    )
    assert (await resp.json())["name"] == "EG"

    resp = await client.put(
        "/api/floorplan/floors/ground-floor/image",
        headers=headers,
        data=_form(png(80, 120)),
    )
    assert (await resp.json())["width"] == 80

    assert (
        await client.delete("/api/floorplan/floors/ground-floor", headers=headers)
    ).status == 204
    assert (
        await client.get("/api/floorplan/floors/ground-floor/image", headers=headers)
    ).status == 404


async def test_floor_upload_validation(client, headers):
    """Missing image, bad image, bad fields and unknown floors are rejected."""
    resp = await client.post(
        "/api/floorplan/floors", headers=headers, data=_form(name="EG")
    )
    assert resp.status == 400
    assert await resp.text() == "image is required"
    resp = await _add_floor(client, headers, image=b"<svg></svg>")
    assert resp.status == 400
    assert "PNG, JPEG or WebP" in await resp.text()
    assert (await _add_floor(client, headers, name="")).status == 400
    assert (await _add_floor(client, headers, level="x")).status == 400
    resp = await client.put(
        "/api/floorplan/floors/missing", headers=headers, json={"name": "X"}
    )
    assert resp.status == 404
    assert (
        await client.delete("/api/floorplan/floors/missing", headers=headers)
    ).status == 404


async def test_oversized_upload_is_rejected(client, headers):
    """Requests above the upload limit fail without storing anything."""
    from custom_components.unifi_people_pointer import webui

    big = b"\0" * (webui.MAX_REQUEST_BYTES + 1)
    resp = await _add_floor(client, headers, image=big)
    assert resp.status in (400, 413)
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["floors"] == []


async def test_place_and_remove_ap(client, headers):
    """APs get fractional positions on a floor and can be taken off again."""
    await _add_floor(client, headers)
    resp = await client.put(
        f"/api/floorplan/aps/{AP_HALL.upper()}",
        headers=headers,
        json={"floor": "eg", "x": 0.5, "y": 0.25},
    )
    assert await resp.json() == {"floor": "eg", "x": 0.5, "y": 0.25}
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    hall = next(ap for ap in data["aps"] if ap["mac"] == AP_HALL)
    assert (hall["floor"], hall["x"], hall["y"]) == ("eg", 0.5, 0.25)

    for body, status in (
        ({"floor": "eg", "x": 2, "y": 0}, 400),
        ({"floor": "nope", "x": 0, "y": 0}, 404),
        ({"x": 0, "y": 0}, 400),
    ):
        resp = await client.put(
            f"/api/floorplan/aps/{AP_HALL}", headers=headers, json=body
        )
        assert resp.status == status

    assert (
        await client.delete(f"/api/floorplan/aps/{AP_HALL}", headers=headers)
    ).status == 204
    assert (
        await client.delete(f"/api/floorplan/aps/{AP_HALL}", headers=headers)
    ).status == 404


async def test_persons_only_with_privacy_release(client, headers):
    """Person markers appear only after the switch and the person release."""
    await _add_floor(client, headers)
    await client.put(
        f"/api/floorplan/aps/{AP_HALL}",
        headers=headers,
        json={"floor": "eg", "x": 0.5, "y": 0.5},
    )
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["persons"] == []

    resp = await client.put(
        "/api/floorplan/privacy",
        headers=headers,
        json={"locate_persons": False, "persons": ["christoph"]},
    )
    assert resp.status == 200
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["persons"] == []

    await client.put(
        "/api/floorplan/privacy",
        headers=headers,
        json={"locate_persons": True, "persons": ["christoph", "amelie"]},
    )
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    persons = {p["id"]: p for p in data["persons"]}
    assert set(persons) == {"christoph", "amelie"}
    christoph = persons["christoph"]
    assert christoph == {
        "id": "christoph",
        "name": "Christoph",
        "ap_mac": AP_HALL,
        "ap_name": "AP Hall",
        "signal": -52,
        "radius_m": christoph["radius_m"],
        "floor": "eg",
        "x": 0.5,
        "y": 0.5,
    }
    assert 2 <= christoph["radius_m"] <= 15
    # Stronger signal, smaller circle.
    assert persons["amelie"]["radius_m"] < christoph["radius_m"]

    resp = await client.put(
        "/api/floorplan/privacy",
        headers=headers,
        json={"locate_persons": True, "persons": ["nobody"]},
    )
    assert resp.status == 400


async def test_person_at_unplaced_ap(client, headers):
    """A released person at an AP without position has no coordinates."""
    await client.put(
        "/api/floorplan/privacy",
        headers=headers,
        json={"locate_persons": True, "persons": ["christoph"]},
    )
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert [(p["id"], p["ap_name"], p["floor"]) for p in data["persons"]] == [
        ("christoph", "AP Hall", None)
    ]


async def test_deleted_person_release_does_not_return(client, headers):
    """A person created again under the same name is not located without a new release."""
    await client.put(
        "/api/floorplan/privacy",
        headers=headers,
        json={"locate_persons": True, "persons": ["christoph"]},
    )
    resp = await client.delete("/api/persons/christoph", headers=headers)
    assert resp.status == 204
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["privacy"]["persons"] == []
    resp = await client.post(
        "/api/persons", headers=headers, json={"name": "christoph"}
    )
    assert resp.status in (200, 201)
    person_id = (await resp.json())["id"]
    assert person_id == "christoph"
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["persons"] == []


async def test_json_endpoints_keep_default_body_limit(client, headers):
    """Only the upload routes accept bodies above the aiohttp default."""
    big = {"name": "x" * (2 * 1024 * 1024)}
    resp = await client.post("/api/persons", headers=headers, json=big)
    assert resp.status == 413


async def test_import_innerspace(client, headers, caplog):
    """The import merges floors; credentials are passed through, never logged."""
    caplog.set_level(logging.DEBUG)
    result = InnerSpaceResult(
        floors=[
            ImportedFloor(name="EG", level=0, image=png(), aps=[(AP_UP, 0.1, 0.9)])
        ],
        skipped_aps=["AP Garage (no MAC or position)"],
        warnings=["DG: map rotated by 180 degrees, AP positions corrected"],
    )
    with patch(FETCH, new=AsyncMock(return_value=result)) as fetch:
        resp = await client.post(
            "/api/floorplan/import/innerspace",
            headers=headers,
            json={"username": " importer ", "password": "pa ss"},
        )
    assert resp.status == 200
    assert await resp.json() == {
        "floors_created": 1,
        "floors_updated": 0,
        "aps_placed": 1,
        "skipped_aps": ["AP Garage (no MAC or position)"],
        "warnings": ["DG: map rotated by 180 degrees, AP positions corrected"],
    }
    fetch.assert_awaited_once_with("192.168.10.1", False, "importer", "pa ss")
    assert "pa ss" not in caplog.text
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    up = next(ap for ap in data["aps"] if ap["mac"] == AP_UP)
    assert (up["floor"], up["x"], up["y"]) == ("eg", 0.1, 0.9)


async def test_import_innerspace_errors(client, headers):
    """Errors come back as messages; an empty result stores nothing."""
    from custom_components.unifi_people_pointer.innerspace import InnerSpaceError

    with patch(FETCH, new=AsyncMock(side_effect=InnerSpaceError("UniFi OS rejected"))):
        resp = await client.post(
            "/api/floorplan/import/innerspace",
            headers=headers,
            json={"username": "a", "password": "b"},
        )
    assert resp.status == 502
    assert await resp.json() == {"error": "UniFi OS rejected"}

    empty = InnerSpaceResult(warnings=["EG: no floor plan image, floor skipped"])
    with patch(FETCH, new=AsyncMock(return_value=empty)):
        resp = await client.post(
            "/api/floorplan/import/innerspace",
            headers=headers,
            json={"username": "a", "password": "b"},
        )
    assert resp.status == 422
    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert data["floors"] == []


async def test_usage_now_and_periods(hass, client, headers):
    """Heatmap data: live counts, history per period, positions, no persons."""
    await _add_floor(client, headers)
    await client.put(
        f"/api/floorplan/aps/{AP_HALL}",
        headers=headers,
        json={"floor": "eg", "x": 0.5, "y": 0.5},
    )
    data = await (
        await client.get("/api/floorplan/usage?period=now", headers=headers)
    ).json()
    assert data["period"] == "now"
    assert data["has_bytes"] is False
    rows = {row["mac"]: row for row in data["aps"]}
    assert rows[AP_HALL] == {
        "mac": AP_HALL,
        "name": "AP Hall",
        "clients": 2.0,
        "clients_max": 2,
        "bytes": None,
        "floor": "eg",
        "x": 0.5,
        "y": 0.5,
    }
    assert rows[AP_UP]["clients"] == 1.0
    assert rows[AP_UP]["floor"] is None
    assert "persons" not in data

    hour = await (
        await client.get("/api/floorplan/usage?period=1h", headers=headers)
    ).json()
    assert hour["samples"] >= 1
    assert hour["since"] is not None
    assert {row["mac"]: row["clients"] for row in hour["aps"]}[AP_HALL] == 2.0

    resp = await client.get("/api/floorplan/usage?period=2y", headers=headers)
    assert resp.status == 400


async def test_usage_with_rates(hass, client, headers):
    """With client rates the data volume is reported per period."""
    import time

    from custom_components.unifi_people_pointer.const import DOMAIN as D

    usage = hass.data[D]["coordinator"].usage
    usage.record(time.time(), {AP_HALL: 3}, {AP_HALL: 100.0}, True)
    now = await (
        await client.get("/api/floorplan/usage?period=now", headers=headers)
    ).json()
    assert now["has_bytes"] is True
    assert now["bytes_unit"] == "B/s"
    hall = next(row for row in now["aps"] if row["mac"] == AP_HALL)
    assert (hall["clients"], hall["bytes"]) == (3.0, 100)
    day = await (
        await client.get("/api/floorplan/usage?period=24h", headers=headers)
    ).json()
    assert day["bytes_unit"] == "B"
    hall = next(row for row in day["aps"] if row["mac"] == AP_HALL)
    assert hall["bytes"] > 0


async def test_network_filter_applies_to_map_and_heatmap(hass, client, headers):
    """Clients outside the network filter neither locate people nor count."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    await client.put(
        "/api/floorplan/privacy",
        headers=headers,
        json={"locate_persons": True, "persons": ["christoph", "amelie"]},
    )
    # Only the network of Amelie's phone (AP Hall); Christoph's phone (AP Hall)
    # and watch (AP Upstairs) are outside.
    await coordinator.async_apply_network_options({"networks": ["192.168.10.101/32"]})
    await coordinator.async_refresh()

    data = await (await client.get("/api/floorplan", headers=headers)).json()
    assert [p["id"] for p in data["persons"]] == ["amelie"]
    assert {ap["mac"]: ap["clients"] for ap in data["aps"]} == {
        AP_HALL: 1,
        AP_UP: 0,
    }

    now = await (
        await client.get("/api/floorplan/usage?period=now", headers=headers)
    ).json()
    assert {row["mac"]: row["clients"] for row in now["aps"]} == {
        AP_HALL: 1.0,
        AP_UP: 0.0,
    }
    # The poll after the filter change recorded only clients inside it.
    assert coordinator.usage.current_counts.get(AP_HALL) == 1
    assert not coordinator.usage.current_counts.get(AP_UP)
