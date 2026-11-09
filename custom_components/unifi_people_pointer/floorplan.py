"""Floor plans: floor images, access point positions and location privacy.

Everything lives in ``floorplans.json`` next to ``people.json`` plus one image
per floor under ``floorplans/``. AP positions are stored as fractions of the
image width and height (0..1), so a replaced image with another resolution
keeps the points in place. Locating people is off until an admin switches it
on and releases individual persons.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import os
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from homeassistant.core import HomeAssistant

from .api_parser import normalize_mac
from .const import (
    FLOORPLAN_DEFAULT_RADIUS_M,
    FLOORPLAN_IMAGE_DIR,
    FLOORPLAN_MAX_IMAGE_BYTES,
    FLOORPLAN_MAX_IMAGE_SIDE,
    FLOORPLAN_MAX_RADIUS_M,
    FLOORPLAN_MIN_RADIUS_M,
    FLOORPLANS_FILE,
)

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_IMAGE_NAME_RE = re.compile(r"^[a-z0-9-]+\.(png|jpg|webp)$")
# Pillow format name -> (file extension, content type). No SVG: an SVG served
# from the web UI origin could run script next to the stored access token.
IMAGE_FORMATS = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
}
CONTENT_TYPES = {ext: ctype for ext, ctype in IMAGE_FORMATS.values()}
# Log-distance path loss: signal at 1 m and indoor path loss exponent.
_SIGNAL_AT_1M_DBM = -40.0
_PATH_LOSS_EXPONENT = 3.0


class FloorplanError(ValueError):
    """A request the floor plan store rejects (shown to the user)."""


@dataclass
class ImageInfo:
    """Checked floor plan image."""

    ext: str
    width: int
    height: int


@dataclass
class ImportedFloor:
    """One floor read from an external source (UniFi InnerSpace)."""

    name: str
    level: int
    image: bytes
    width_m: float | None = None
    # (normalized AP MAC, x fraction, y fraction)
    aps: list[tuple[str, float, float]] = field(default_factory=list)


def inspect_image(data: bytes) -> ImageInfo:
    """Return format and size of an uploaded image; reject anything else."""
    if not data:
        raise FloorplanError("image is empty")
    if len(data) > FLOORPLAN_MAX_IMAGE_BYTES:
        raise FloorplanError(
            f"image is larger than {FLOORPLAN_MAX_IMAGE_BYTES // (1024 * 1024)} MB"
        )
    # Pillow is provided by Home Assistant Core, not by this integration.
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as image:
            fmt = image.format or ""
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as err:
        raise FloorplanError("file is not a readable PNG, JPEG or WebP image") from err
    except Image.DecompressionBombError as err:
        raise FloorplanError("image has too many pixels") from err
    if fmt not in IMAGE_FORMATS:
        raise FloorplanError("image must be PNG, JPEG or WebP")
    if not (
        0 < width <= FLOORPLAN_MAX_IMAGE_SIDE and 0 < height <= FLOORPLAN_MAX_IMAGE_SIDE
    ):
        raise FloorplanError(
            f"image sides must be between 1 and {FLOORPLAN_MAX_IMAGE_SIDE} pixels"
        )
    return ImageInfo(ext=IMAGE_FORMATS[fmt][0], width=width, height=height)


def signal_radius_m(signal: Any) -> float:
    """Uncertainty radius around the AP for a client signal in dBm.

    A rough log-distance estimate (strong signal: close to the AP, weak: at
    the edge of the cell), clamped to a sensible indoor range. Unknown or
    non-dBm values fall back to a medium radius.
    """
    try:
        dbm = float(signal)
    except (TypeError, ValueError):
        return FLOORPLAN_DEFAULT_RADIUS_M
    if not math.isfinite(dbm) or dbm >= 0:
        return FLOORPLAN_DEFAULT_RADIUS_M
    distance = 10 ** ((_SIGNAL_AT_1M_DBM - dbm) / (10 * _PATH_LOSS_EXPONENT))
    return round(min(max(distance, FLOORPLAN_MIN_RADIUS_M), FLOORPLAN_MAX_RADIUS_M), 1)


def _slug(name: str) -> str:
    return _SLUG_RE.sub("-", name.strip().lower()).strip("-") or "floor"


def _fraction(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise FloorplanError("x and y must be numbers") from err
    if not math.isfinite(number) or number < 0 or number > 1:
        raise FloorplanError("x and y must be between 0 and 1")
    return round(number, 5)


def clean_name(value: Any) -> str:
    """Return a floor name or raise."""
    name = str(value or "").strip()
    if not name:
        raise FloorplanError("name is required")
    if len(name) > 40:
        raise FloorplanError("name must be at most 40 characters")
    return name


def clean_level(value: Any) -> int:
    """Return a floor level (ordering, e.g. -1 basement, 0 ground) or raise."""
    if value is None or value == "":
        return 0
    try:
        level = int(value)
    except (TypeError, ValueError) as err:
        raise FloorplanError("level must be a whole number") from err
    if not -20 <= level <= 200:
        raise FloorplanError("level must be between -20 and 200")
    return level


def clean_width_m(value: Any) -> float | None:
    """Return the real width of the plan in meters (optional) or raise."""
    if value is None or value == "":
        return None
    try:
        width = float(value)
    except (TypeError, ValueError) as err:
        raise FloorplanError("width_m must be a number") from err
    if not math.isfinite(width) or not 1 <= width <= 1000:
        raise FloorplanError("width_m must be between 1 and 1000 meters")
    return round(width, 2)


def _empty() -> dict[str, Any]:
    return {
        "version": 1,
        "floors": [],
        "aps": {},
        "privacy": {"locate_persons": False, "persons": []},
    }


def _valid_floor(floor: Any) -> bool:
    if not isinstance(floor, dict):
        return False
    try:
        return (
            bool(floor.get("id"))
            and bool(_IMAGE_NAME_RE.match(str(floor.get("image") or "")))
            and int(floor.get("width") or 0) > 0
            and int(floor.get("height") or 0) > 0
            and bool(str(floor.get("name") or "").strip())
        )
    except (TypeError, ValueError):
        return False


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    """Drop invalid parts of a loaded file instead of failing as a whole."""
    result = _empty()
    floors = [f for f in data.get("floors") or [] if _valid_floor(f)]
    for floor in floors:
        floor["level"] = int(floor.get("level") or 0)
        floor["width"] = int(floor["width"])
        floor["height"] = int(floor["height"])
        try:
            floor["width_m"] = clean_width_m(floor.get("width_m"))
        except FloorplanError:
            floor["width_m"] = None
    result["floors"] = floors
    floor_ids = {f["id"] for f in floors}
    aps = data.get("aps") if isinstance(data.get("aps"), dict) else {}
    for mac, pos in aps.items():
        mac_n = normalize_mac(str(mac))
        if len(mac_n.split(":")) != 6 or not isinstance(pos, dict):
            continue
        if pos.get("floor") not in floor_ids:
            continue
        try:
            result["aps"][mac_n] = {
                "floor": pos["floor"],
                "x": _fraction(pos.get("x")),
                "y": _fraction(pos.get("y")),
            }
        except FloorplanError:
            continue
    privacy = data.get("privacy") if isinstance(data.get("privacy"), dict) else {}
    persons = privacy.get("persons") if isinstance(privacy.get("persons"), list) else []
    result["privacy"] = {
        "locate_persons": privacy.get("locate_persons") is True,
        "persons": sorted({str(p) for p in persons if p}),
    }
    return result


class FloorplanStore:
    """Floor plan file and images of one integration storage directory."""

    def __init__(self, storage: Path) -> None:
        """Initialize (call ``load`` before use)."""
        self.path = storage / FLOORPLANS_FILE
        self.image_dir = storage / FLOORPLAN_IMAGE_DIR
        self._data = _empty()
        self._lock = asyncio.Lock()

    # --- read -----------------------------------------------------------------

    @property
    def floors(self) -> list[dict[str, Any]]:
        """Floors ordered by level, then name."""
        return sorted(
            (dict(f) for f in self._data["floors"]),
            key=lambda f: (f["level"], f["name"].lower()),
        )

    @property
    def ap_positions(self) -> dict[str, dict[str, Any]]:
        """AP positions by normalized MAC."""
        return {mac: dict(pos) for mac, pos in self._data["aps"].items()}

    @property
    def privacy(self) -> dict[str, Any]:
        """Location privacy settings."""
        privacy = self._data["privacy"]
        return {
            "locate_persons": privacy["locate_persons"],
            "persons": list(privacy["persons"]),
        }

    def person_located(self, person_id: str) -> bool:
        """True when this person may be shown on the floor plan."""
        privacy = self._data["privacy"]
        return bool(privacy["locate_persons"]) and person_id in privacy["persons"]

    def floor(self, floor_id: str) -> dict[str, Any] | None:
        """Return one floor."""
        return next(
            (dict(f) for f in self._data["floors"] if f["id"] == floor_id), None
        )

    def image_file(self, floor_id: str) -> tuple[Path, str] | None:
        """Path and content type of a floor image."""
        floor = self.floor(floor_id)
        if floor is None:
            return None
        path = self.image_dir / floor["image"]
        ext = floor["image"].rsplit(".", 1)[-1]
        return path, CONTENT_TYPES[ext]

    def load(self) -> None:
        """Read the file from disk (blocking); a broken file keeps the old state."""
        if not self.path.exists():
            self._data = _empty()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("expected an object")
        except (OSError, ValueError) as err:
            _LOGGER.warning("Keeping previous floor plans after read failure: %s", err)
            return
        self._data = _normalize(raw)

    # --- write ----------------------------------------------------------------

    async def async_change(
        self, hass: HomeAssistant, fn: Callable[..., _T], *args: Any
    ) -> _T:
        """Run one blocking change under the store lock."""
        async with self._lock:
            return await hass.async_add_executor_job(fn, *args)

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(tmp, self.path)
        self._data = data

    def _copy(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._data))

    def _write_image(self, floor_id: str, data: bytes) -> tuple[str, ImageInfo]:
        info = inspect_image(data)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        # A fresh name per upload also busts browser caches.
        name = f"{floor_id}-{secrets.token_hex(4)}.{info.ext}"
        tmp = self.image_dir / f".{name}.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, self.image_dir / name)
        return name, info

    def _remove_image(self, name: str | None) -> None:
        if name and _IMAGE_NAME_RE.match(name):
            try:
                (self.image_dir / name).unlink()
            except FileNotFoundError:
                pass

    def _new_floor_id(self, data: dict[str, Any], name: str) -> str:
        base = _slug(name)[:24]
        taken = {f["id"] for f in data["floors"]}
        candidate, counter = base, 2
        while candidate in taken:
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def add_floor(
        self, name: str, level: int, image: bytes, width_m: float | None
    ) -> dict[str, Any]:
        """Create a floor with its image."""
        data = self._copy()
        floor_id = self._new_floor_id(data, name)
        image_name, info = self._write_image(floor_id, image)
        floor = {
            "id": floor_id,
            "name": name,
            "level": level,
            "image": image_name,
            "width": info.width,
            "height": info.height,
            "width_m": width_m,
        }
        data["floors"].append(floor)
        try:
            self._save(data)
        except OSError:
            self._remove_image(image_name)
            raise
        return dict(floor)

    def _find(self, data: dict[str, Any], floor_id: str) -> dict[str, Any]:
        for floor in data["floors"]:
            if floor["id"] == floor_id:
                return floor
        raise KeyError(floor_id)

    def update_floor(
        self, floor_id: str, name: str, level: int, width_m: float | None
    ) -> dict[str, Any]:
        """Rename a floor, change its level or real width."""
        data = self._copy()
        floor = self._find(data, floor_id)
        floor.update(name=name, level=level, width_m=width_m)
        self._save(data)
        return dict(floor)

    def replace_image(self, floor_id: str, image: bytes) -> dict[str, Any]:
        """Swap the image of a floor; AP positions keep their fractions."""
        data = self._copy()
        floor = self._find(data, floor_id)
        old = floor["image"]
        image_name, info = self._write_image(floor_id, image)
        floor.update(image=image_name, width=info.width, height=info.height)
        try:
            self._save(data)
        except OSError:
            self._remove_image(image_name)
            raise
        self._remove_image(old)
        return dict(floor)

    def delete_floor(self, floor_id: str) -> None:
        """Remove a floor, its image and the AP positions on it."""
        data = self._copy()
        floor = self._find(data, floor_id)
        data["floors"] = [f for f in data["floors"] if f["id"] != floor_id]
        data["aps"] = {
            mac: pos for mac, pos in data["aps"].items() if pos["floor"] != floor_id
        }
        self._save(data)
        self._remove_image(floor["image"])

    def set_ap_position(self, mac: str, floor_id: str, x: Any, y: Any) -> dict:
        """Place an AP on a floor."""
        mac_n = normalize_mac(mac)
        if len(mac_n.split(":")) != 6:
            raise FloorplanError("mac must be a MAC address")
        data = self._copy()
        self._find(data, floor_id)
        position = {"floor": floor_id, "x": _fraction(x), "y": _fraction(y)}
        data["aps"][mac_n] = position
        self._save(data)
        return dict(position)

    def clear_ap_position(self, mac: str) -> bool:
        """Take an AP off the floor plan."""
        mac_n = normalize_mac(mac)
        data = self._copy()
        if data["aps"].pop(mac_n, None) is None:
            return False
        self._save(data)
        return True

    def set_privacy(self, locate_persons: bool, persons: list[str]) -> dict:
        """Store the location switch and the released persons."""
        data = self._copy()
        data["privacy"] = {
            "locate_persons": bool(locate_persons),
            "persons": sorted({str(p) for p in persons if p}),
        }
        self._save(data)
        return dict(data["privacy"])

    def remove_person(self, person_id: str) -> bool:
        """Drop the location release of a deleted person."""
        data = self._copy()
        persons = data["privacy"]["persons"]
        if person_id not in persons:
            return False
        data["privacy"]["persons"] = [p for p in persons if p != person_id]
        self._save(data)
        return True

    def import_floors(self, floors: list[ImportedFloor]) -> dict[str, Any]:
        """Merge imported floors: same name replaces the image, else a new floor.

        Imported AP positions replace the stored position of the same AP;
        other APs and floors stay as they are.
        """
        data = self._copy()
        created, updated, placed = 0, 0, 0
        new_images: list[str] = []
        old_images: list[str] = []
        try:
            for item in floors:
                existing = next(
                    (
                        f
                        for f in data["floors"]
                        if f["name"].strip().lower() == item.name.strip().lower()
                    ),
                    None,
                )
                floor_id = (
                    existing["id"] if existing else self._new_floor_id(data, item.name)
                )
                image_name, info = self._write_image(floor_id, item.image)
                new_images.append(image_name)
                if existing is None:
                    data["floors"].append(
                        {
                            "id": floor_id,
                            "name": item.name,
                            "level": item.level,
                            "image": image_name,
                            "width": info.width,
                            "height": info.height,
                            "width_m": item.width_m,
                        }
                    )
                    created += 1
                else:
                    old_images.append(existing["image"])
                    existing.update(
                        image=image_name,
                        width=info.width,
                        height=info.height,
                        level=item.level,
                    )
                    if item.width_m is not None:
                        existing["width_m"] = item.width_m
                    updated += 1
                for mac, x, y in item.aps:
                    data["aps"][normalize_mac(mac)] = {
                        "floor": floor_id,
                        "x": _fraction(x),
                        "y": _fraction(y),
                    }
                    placed += 1
            self._save(data)
        except BaseException:
            for name in new_images:
                self._remove_image(name)
            raise
        for name in old_images:
            self._remove_image(name)
        return {
            "floors_created": created,
            "floors_updated": updated,
            "aps_placed": placed,
        }
