"""Floor plan store: images, AP positions, privacy, import merge."""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from custom_components.unifi_people_pointer.floorplan import (
    FloorplanError,
    FloorplanStore,
    ImportedFloor,
    clean_level,
    clean_name,
    clean_width_m,
    inspect_image,
    signal_radius_m,
)

pytestmark = pytest.mark.unit

AP = "24:5a:4c:aa:bb:cc"


def image_bytes(width: int = 40, height: int = 60, fmt: str = "PNG") -> bytes:
    """Small solid image in the given format."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 200, 190)).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def store(tmp_path) -> FloorplanStore:
    """Empty store in a temporary storage directory."""
    result = FloorplanStore(tmp_path)
    result.load()
    return result


def test_inspect_image_formats():
    """PNG, JPEG and WebP pass with their size; other files do not."""
    assert inspect_image(image_bytes(40, 60)).__dict__ == {
        "ext": "png",
        "width": 40,
        "height": 60,
    }
    assert inspect_image(image_bytes(10, 5, "JPEG")).ext == "jpg"
    assert inspect_image(image_bytes(10, 5, "WEBP")).ext == "webp"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>x()</script></svg>'
    for data in (b"", b"not an image", svg, image_bytes(8, 8, "GIF")):
        with pytest.raises(FloorplanError):
            inspect_image(data)


def test_inspect_image_limits(monkeypatch):
    """Too many bytes or too large sides are rejected."""
    # The module object the function was imported from (conftest re-imports).
    module_globals = inspect_image.__globals__
    monkeypatch.setitem(module_globals, "FLOORPLAN_MAX_IMAGE_BYTES", 10)
    with pytest.raises(FloorplanError, match="larger"):
        inspect_image(image_bytes())
    monkeypatch.setitem(module_globals, "FLOORPLAN_MAX_IMAGE_BYTES", 10**7)
    monkeypatch.setitem(module_globals, "FLOORPLAN_MAX_IMAGE_SIDE", 50)
    with pytest.raises(FloorplanError, match="sides"):
        inspect_image(image_bytes(40, 60))


def test_signal_radius():
    """Strong signal: small circle; weak: large; unknown: medium."""
    assert signal_radius_m(-30) == 2.0
    assert signal_radius_m(-60) == pytest.approx(4.6, abs=0.1)
    assert signal_radius_m(-70) == pytest.approx(10.0, abs=0.1)
    assert signal_radius_m(-90) == 15.0
    assert signal_radius_m(-60) < signal_radius_m(-70)
    for value in (None, "x", 0, 45, float("nan")):
        assert signal_radius_m(value) == 8.0


def test_field_validation():
    """Names, levels and widths are checked."""
    assert clean_name("  EG ") == "EG"
    assert clean_level("-1") == -1
    assert clean_level(None) == 0
    assert clean_width_m("") is None
    assert clean_width_m("12.345") == 12.35
    for fn, value in (
        (clean_name, ""),
        (clean_name, "x" * 41),
        (clean_level, "1.5"),
        (clean_level, 500),
        (clean_width_m, "abc"),
        (clean_width_m, 0),
    ):
        with pytest.raises(FloorplanError):
            fn(value)


def test_add_floor_writes_image_and_file(store, tmp_path):
    """A new floor gets a slug id, its image and its pixel size."""
    floor = store.add_floor("Ground floor", 0, image_bytes(40, 60), 12.0)
    assert floor["id"] == "ground-floor"
    assert (floor["width"], floor["height"], floor["width_m"]) == (40, 60, 12.0)
    path, content_type = store.image_file("ground-floor")
    assert path.is_file() and path.parent == tmp_path / "floorplans"
    assert content_type == "image/png"
    saved = json.loads((tmp_path / "floorplans.json").read_text())
    assert saved["floors"][0]["image"] == path.name
    assert saved["privacy"] == {"locate_persons": False, "persons": []}

    again = store.add_floor("Ground floor", 1, image_bytes(), None)
    assert again["id"] == "ground-floor-2"
    assert [f["id"] for f in store.floors] == ["ground-floor", "ground-floor-2"]


def test_invalid_upload_leaves_no_file(store, tmp_path):
    """A rejected image changes nothing."""
    with pytest.raises(FloorplanError):
        store.add_floor("EG", 0, b"nope", None)
    assert store.floors == []
    assert not (tmp_path / "floorplans.json").exists()


def test_floors_sorted_by_level(store):
    """Basement first, then ground floor, then upper floors."""
    store.add_floor("OG", 1, image_bytes(), None)
    store.add_floor("KG", -1, image_bytes(), None)
    store.add_floor("EG", 0, image_bytes(), None)
    assert [f["name"] for f in store.floors] == ["KG", "EG", "OG"]


def test_ap_positions_and_delete_floor(store, tmp_path):
    """Positions are fractions; deleting a floor drops its APs and image."""
    store.add_floor("EG", 0, image_bytes(), None)
    store.add_floor("OG", 1, image_bytes(), None)
    assert store.set_ap_position("24-5A-4C-AA-BB-CC", "eg", 0.25, "0.5") == {
        "floor": "eg",
        "x": 0.25,
        "y": 0.5,
    }
    store.set_ap_position("24:5a:4c:aa:bb:dd", "og", 1, 0)
    assert store.ap_positions[AP] == {"floor": "eg", "x": 0.25, "y": 0.5}
    for bad in ((AP, "eg", 1.2, 0.5), (AP, "eg", "x", 0.5), ("nope", "eg", 0, 0)):
        with pytest.raises(FloorplanError):
            store.set_ap_position(*bad)
    with pytest.raises(KeyError):
        store.set_ap_position(AP, "missing", 0.1, 0.1)

    image = store.image_file("eg")[0]
    store.delete_floor("eg")
    assert not image.exists()
    assert set(store.ap_positions) == {"24:5a:4c:aa:bb:dd"}
    assert store.clear_ap_position("24:5a:4c:aa:bb:dd") is True
    assert store.clear_ap_position("24:5a:4c:aa:bb:dd") is False


def test_replace_image_keeps_positions(store):
    """A new image with another size keeps AP fractions and drops the old file."""
    store.add_floor("EG", 0, image_bytes(40, 60), None)
    store.set_ap_position(AP, "eg", 0.5, 0.5)
    old = store.image_file("eg")[0]
    floor = store.replace_image("eg", image_bytes(400, 600, "JPEG"))
    assert (floor["width"], floor["height"]) == (400, 600)
    assert not old.exists()
    assert store.image_file("eg")[1] == "image/jpeg"
    assert store.ap_positions[AP]["x"] == 0.5


def test_update_floor(store):
    """Rename, new level and width."""
    store.add_floor("EG", 0, image_bytes(), None)
    floor = store.update_floor("eg", "Erdgeschoss", 2, 14.5)
    assert (floor["id"], floor["name"], floor["level"], floor["width_m"]) == (
        "eg",
        "Erdgeschoss",
        2,
        14.5,
    )
    with pytest.raises(KeyError):
        store.update_floor("missing", "x", 0, None)


def test_privacy(store):
    """Locating is off by default and needs the switch plus a released person."""
    assert store.person_located("jane") is False
    store.set_privacy(False, ["jane"])
    assert store.person_located("jane") is False
    store.set_privacy(True, ["jane", "jane", ""])
    assert store.privacy == {"locate_persons": True, "persons": ["jane"]}
    assert store.person_located("jane") is True
    assert store.person_located("john") is False


def test_load_drops_invalid_parts(tmp_path):
    """Broken entries are skipped, a broken file keeps the previous state."""
    (tmp_path / "floorplans.json").write_text(
        json.dumps(
            {
                "floors": [
                    {
                        "id": "eg",
                        "name": "EG",
                        "image": "eg-1.png",
                        "width": 4,
                        "height": 3,
                    },
                    {
                        "id": "bad",
                        "name": "Bad",
                        "image": "../x.png",
                        "width": 4,
                        "height": 3,
                    },
                    "junk",
                ],
                "aps": {
                    AP: {"floor": "eg", "x": 0.1, "y": 0.2},
                    "24:5a:4c:aa:bb:dd": {"floor": "bad", "x": 0.1, "y": 0.2},
                    "24:5a:4c:aa:bb:ee": {"floor": "eg", "x": 7, "y": 0.2},
                    "nope": {"floor": "eg", "x": 0.1, "y": 0.2},
                },
                "privacy": {"locate_persons": "yes", "persons": ["a"]},
            }
        )
    )
    store = FloorplanStore(tmp_path)
    store.load()
    assert [f["id"] for f in store.floors] == ["eg"]
    assert list(store.ap_positions) == [AP]
    assert store.privacy == {"locate_persons": False, "persons": ["a"]}

    (tmp_path / "floorplans.json").write_text("{broken")
    store.load()
    assert [f["id"] for f in store.floors] == ["eg"]


def test_import_merges_by_name(store):
    """Same floor name replaces the image; imported APs override positions."""
    store.add_floor("EG", 0, image_bytes(40, 60), 11.0)
    store.add_floor("Attic", 3, image_bytes(), None)
    store.set_ap_position(AP, "attic", 0.9, 0.9)
    store.set_ap_position("24:5a:4c:aa:bb:ee", "attic", 0.1, 0.1)
    old_eg = store.image_file("eg")[0]

    summary = store.import_floors(
        [
            ImportedFloor(
                name="eg", level=0, image=image_bytes(80, 120), aps=[(AP, 0.25, 0.75)]
            ),
            ImportedFloor(name="KG", level=-1, image=image_bytes(), width_m=9.5),
        ]
    )
    assert summary == {"floors_created": 1, "floors_updated": 1, "aps_placed": 1}
    assert not old_eg.exists()
    eg = store.floor("eg")
    assert (eg["width"], eg["height"], eg["width_m"]) == (80, 120, 11.0)
    assert store.ap_positions[AP] == {"floor": "eg", "x": 0.25, "y": 0.75}
    assert store.ap_positions["24:5a:4c:aa:bb:ee"]["floor"] == "attic"
    assert store.floor("kg")["width_m"] == 9.5


def test_import_with_bad_image_changes_nothing(store, tmp_path):
    """One unreadable image aborts the whole import without leftovers."""
    with pytest.raises(FloorplanError):
        store.import_floors(
            [
                ImportedFloor(name="EG", level=0, image=image_bytes()),
                ImportedFloor(name="OG", level=1, image=b"broken"),
            ]
        )
    assert store.floors == []
    assert not list((tmp_path / "floorplans").glob("*"))
