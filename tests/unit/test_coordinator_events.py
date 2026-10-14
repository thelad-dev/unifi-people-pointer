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
