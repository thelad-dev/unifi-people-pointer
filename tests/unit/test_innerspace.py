"""UniFi InnerSpace import against responses shaped like InnerSpace 1.4.1.

The InnerSpace integration API needs a UniFi OS session, so these responses
follow the route handlers and response schemas shipped with InnerSpace
(``floor_plans``, ``access_points``, ``project?mode=2D``, ``assets``) instead
of a live controller.
"""

from __future__ import annotations

import io
import logging
import math

import pytest
from aioresponses import aioresponses
from PIL import Image

from custom_components.unifi_people_pointer.innerspace import (
    InnerSpaceError,
    async_fetch_innerspace,
    build_floors,
    plausible_width_m,
    unrotate,
)

pytestmark = pytest.mark.unit

BASE = "https://192.168.10.1"
API = f"{BASE}/proxy/innerspace/integration/v1"
PLAN_EG = "3f1c2b8e-1111-4c7a-9d55-0a1b2c3d4e5f"
PLAN_DG = "3f1c2b8e-2222-4c7a-9d55-0a1b2c3d4e5f"
SECRET = "s3cr3t-Passw0rd"


def png(width: int, height: int) -> bytes:
    """PNG of the given size."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (240, 240, 235)).save(buffer, format="PNG")
    return buffer.getvalue()


FLOOR_PLANS = {
    "floor_plans": [
        {
            "id": PLAN_EG,
            "name": "EG",
            "image_url": f"/proxy/innerspace/integration/v1/assets/{PLAN_EG}/{PLAN_EG}.png",
            # Uncalibrated scale: 200 px / 4.47 ppm would be a 45 m wide plan,
            # here kept plausible on purpose: 200 / 20 = 10 m.
            "ppm": 20,
            "width": 200,
            "height": 400,
            "origin_x": 0,
            "origin_y": 0,
        },
        {
            "id": PLAN_DG,
            "name": "DG",
            "floor_number": 2,
            "image_url": f"/proxy/innerspace/integration/v1/assets/{PLAN_DG}/{PLAN_DG}.png",
            "ppm": 1,
            "width": 100,
            "height": 50,
            "origin_x": 0,
            "origin_y": 0,
        },
    ]
}
ACCESS_POINTS = {
    "access_points": [
        {
            "id": "a0000000-0000-4000-8000-000000000001",
            "name": "AP Hall",
            "model": "U7PG2",
            "mac": "24:5a:4c:aa:bb:cc",
            "serial": "SN245a4caabbcc",
            "floor_plan_id": PLAN_EG,
            "x": 50,
            "y": 100,
            "height": 2.6,
            "azimuth": 0,
            "mount": "ceiling",
            "status": "online",
        },
        {
            "id": "a0000000-0000-4000-8000-000000000002",
            "name": "AP Attic",
            "model": "U6Lite",
            "mac": "24:5a:4c:aa:bb:dd",
            "serial": "SN245a4caabbdd",
            "floor_plan_id": PLAN_DG,
            "x": 20,
            "y": 10,
            "height": 2.2,
            "azimuth": 90,
            "mount": "wall",
            "status": "offline",
        },
        {
            "id": "a0000000-0000-4000-8000-000000000003",
            "name": "AP Unknown",
            "model": "U6Lite",
            "mac": None,
            "serial": None,
            "floor_plan_id": PLAN_EG,
            "x": 10,
            "y": 10,
            "height": 2.2,
            "azimuth": 0,
            "mount": "wall",
            "status": "offline",
        },
    ]
}
PROJECT = {
    "data": {
        "project": {"id": "p", "title": "Home"},
        "plans": [],
        "shapes": [
            {"id": "m1", "type": "map", "planId": PLAN_EG, "rotation": 0},
            {"id": "m2", "type": "map", "planId": PLAN_DG, "rotation": math.pi},
            {"id": "d1", "type": "device", "planId": PLAN_EG},
        ],
    }
}


def test_unrotate():
    """No rotation keeps the point; 180 degrees mirrors it through the center."""
    assert unrotate(20, 10, 100, 50, 0) == (20, 10)
    x, y = unrotate(20, 10, 100, 50, math.pi)
    assert (round(x, 6), round(y, 6)) == (80, 40)
    x, y = unrotate(50, 25, 100, 50, 1.234)
    assert (round(x, 6), round(y, 6)) == (50, 25)


def test_plausible_width():
    """Only house-like widths survive."""
    assert plausible_width_m(200, 20) == 10.0
    assert plausible_width_m(699, 4.47) is None
    assert plausible_width_m(100, 1) is None
    assert plausible_width_m(None, 20) is None
    assert plausible_width_m(100, 0) is None


def test_build_floors_converts_positions():
    """Fractions of the image, rotation applied, unusable APs reported."""
    result = build_floors(
        FLOOR_PLANS["floor_plans"],
        ACCESS_POINTS["access_points"],
        {PLAN_EG: png(200, 400), PLAN_DG: png(100, 50)},
        {PLAN_DG: math.pi},
    )
    eg, dg = result.floors
    assert (eg.name, eg.level, eg.width_m) == ("EG", 0, 10.0)
    assert eg.aps == [("24:5a:4c:aa:bb:cc", 0.25, 0.25)]
    assert (dg.name, dg.level, dg.width_m) == ("DG", 2, None)
    mac, fx, fy = dg.aps[0]
    assert mac == "24:5a:4c:aa:bb:dd"
    assert (round(fx, 6), round(fy, 6)) == (0.8, 0.8)
    assert result.skipped_aps == ["AP Unknown (no MAC or position)"]
    assert any("rotated by 180" in w for w in result.warnings)


def test_build_floors_skips_missing_images_and_far_points():
    """No image: floor skipped with a warning; points outside: AP skipped."""
    aps = [dict(ACCESS_POINTS["access_points"][0], x=500, y=100)]
    result = build_floors(FLOOR_PLANS["floor_plans"], aps, {PLAN_EG: png(200, 400)}, {})
    assert [f.name for f in result.floors] == ["EG"]
    assert result.floors[0].aps == []
    assert result.skipped_aps == ["AP Hall (outside the floor plan image)"]
    assert result.warnings == ["DG: no floor plan image, floor skipped"]


def _mock_login(mocked, status=200):
    mocked.post(
        f"{BASE}/api/auth/login",
        status=status,
        headers={"X-CSRF-Token": "csrf-1", "Set-Cookie": "TOKEN=abc; Path=/; Secure"},
        payload={},
    )


async def test_fetch_signs_in_reads_and_signs_out(caplog):
    """Full import round: login, plans, APs, project, images, logout."""
    caplog.set_level(logging.DEBUG)
    with aioresponses() as mocked:
        _mock_login(mocked)
        mocked.get(f"{API}/floor_plans", payload=FLOOR_PLANS)
        mocked.get(f"{API}/access_points", payload=ACCESS_POINTS)
        mocked.get(f"{API}/project?mode=2D", payload=PROJECT)
        mocked.get(f"{API}/assets/{PLAN_EG}/{PLAN_EG}.png", body=png(200, 400))
        mocked.get(f"{API}/assets/{PLAN_DG}/{PLAN_DG}.png", body=png(100, 50))
        mocked.post(f"{BASE}/api/auth/logout", status=200)
        result = await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)

        login = mocked.requests[("POST", _url(f"{BASE}/api/auth/login"))][0]
        assert login.kwargs["json"] == {
            "username": "importer",
            "password": SECRET,
            "rememberMe": False,
        }
        logout = mocked.requests[("POST", _url(f"{BASE}/api/auth/logout"))][0]
        assert logout.kwargs["headers"] == {"X-CSRF-Token": "csrf-1"}

    assert [f.name for f in result.floors] == ["EG", "DG"]
    fx, fy = result.floors[1].aps[0][1:]
    assert (round(fx, 6), round(fy, 6)) == (0.8, 0.8)
    assert SECRET not in caplog.text


def _url(value: str):
    from yarl import URL

    return URL(value)


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "rejected the user name or password"),
        (499, "two-factor"),
        (429, "rate limiting"),
        (500, "HTTP 500"),
    ],
)
async def test_login_errors(status, message, caplog):
    """Sign-in failures give a clear message, no logout, no secret in logs."""
    caplog.set_level(logging.DEBUG)
    with aioresponses() as mocked:
        _mock_login(mocked, status)
        with pytest.raises(InnerSpaceError, match=message) as err:
            await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)
        assert ("POST", _url(f"{BASE}/api/auth/logout")) not in mocked.requests
    assert SECRET not in str(err.value)
    assert SECRET not in caplog.text


@pytest.mark.parametrize(
    ("status", "message"),
    [(403, "Admin role for InnerSpace"), (404, "not installed"), (502, "HTTP 502")],
)
async def test_innerspace_errors_still_sign_out(status, message):
    """InnerSpace refusing access ends the session anyway."""
    with aioresponses() as mocked:
        _mock_login(mocked)
        mocked.get(f"{API}/floor_plans", status=status, payload={"code": "x"})
        mocked.post(f"{BASE}/api/auth/logout", status=200)
        with pytest.raises(InnerSpaceError, match=message):
            await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)
        assert ("POST", _url(f"{BASE}/api/auth/logout")) in mocked.requests


async def test_project_failure_imports_without_rotation():
    """Without the project the import still works and says so."""
    with aioresponses() as mocked:
        _mock_login(mocked)
        mocked.get(f"{API}/floor_plans", payload=FLOOR_PLANS)
        mocked.get(f"{API}/access_points", payload=ACCESS_POINTS)
        mocked.get(f"{API}/project?mode=2D", status=500)
        mocked.get(f"{API}/assets/{PLAN_EG}/{PLAN_EG}.png", body=png(200, 400))
        mocked.get(f"{API}/assets/{PLAN_DG}/{PLAN_DG}.png", body=png(100, 50))
        mocked.post(f"{BASE}/api/auth/logout", status=200)
        result = await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)
    assert result.floors[1].aps[0][1:] == (0.2, 0.2)
    assert result.warnings[0].startswith("Map rotation could not be read")


async def test_foreign_image_urls_are_not_followed():
    """Only the InnerSpace asset route is fetched."""
    plans = {
        "floor_plans": [
            dict(FLOOR_PLANS["floor_plans"][0], image_url="https://example.com/x.png"),
            dict(
                FLOOR_PLANS["floor_plans"][1],
                image_url="/proxy/innerspace/integration/v1/assets/../../../api/x",
            ),
        ]
    }
    with aioresponses() as mocked:
        _mock_login(mocked)
        mocked.get(f"{API}/floor_plans", payload=plans)
        mocked.get(f"{API}/access_points", payload={"access_points": []})
        mocked.get(f"{API}/project?mode=2D", payload=PROJECT)
        mocked.post(f"{BASE}/api/auth/logout", status=200)
        result = await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)
    assert result.floors == []
    assert len(result.warnings) == 2


async def test_unreachable_and_bad_format():
    """Connection errors and unexpected payloads become InnerSpaceError."""
    with aioresponses() as mocked:
        with pytest.raises(InnerSpaceError, match="Could not reach"):
            await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)
    with aioresponses() as mocked:
        _mock_login(mocked)
        mocked.get(f"{API}/floor_plans", payload=["unexpected"])
        mocked.get(f"{API}/access_points", payload={"access_points": []})
        mocked.post(f"{BASE}/api/auth/logout", status=200)
        with pytest.raises(InnerSpaceError, match="unexpected format"):
            await async_fetch_innerspace("192.168.10.1", False, "importer", SECRET)
    with pytest.raises(InnerSpaceError, match="required"):
        await async_fetch_innerspace("192.168.10.1", False, "importer", "")
