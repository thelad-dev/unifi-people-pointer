"""One-time import of floor plans and AP positions from UniFi InnerSpace.

InnerSpace (a separate UniFi OS app) keeps floor plans and placed devices and
offers them under ``/proxy/innerspace/integration/v1``. That API only accepts a
UniFi OS user session, not the Network API key, so the import signs in with a
local account, reads the plans, AP positions and images, and signs out again.
The credentials are used for this one request only: they are never stored,
logged or echoed in errors.

AP coordinates from InnerSpace are image pixels that ignore a rotated map; the
rotation of the map shape (``project?mode=2D``) is applied here around the
image center.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .api_parser import normalize_mac
from .floorplan import FloorplanError, ImportedFloor, inspect_image

_LOGGER = logging.getLogger(__name__)

API = "/proxy/innerspace/integration/v1"
ASSET_PREFIX = f"{API}/assets/"
# Plausible real width of an imported plan; InnerSpace scales are often
# uncalibrated, then the plan keeps no width (UI assumes a default).
MIN_PLAUSIBLE_WIDTH_M = 4.0
MAX_PLAUSIBLE_WIDTH_M = 80.0
# Points this far outside the image are dropped instead of clamped.
_EDGE_TOLERANCE = 0.03


class InnerSpaceError(Exception):
    """Import failed; the message is safe to show to the user."""


@dataclass
class InnerSpaceResult:
    """Floors read from InnerSpace plus what could not be used."""

    floors: list[ImportedFloor] = field(default_factory=list)
    skipped_aps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _host_url(host: str) -> str:
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"https://{host}"


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def unrotate(
    x: float, y: float, width: float, height: float, rotation: float
) -> tuple[float, float]:
    """Pixel position on the unrotated image for an InnerSpace AP position.

    InnerSpace converts scene coordinates (origin at the image center, y up)
    to pixels as ``x + w/2, h/2 - y`` and ignores the map rotation. Undo that
    conversion, rotate the scene point back by the map rotation and convert
    again.
    """
    if not rotation:
        return x, y
    sx, sy = x - width / 2, height / 2 - y
    cos_r, sin_r = math.cos(rotation), math.sin(rotation)
    ux = cos_r * sx + sin_r * sy
    uy = -sin_r * sx + cos_r * sy
    return ux + width / 2, height / 2 - uy


def plausible_width_m(width_px: float | None, ppm: float | None) -> float | None:
    """Real plan width from pixels per meter, if the result looks like a house."""
    if not width_px or not ppm or ppm <= 0:
        return None
    width_m = width_px / ppm
    if MIN_PLAUSIBLE_WIDTH_M <= width_m <= MAX_PLAUSIBLE_WIDTH_M:
        return round(width_m, 2)
    return None


def _map_rotations(project: Any) -> dict[str, float]:
    """Rotation (radians) of each plan's map shape from ``project?mode=2D``."""
    data = project.get("data") if isinstance(project, dict) else None
    shapes = data.get("shapes") if isinstance(data, dict) else None
    rotations: dict[str, float] = {}
    for shape in shapes if isinstance(shapes, list) else []:
        if not isinstance(shape, dict) or shape.get("type") != "map":
            continue
        rotation = _number(shape.get("rotation"))
        if shape.get("planId") and rotation is not None:
            rotations[str(shape["planId"])] = rotation
    return rotations


def build_floors(
    floor_plans: list[dict[str, Any]],
    access_points: list[dict[str, Any]],
    images: dict[str, bytes],
    rotations: dict[str, float],
) -> InnerSpaceResult:
    """Turn InnerSpace API rows into floors for the floor plan store."""
    result = InnerSpaceResult()
    by_plan: dict[str, list[dict[str, Any]]] = {}
    for ap in access_points:
        if isinstance(ap, dict) and ap.get("floor_plan_id"):
            by_plan.setdefault(str(ap["floor_plan_id"]), []).append(ap)

    for index, plan in enumerate(floor_plans):
        if not isinstance(plan, dict) or not plan.get("id"):
            continue
        plan_id = str(plan["id"])
        name = str(plan.get("name") or "").strip()[:40] or f"Floor {index + 1}"
        image = images.get(plan_id)
        if image is None:
            result.warnings.append(f"{name}: no floor plan image, floor skipped")
            continue
        try:
            info = inspect_image(image)
        except FloorplanError as err:
            result.warnings.append(f"{name}: {err}, floor skipped")
            continue
        # Pixel coordinates refer to the size InnerSpace reports; fall back to
        # the image itself when it does not report one.
        width = _number(plan.get("width")) or float(info.width)
        height = _number(plan.get("height")) or float(info.height)
        rotation = rotations.get(plan_id, 0.0)
        if rotation:
            result.warnings.append(
                f"{name}: map rotated by {round(math.degrees(rotation)) % 360} degrees,"
                " AP positions corrected"
            )
        floor = ImportedFloor(
            name=name,
            level=int(_number(plan.get("floor_number")) or 0),
            image=image,
            width_m=plausible_width_m(width, _number(plan.get("ppm"))),
        )
        for ap in by_plan.get(plan_id, []):
            label = str(ap.get("name") or ap.get("mac") or ap.get("id") or "?")
            mac = normalize_mac(str(ap.get("mac") or ""))
            x, y = _number(ap.get("x")), _number(ap.get("y"))
            if len(mac.split(":")) != 6 or x is None or y is None:
                result.skipped_aps.append(f"{label} (no MAC or position)")
                continue
            px, py = unrotate(x, y, width, height, rotation)
            fx, fy = px / width, py / height
            if not (
                -_EDGE_TOLERANCE <= fx <= 1 + _EDGE_TOLERANCE
                and -_EDGE_TOLERANCE <= fy <= 1 + _EDGE_TOLERANCE
            ):
                result.skipped_aps.append(f"{label} (outside the floor plan image)")
                continue
            floor.aps.append((mac, min(max(fx, 0.0), 1.0), min(max(fy, 0.0), 1.0)))
        result.floors.append(floor)
    return result


class _Session:
    """A signed-in UniFi OS session (cookie jar plus CSRF token)."""

    def __init__(self, base: str, verify_ssl: bool) -> None:
        self.base = base
        self.ssl: bool = verify_ssl
        # unsafe=True: keep cookies from IP-address hosts (the usual case).
        self.http = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        self.csrf: str | None = None
        self.signed_in = False

    async def login(self, username: str, password: str) -> None:
        async with self.http.post(
            f"{self.base}/api/auth/login",
            json={"username": username, "password": password, "rememberMe": False},
            headers={"Accept": "application/json"},
            ssl=self.ssl,
        ) as response:
            status = response.status
            self.csrf = response.headers.get(
                "X-Updated-CSRF-Token"
            ) or response.headers.get("X-CSRF-Token")
        if status == 499:
            raise InnerSpaceError(
                "This account uses two-factor sign-in. Use a local UniFi OS account"
                " without 2FA for the import."
            )
        if status == 429:
            raise InnerSpaceError(
                "UniFi OS is rate limiting sign-ins; try again later."
            )
        if status in (400, 401, 403):
            raise InnerSpaceError("UniFi OS rejected the user name or password.")
        if status >= 400:
            raise InnerSpaceError(f"UniFi OS sign-in failed (HTTP {status}).")
        self.signed_in = True

    async def get_json(self, path: str) -> Any:
        async with self.http.get(
            f"{self.base}{path}", headers={"Accept": "application/json"}, ssl=self.ssl
        ) as response:
            self._check(response.status)
            return await response.json(content_type=None)

    async def get_bytes(self, path: str) -> bytes:
        async with self.http.get(f"{self.base}{path}", ssl=self.ssl) as response:
            self._check(response.status)
            return await response.read()

    @staticmethod
    def _check(status: int) -> None:
        if status in (401, 403):
            raise InnerSpaceError(
                "InnerSpace refused access. The account needs the Admin role for"
                " InnerSpace in UniFi OS."
            )
        if status == 404:
            raise InnerSpaceError("UniFi InnerSpace is not installed on this console.")
        if status >= 400:
            raise InnerSpaceError(f"InnerSpace answered HTTP {status}.")

    async def close(self) -> None:
        try:
            if not self.signed_in:
                return
            headers = {"X-CSRF-Token": self.csrf} if self.csrf else {}
            async with self.http.post(
                f"{self.base}/api/auth/logout", headers=headers, ssl=self.ssl
            ) as response:
                if response.status >= 400:
                    _LOGGER.debug("UniFi OS sign-out answered HTTP %s", response.status)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("UniFi OS sign-out failed: %s", type(err).__name__)
        finally:
            await self.http.close()


async def async_fetch_innerspace(
    host: str, verify_ssl: bool, username: str, password: str
) -> InnerSpaceResult:
    """Sign in, read floor plans, AP positions and images, sign out."""
    if not username or not password:
        raise InnerSpaceError("User name and password are required.")
    session = _Session(_host_url(host), verify_ssl)
    try:
        await session.login(username, password)
        plans_payload = await session.get_json(f"{API}/floor_plans")
        aps_payload = await session.get_json(f"{API}/access_points")
        floor_plans = (
            plans_payload.get("floor_plans")
            if isinstance(plans_payload, dict)
            else None
        )
        access_points = (
            aps_payload.get("access_points") if isinstance(aps_payload, dict) else None
        )
        if not isinstance(floor_plans, list) or not isinstance(access_points, list):
            raise InnerSpaceError("InnerSpace answered in an unexpected format.")
        rotations: dict[str, float] = {}
        warnings: list[str] = []
        try:
            rotations = _map_rotations(await session.get_json(f"{API}/project?mode=2D"))
        except (InnerSpaceError, aiohttp.ClientError, ValueError) as err:
            _LOGGER.debug("InnerSpace project read failed: %s", type(err).__name__)
            warnings.append(
                "Map rotation could not be read; check AP positions on rotated plans."
            )
        images: dict[str, bytes] = {}
        for plan in floor_plans:
            if not isinstance(plan, dict) or not plan.get("id"):
                continue
            url = str(plan.get("image_url") or "")
            # Only follow image paths of the InnerSpace asset route.
            if not url.startswith(ASSET_PREFIX) or ".." in url:
                continue
            images[str(plan["id"])] = await session.get_bytes(url)
        result = build_floors(floor_plans, access_points, images, rotations)
        result.warnings[:0] = warnings
        return result
    except aiohttp.ClientError as err:
        raise InnerSpaceError(
            f"Could not reach UniFi OS ({type(err).__name__})."
        ) from None
    except asyncio.TimeoutError:
        raise InnerSpaceError("UniFi OS did not answer in time.") from None
    finally:
        await session.close()
