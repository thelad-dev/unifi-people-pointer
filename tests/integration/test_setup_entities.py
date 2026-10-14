"""Regression: setup must create person trackers (not load empty)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unifi_people_pointer.const import DOMAIN, STORAGE_DIR


pytestmark = pytest.mark.integration


async def test_setup_creates_person_and_device_trackers(
    hass, devices_data, people_data, mock_unifi_api_clients_online
):
    """Loaded entry with people/devices JSON must expose tracker entities.

    Reproduces the prior failure mode: entry state=loaded but zero integration
    entities because platforms were deferred and trackers stayed empty.
    """
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "192.168.88.1",
            "token": "test-token",
            "verify_ssl": False,
        },
        options={"scan_interval": 45, "event_debounce": 0},
        title="UniFi People Pointer",
        unique_id="192.168.88.1",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator._fetch_clients",
        new=AsyncMock(return_value=mock_unifi_api_clients_online),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    # Person trackers (Zielbild: people, not only HACS update entity)
    janine = hass.states.get("device_tracker.janine")
    sebastian = hass.states.get("device_tracker.sebastian")
    assert janine is not None
    assert sebastian is not None
    assert janine.state == "home"
    assert sebastian.state == "home"

    # Sensors exist
    assert hass.states.get("sensor.unknown_wifi_clients") is not None
    assert hass.states.get("sensor.guest_wifi_clients") is not None

    # Device tracker for a known phone
    assert hass.states.get("device_tracker.iphone_jd") is not None


async def test_setup_marks_person_away_when_no_clients(
    hass, devices_data, people_data
):
    """Person trackers go not_home when UniFi returns no clients."""
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "192.168.88.1",
            "token": "test-token",
            "verify_ssl": False,
        },
        options={"event_debounce": 0},
        title="UniFi People Pointer",
        unique_id="test-away",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator._fetch_clients",
        new=AsyncMock(return_value=[]),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    janine = hass.states.get("device_tracker.janine")
    assert janine is not None
    assert janine.state == "not_home"


async def test_scan_picks_up_devices_json_change(
    hass, devices_data, people_data, mock_unifi_api_clients_online
):
    """Editing devices.json then refreshing must flip person presence."""
    storage = Path(hass.config.path(STORAGE_DIR))
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "devices.json").write_text(json.dumps(devices_data), encoding="utf-8")
    (storage / "people.json").write_text(json.dumps(people_data), encoding="utf-8")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "192.168.88.1",
            "token": "test-token",
            "verify_ssl": False,
        },
        options={"event_debounce": 0},
        title="UniFi People Pointer",
        unique_id="test-json-reload",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.unifi_people_pointer.coordinator.UniFiPeoplePointerCoordinator._fetch_clients",
        new=AsyncMock(return_value=mock_unifi_api_clients_online),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert hass.states.get("device_tracker.janine").state == "home"

        patched = json.loads((storage / "devices.json").read_text(encoding="utf-8"))
        for device in patched["devices"]:
            if device["id"] == "iphone-jd":
                device["mac"] = "de:ad:be:ef:00:01"
                device["hostname_match"] = ["__no_such_host__"]
        (storage / "devices.json").write_text(
            json.dumps(patched), encoding="utf-8"
        )

        coordinator = hass.data[DOMAIN]["coordinator"]
        await coordinator.async_request_refresh()
        await hass.async_block_till_done()

        assert hass.states.get("device_tracker.janine").state == "not_home"
