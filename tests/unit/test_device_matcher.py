"""Unit tests for device matching logic."""

import pytest

# Device matcher helpers are still Phase 3 stubs (raise NotImplementedError).
pytestmark = pytest.mark.skip(reason="Requires Phase 3 device_matcher implementation")


@pytest.mark.unit
class TestDeviceMatcher:
    """Test device matching against configured devices."""

    def test_match_by_exact_mac(self, devices_data):
        """Test matching a client by exact MAC address."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        client = {"mac": "1c:3c:78:b8:ae:b5", "hostname": "SomeOtherName"}

        device = match_device(client, devices_data["devices"])

        assert device is not None
        assert device["id"] == "iphone-jd"
        assert device["mac"] == "1c:3c:78:b8:ae:b5"

    def test_match_by_hostname(self, devices_data):
        """Test matching a client by hostname when MAC doesn't match."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        # Client with randomized MAC but known hostname
        client = {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "iPhone-JD"}

        device = match_device(client, devices_data["devices"])

        assert device is not None
        assert device["id"] == "iphone-jd"
        assert device["hostname_match"][0] == "iPhone-JD"

    def test_match_hostname_case_insensitive(self, devices_data):
        """Test that hostname matching is case-insensitive."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        client = {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "iphone-jd"}  # lowercase

        device = match_device(client, devices_data["devices"])

        assert device is not None
        assert device["id"] == "iphone-jd"

    def test_no_match_unknown_device(self, devices_data):
        """Test that unknown devices return None."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        client = {"mac": "ff:ff:ff:ff:ff:ff", "hostname": "UnknownDevice"}

        device = match_device(client, devices_data["devices"])

        assert device is None

    def test_match_only_tracked_devices(self, devices_data):
        """Test filtering to only return tracked devices."""
        from custom_components.unifi_people_pointer.device_matcher import (
            is_tracked,
            match_device,
        )

        # iphone-legacy has track: false
        client = {"mac": "02:a2:54:a8:e1:98", "hostname": "iPhone"}

        device = match_device(client, devices_data["devices"])

        assert device is not None
        assert device["id"] == "iphone-legacy"
        assert not is_tracked(device)

    def test_match_with_null_hostname(self, devices_data):
        """Test matching when client has no hostname."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        client = {"mac": "38:7f:8b:da:18:20", "hostname": None}

        device = match_device(client, devices_data["devices"])

        # Should still match by MAC
        assert device is not None
        assert device["id"] == "iphone-skhl"

    def test_match_multiple_hostname_patterns(self):
        """Test matching against multiple hostname patterns."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        devices = {
            "devices": [
                {
                    "id": "multi-name-device",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "hostname_match": ["DeviceName1", "DeviceName2", "AltName"],
                    "track": True,
                }
            ]
        }

        # Should match any of the patterns
        for hostname in ["DeviceName1", "DeviceName2", "AltName"]:
            client = {"mac": "11:22:33:44:55:66", "hostname": hostname}
            device = match_device(client, devices["devices"])
            assert device is not None
            assert device["id"] == "multi-name-device"

    def test_match_partial_hostname(self):
        """Test that partial hostname matching can be configured."""
        from custom_components.unifi_people_pointer.device_matcher import (
            match_device_partial,
        )

        devices = {
            "devices": [
                {
                    "id": "android-device",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "hostname_match": ["android-"],
                    "track": True,
                }
            ]
        }

        client = {"mac": "11:22:33:44:55:66", "hostname": "android-abc123def456"}

        device = match_device_partial(client, devices["devices"])

        assert device is not None
        assert device["id"] == "android-device"

    def test_match_priority_mac_over_hostname(self, devices_data):
        """Test that MAC match takes priority over hostname match."""
        from custom_components.unifi_people_pointer.device_matcher import match_device

        # Client with one device's MAC but another device's hostname
        client = {
            "mac": "1c:3c:78:b8:ae:b5",  # iphone-jd MAC
            "hostname": "iPhone-SKHL",  # iphone-skhl hostname
        }

        device = match_device(client, devices_data["devices"])

        # Should match by MAC (iphone-jd), not hostname
        assert device is not None
        assert device["id"] == "iphone-jd"

    def test_match_with_oui_prefix(self, devices_data, manufacturers_data):
        """Test matching by OUI prefix as a hint."""
        from custom_components.unifi_people_pointer.device_matcher import (
            get_manufacturer_hint,
        )

        client = {
            "mac": "1c:3c:78:b8:ae:b5",  # Apple OUI
            "hostname": "UnknownAppleDevice",
        }

        manufacturer = get_manufacturer_hint(
            client, manufacturers_data["manufacturers"]
        )

        assert manufacturer is not None
        assert manufacturer["id"] == "apple"

    def test_match_manufacturer_not_in_list(self, manufacturers_data):
        """Test OUI lookup for manufacturer not in our list."""
        from custom_components.unifi_people_pointer.device_matcher import (
            get_manufacturer_hint,
        )

        client = {"mac": "ff:ee:dd:cc:bb:aa", "hostname": "UnknownBrandDevice"}

        manufacturer = get_manufacturer_hint(
            client, manufacturers_data["manufacturers"]
        )

        assert manufacturer is None
