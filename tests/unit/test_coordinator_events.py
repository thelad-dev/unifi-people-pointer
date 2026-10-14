"""Behavioral coverage for coordinator presence event transitions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_people_pointer.const import DOMAIN, STORAGE_DIR
from custom_components.unifi_people_pointer.coordinator import (
    UniFiPeoplePointerCoordinator,
)

pytestmark = pytest.mark.unit


def _client(mac: str, hostname: str = "phone") -> dict:
    return {
        "mac": mac,
        "hostname": hostname,
        "is_wired": False,
        "is_guest": False,
        "essid": "home",
        "ip": "192.168.1.10",
        "ap_mac": "aa:aa:aa:aa:aa:01",
        "signal": -50,
    }


async def _make_coordinator(hass, tmp_path=None) -> UniFiPeoplePointerCoordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.1", "token": "t", "verify_ssl": False},
        options={"scan_interval": 60},
        unique_id="coord-events",
        title="UPP",
    )
    entry.add_to_hass(hass)
    coordinator = UniFiPeoplePointerCoordinator(hass, entry)
    if tmp_path is not None:
        storage = tmp_path / STORAGE_DIR
        storage.mkdir(parents=True, exist_ok=True)
        coordinator.storage_path = storage
        coordinator._loader._devices_path = storage / "devices.json"
        coordinator._loader._people_path = storage / "people.json"
        coordinator._loader._manufacturers_path = storage / "manufacturers.json"
    event_manager = MagicMock()
    hass.data.setdefault(DOMAIN, {})["event_manager"] = event_manager
    hass.data[DOMAIN]["coordinator"] = coordinator
    return coordinator


def _stop_coordinator(coordinator: UniFiPeoplePointerCoordinator) -> None:
    """Cancel scheduled refresh handles left by mutate/publish paths."""
    coordinator._async_unsub_refresh()
    coordinator._debounced_refresh.async_cancel()


def _set_config(
    coordinator: UniFiPeoplePointerCoordinator,
    *,
    people: list[dict],
    devices: list[dict],
) -> None:
    coordinator._loader._people = {"version": 1, "people": people}
    coordinator._loader._devices = {"version": 1, "devices": devices}


async def test_new_home_person_after_prime_fires_arrived(hass) -> None:
    """After priming, a newly introduced home person schedules person_arrived."""
    coordinator = await _make_coordinator(hass)
    mac = "aa:bb:cc:dd:ee:01"
    device = {
        "id": "dev-phone",
        "name": "Phone",
        "mac": mac,
        "type": "phone",
        "track": True,
        "hostname_match": [],
    }
    _set_config(
        coordinator,
        people=[],
        devices=[device],
    )
    clients = [_client(mac)]

    # Prime baseline with no people: no person events.
    coordinator._rebuild_presence_state(clients)
    event_manager = hass.data[DOMAIN]["event_manager"]
    event_manager.fire_person_arrived.assert_not_called()
    assert coordinator._events_primed is True

    # Introduce sebastian already home via the online device.
    _set_config(
        coordinator,
        people=[
            {
                "id": "sebastian",
                "name": "Sebastian",
                "device_ids": ["dev-phone"],
            }
        ],
        devices=[device],
    )
    coordinator._rebuild_presence_state(clients)

    event_manager.fire_person_arrived.assert_called()
    args, kwargs = event_manager.fire_person_arrived.call_args
    assert kwargs.get("person") == "sebastian" or (args and args[0] == "sebastian")


async def test_device_connected_reschedules_on_owner_change(hass) -> None:
    """Ownership change while online cancels and reschedules device_connected."""
    coordinator = await _make_coordinator(hass)
    mac = "aa:bb:cc:dd:ee:02"
    device = {
        "id": "iphone-jd",
        "name": "iPhone",
        "mac": mac,
        "type": "phone",
        "track": True,
        "hostname_match": [],
    }
    clients = [_client(mac, hostname="iphone")]

    # Unassigned online device primes baseline and schedules connected w/o person.
    _set_config(coordinator, people=[], devices=[device])
    coordinator._rebuild_presence_state(clients)
    event_manager = hass.data[DOMAIN]["event_manager"]
    # First rebuild primes without firing (events_primed starts false).
    event_manager.fire_device_connected.assert_not_called()

    # Second rebuild with same state still no transition.
    coordinator._rebuild_presence_state(clients)
    event_manager.fire_device_connected.assert_not_called()

    # Device goes through online transition after being offline baseline.
    coordinator._prev_online_device_ids = set()
    coordinator._prev_device_owners = {}
    coordinator._rebuild_presence_state(clients)
    event_manager.fire_device_connected.assert_called()
    first_person = event_manager.fire_device_connected.call_args.kwargs.get("person")
    assert first_person is None
    event_manager.reset_mock()

    # Assign exclusively to sebastian while still online.
    _set_config(
        coordinator,
        people=[
            {
                "id": "sebastian",
                "name": "Sebastian",
                "device_ids": ["iphone-jd"],
            }
        ],
        devices=[device],
    )
    coordinator._rebuild_presence_state(clients)

    event_manager.cancel_device_event.assert_called()
    event_manager.fire_device_connected.assert_called()
    new_person = event_manager.fire_device_connected.call_args.kwargs.get("person")
    assert new_person == "sebastian"


async def test_auth_failure_raises_after_last_good_rebuild(hass, tmp_path) -> None:
    """PermissionError fails closed after applying last-good client rebuild."""
    coordinator = await _make_coordinator(hass, tmp_path=tmp_path)
    mac = "aa:bb:cc:dd:ee:03"
    device = {
        "id": "dev-a",
        "name": "A",
        "mac": mac,
        "type": "phone",
        "track": True,
        "hostname_match": [],
    }
    people = [{"id": "janine", "name": "Janine", "device_ids": ["dev-a"]}]
    _set_config(coordinator, people=people, devices=[device])
    coordinator._rebuild_presence_state([_client(mac)])
    assert coordinator.get_person_state("janine") == "home"

    async def _auth_fail():
        raise PermissionError("Invalid API token")

    coordinator._fetch_clients = _auth_fail  # type: ignore[method-assign]
    coordinator._loader.reload = lambda: None  # already in-memory

    with pytest.raises(UpdateFailed, match="authentication failed"):
        await coordinator._async_update_data()

    # Config/presence still recomputed from last-good clients before fail-closed.
    assert coordinator.get_person_state("janine") == "home"


async def test_assign_does_not_seed_friendly_name_as_partial(hass, tmp_path) -> None:
    """device_name is display-only; hostname_match keeps live UniFi hostname."""
    coordinator = await _make_coordinator(hass, tmp_path=tmp_path)
    seb_mac = "aa:bb:cc:dd:ee:10"
    jan_mac = "aa:bb:cc:dd:ee:11"
    coordinator._all_clients = [
        _client(seb_mac, hostname="iPhone-SK"),
        _client(jan_mac, hostname="iPhone-JD"),
    ]
    coordinator._clients_by_mac = {c["mac"]: c for c in coordinator._all_clients}
    coordinator._rebuild_presence_state(list(coordinator._all_clients))

    # Sebastian already owns the SK phone.
    (tmp_path / STORAGE_DIR / "devices.json").write_text(
        '{"version":1,"devices":[{"id":"iphone-sk","name":"Sebastian Phone",'
        '"mac":"aa:bb:cc:dd:ee:10","hostname_match":["iPhone-SK"],"track":true}]}',
        encoding="utf-8",
    )
    (tmp_path / STORAGE_DIR / "people.json").write_text(
        '{"version":1,"people":[{"id":"sebastian","name":"Sebastian",'
        '"device_ids":["iphone-sk"]}]}',
        encoding="utf-8",
    )
    coordinator._loader.reload()

    await coordinator.assign_device(jan_mac, "janine", "primary", device_name="iPhone")

    devices = coordinator.devices
    jan_dev = next(d for d in devices if d.get("mac") == jan_mac)
    assert jan_dev["name"] == "iPhone"
    assert jan_dev.get("hostname_match") == ["iPhone-JD"]
    assert "iPhone" not in (jan_dev.get("hostname_match") or [])

    assert coordinator.get_person_state("sebastian") == "home"
    assert coordinator.get_person_state("janine") == "home"
    jan_online = (coordinator.get_person_presence("janine") or {}).get(
        "online_device_ids"
    ) or []
    assert "iphone-sk" not in jan_online
    assert any(str(i).startswith("dev-") or i == jan_dev.get("id") for i in jan_online)
    _stop_coordinator(coordinator)


async def test_assign_publishes_presence_before_refresh(hass, tmp_path) -> None:
    """Mutate rebuild notifies listeners immediately, not only after UniFi fetch."""
    coordinator = await _make_coordinator(hass, tmp_path=tmp_path)
    mac = "aa:bb:cc:dd:ee:20"
    coordinator._all_clients = [_client(mac, hostname="Pixel-J")]
    coordinator._clients_by_mac = {mac: coordinator._all_clients[0]}
    coordinator._rebuild_presence_state(list(coordinator._all_clients))

    (tmp_path / STORAGE_DIR / "devices.json").write_text(
        '{"version":1,"devices":[]}', encoding="utf-8"
    )
    (tmp_path / STORAGE_DIR / "people.json").write_text(
        '{"version":1,"people":[]}', encoding="utf-8"
    )
    coordinator._loader.reload()

    notified: list[object] = []

    def _listener() -> None:
        notified.append(coordinator.data)

    coordinator.async_add_listener(_listener)

    async def _slow_fetch():
        # Should not be required for the first presence publish.
        raise ConnectionError("network down")

    coordinator._fetch_clients = _slow_fetch  # type: ignore[method-assign]

    await coordinator.assign_device(mac, "sebastian", "primary", device_name="Pixel")

    assert notified, "assign must publish via async_set_updated_data"
    assert coordinator.get_person_state("sebastian") == "home"
    assert coordinator.data is not None
    assert any(
        row.get("id") == "sebastian" and row.get("is_home")
        for row in (coordinator.data.get("presence") or [])
    )
    _stop_coordinator(coordinator)


async def test_integration_nonlist_payload_keeps_last_good(hass, tmp_path) -> None:
    """Non-list integration payload must not wipe clients to all-offline."""
    coordinator = await _make_coordinator(hass, tmp_path=tmp_path)
    mac = "aa:bb:cc:dd:ee:30"
    device = {
        "id": "dev-b",
        "name": "B",
        "mac": mac,
        "type": "phone",
        "track": True,
        "hostname_match": [],
    }
    people = [{"id": "janine", "name": "Janine", "device_ids": ["dev-b"]}]
    _set_config(coordinator, people=people, devices=[device])
    coordinator._rebuild_presence_state([_client(mac)])
    assert coordinator.get_person_state("janine") == "home"

    async def _bad_payload():
        raise ConnectionError("UniFi clients API returned no client list")

    coordinator._fetch_clients = _bad_payload  # type: ignore[method-assign]
    coordinator._loader.reload = lambda: None

    data = await coordinator._async_update_data()
    assert coordinator.get_person_state("janine") == "home"
    assert data["clients"]


async def test_untracked_mac_not_online(hass, tmp_path) -> None:
    """track:false devices stay offline for is_device_online and connected flags."""
    coordinator = await _make_coordinator(hass, tmp_path=tmp_path)
    mac = "aa:bb:cc:dd:ee:40"
    device = {
        "id": "galaxy-tab",
        "name": "Tab",
        "mac": mac,
        "type": "tablet",
        "track": False,
        "hostname_match": [],
    }
    people = [{"id": "janine", "name": "Janine", "device_ids": ["galaxy-tab"]}]
    _set_config(coordinator, people=people, devices=[device])
    coordinator._rebuild_presence_state([_client(mac, hostname="galaxy")])

    assert coordinator.get_person_state("janine") == "away"
    assert coordinator.is_device_online(mac) is False
    person_devices = coordinator.get_person_devices("janine")
    primary = person_devices.get("primary") or {}
    assert primary.get("connected") is False
    _stop_coordinator(coordinator)


async def test_mac_index_prefers_tracked_over_untracked_shadow(hass, tmp_path) -> None:
    """Duplicate MAC rows keep the tracked device for is_device_online."""
    coordinator = await _make_coordinator(hass, tmp_path=tmp_path)
    mac = "aa:bb:cc:dd:ee:50"
    devices = [
        {
            "id": "phone",
            "name": "Phone",
            "mac": mac,
            "type": "phone",
            "track": True,
            "hostname_match": [],
        },
        {
            "id": "legacy",
            "name": "Legacy",
            "mac": mac,
            "type": "phone",
            "track": False,
            "hostname_match": [],
        },
    ]
    people = [{"id": "janine", "name": "Janine", "device_ids": ["phone"]}]
    _set_config(coordinator, people=people, devices=devices)
    coordinator._rebuild_presence_state([_client(mac, hostname="phone")])

    assert coordinator.get_person_state("janine") == "home"
    assert coordinator.is_device_online(mac) is True
    indexed = coordinator._device_by_configured_mac.get(mac) or {}
    assert indexed.get("id") == "phone"
    _stop_coordinator(coordinator)
