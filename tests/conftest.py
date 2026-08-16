"""Pytest configuration and shared fixtures for UniFi People Pointer tests."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_HOST, CONF_TOKEN
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"

# Project root must win over pytest-homeassistant's testing_config/custom_components.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations from this repository.

    Home Assistant's test harness mounts ``testing_config`` and can cache an empty
    ``custom_components`` package in ``sys.modules``. Clear that cache so our
    integration under ``./custom_components`` is discoverable.
    """
    for key in list(sys.modules):
        if key == "custom_components" or key.startswith("custom_components."):
            del sys.modules[key]

    if sys.path[0] != str(_PROJECT_ROOT):
        sys.path.insert(0, str(_PROJECT_ROOT))

    import custom_components  # noqa: F401

    yield


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain="unifi_people_pointer",
        data={
            CONF_HOST: "192.168.88.1",
            CONF_TOKEN: "test_api_token_12345",
            "verify_ssl": False,
        },
        unique_id="unifi_people_pointer_test",
        title="UniFi People Pointer",
    )


@pytest.fixture
def manufacturers_data():
    """Return sample manufacturers data."""
    return {
        "version": 1,
        "source": "https://standards-oui.ieee.org/oui/oui.csv",
        "manufacturers": [
            {
                "id": "apple",
                "oui_prefixes": ["00:03:93", "00:05:02", "38:7f:8b", "1c:3c:78"],
                "ieee_assignment_names": ["Apple, Inc."],
            },
            {
                "id": "samsung",
                "oui_prefixes": ["00:00:f0", "50:32:75"],
                "ieee_assignment_names": ["Samsung Electronics Co.,Ltd"],
            },
            {
                "id": "google",
                "oui_prefixes": ["3c:5a:b4", "f4:f5:e8"],
                "ieee_assignment_names": ["Google, Inc."],
            },
        ],
    }


@pytest.fixture
def devices_data():
    """Return sample devices data."""
    return {
        "version": 1,
        "devices": [
            {
                "id": "iphone-jd",
                "name": "iPhone-JD",
                "type": "smartphone",
                "manufacturer_id": "apple",
                "mac": "1c:3c:78:b8:ae:b5",
                "hostname_match": ["iPhone-JD"],
                "track": True,
                "notes": "Primary iPhone",
            },
            {
                "id": "iphone-skhl",
                "name": "iPhone-SKHL",
                "type": "smartphone",
                "manufacturer_id": "apple",
                "mac": "38:7f:8b:da:18:20",
                "hostname_match": ["iPhone-SKHL"],
                "track": True,
                "notes": "Primary iPhone Sebastian",
            },
            {
                "id": "android-helgas",
                "name": "android-00A90B444CB7",
                "type": "smartphone",
                "manufacturer_id": None,
                "mac": "00:a9:0b:44:4c:b7",
                "hostname_match": ["android-00A90B444CB7"],
                "track": True,
                "notes": "Android device",
            },
            {
                "id": "watch-1",
                "name": "Watch",
                "type": "wearable",
                "manufacturer_id": "apple",
                "mac": "82:9c:1a:5e:d0:28",
                "hostname_match": ["Watch"],
                "track": True,
                "notes": "Apple Watch with private MAC",
            },
            {
                "id": "iphone-legacy",
                "name": "iPhone",
                "type": "smartphone",
                "manufacturer_id": "apple",
                "mac": "02:a2:54:a8:e1:98",
                "hostname_match": ["iPhone"],
                "track": False,
                "notes": "Old/randomized MAC - not tracked",
            },
        ],
    }


@pytest.fixture
def people_data():
    """Return sample people data."""
    return {
        "version": 1,
        "people": [
            {
                "id": "sebastian",
                "name": "Sebastian",
                "ha_person": "person.ladwein",
                "device_ids": ["iphone-skhl", "watch-1"],
                "notes": None,
            },
            {
                "id": "janine",
                "name": "Janine",
                "ha_person": "person.janine",
                "device_ids": ["iphone-jd"],
                "notes": None,
            },
            {
                "id": "tablet",
                "name": "Tablet",
                "ha_person": "person.android",
                "device_ids": ["android-helgas"],
                "notes": None,
            },
        ],
    }


@pytest.fixture
def mock_unifi_api_clients_online():
    """Return sample UniFi API response with online clients."""
    return [
        {
            "mac": "1c:3c:78:b8:ae:b5",
            "hostname": "iPhone-JD",
            "ip": "192.168.88.101",
            "last_seen": 1734567890,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:cc",
            "signal": -45,
            "channel": 36,
            "essid": "HomeNetwork",
        },
        {
            "mac": "38:7f:8b:da:18:20",
            "hostname": "iPhone-SKHL",
            "ip": "192.168.88.102",
            "last_seen": 1734567895,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:cc",
            "signal": -52,
            "channel": 36,
            "essid": "HomeNetwork",
        },
        {
            "mac": "82:9c:1a:5e:d0:28",
            "hostname": "Watch",
            "ip": "192.168.88.103",
            "last_seen": 1734567880,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:dd",
            "signal": -65,
            "channel": 149,
            "essid": "HomeNetwork",
        },
    ]


@pytest.fixture
def mock_unifi_api_clients_flapping():
    """Return UniFi API response simulating flapping WiFi connections."""
    return [
        {
            "mac": "1c:3c:78:b8:ae:b5",
            "hostname": "iPhone-JD",
            "ip": "192.168.88.101",
            "last_seen": 1734567890,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:cc",
            "signal": -72,  # Poor signal
            "channel": 36,
            "essid": "HomeNetwork",
        }
    ]


@pytest.fixture
def mock_unifi_api_unknown_macs():
    """Return UniFi API response with unknown MAC addresses."""
    return [
        {
            "mac": "aa:bb:cc:dd:ee:ff",
            "hostname": "UnknownDevice1",
            "ip": "192.168.88.150",
            "last_seen": 1734567890,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:cc",
            "signal": -45,
            "channel": 36,
            "essid": "HomeNetwork",
        },
        {
            "mac": "11:22:33:44:55:66",
            "hostname": None,  # No hostname
            "ip": "192.168.88.151",
            "last_seen": 1734567895,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:cc",
            "signal": -52,
            "channel": 36,
            "essid": "HomeNetwork",
        },
    ]


@pytest.fixture
def mock_unifi_api_duplicate_macs():
    """Return UniFi API response with duplicate MAC addresses (edge case)."""
    return [
        {
            "mac": "1c:3c:78:b8:ae:b5",
            "hostname": "iPhone-JD",
            "ip": "192.168.88.101",
            "last_seen": 1734567890,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:cc",
            "signal": -45,
            "channel": 36,
            "essid": "HomeNetwork",
        },
        {
            "mac": "1c:3c:78:b8:ae:b5",  # Duplicate MAC
            "hostname": "iPhone-JD",
            "ip": "192.168.88.201",  # Different IP
            "last_seen": 1734567895,
            "is_wired": False,
            "ap_mac": "24:5a:4c:aa:bb:dd",  # Different AP
            "signal": -52,
            "channel": 149,
            "essid": "HomeNetwork",
        },
    ]


@pytest.fixture
def mock_unifi_api_empty():
    """Return empty UniFi API response (no clients)."""
    return []


@pytest.fixture
async def mock_unifi_client():
    """Return a mock UniFi API client."""
    client = AsyncMock()
    client.get_clients = AsyncMock()
    client.get_sites = AsyncMock(return_value=[{"name": "default", "desc": "Default"}])
    client.is_connected = True
    return client


@pytest.fixture
def mock_data_files(tmp_path, manufacturers_data, devices_data, people_data):
    """Create temporary data files for testing."""
    manufacturers_file = tmp_path / "manufacturers.json"
    devices_file = tmp_path / "devices.json"
    people_file = tmp_path / "people.json"

    manufacturers_file.write_text(json.dumps(manufacturers_data, indent=2))
    devices_file.write_text(json.dumps(devices_data, indent=2))
    people_file.write_text(json.dumps(people_data, indent=2))

    return {
        "manufacturers": manufacturers_file,
        "devices": devices_file,
        "people": people_file,
    }
