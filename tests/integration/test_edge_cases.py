"""Integration tests for edge cases and error scenarios."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio


@pytest.mark.integration
@pytest.mark.edge_case
class TestUniFiDownScenarios:
    """Test behavior when UniFi controller is completely unavailable."""

    async def test_unifi_controller_offline(self, hass, mock_config_entry):
        """Test when UniFi controller is completely offline."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        with patch.object(coordinator, '_fetch_clients', side_effect=ConnectionError("Controller offline")):
            await coordinator.async_refresh()
            
            assert coordinator.last_update_success is False
            assert "offline" in coordinator.last_exception.lower() or "connection" in coordinator.last_exception.lower()

    async def test_unifi_network_unreachable(self, hass, mock_config_entry):
        """Test when UniFi controller network is unreachable."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        with patch.object(coordinator, '_fetch_clients', side_effect=OSError("Network is unreachable")):
            await coordinator.async_refresh()
            
            assert coordinator.last_update_success is False

    async def test_unifi_api_timeout(self, hass, mock_config_entry):
        """Test when UniFi API requests timeout."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry, request_timeout=5)
        
        async def slow_fetch():
            await asyncio.sleep(10)  # Exceeds timeout
            return []
        
        with patch.object(coordinator, '_fetch_clients', side_effect=slow_fetch):
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(coordinator.async_refresh(), timeout=6)

    async def test_unifi_controller_restarting(self, hass, mock_config_entry):
        """Test when UniFi controller is restarting."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # First few attempts fail, then succeed
        attempt = 0
        
        async def restarting_fetch():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise ConnectionError("Service unavailable")
            return [{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}]
        
        with patch.object(coordinator, '_fetch_clients', side_effect=restarting_fetch):
            # First attempts fail
            await coordinator.async_refresh()
            assert coordinator.last_update_success is False
            
            await coordinator.async_refresh()
            assert coordinator.last_update_success is False
            
            # Third attempt succeeds
            await coordinator.async_refresh()
            assert coordinator.last_update_success is True

    async def test_unifi_firmware_upgrade_downtime(self, hass, mock_config_entry):
        """Test handling extended downtime during firmware upgrade."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # Simulate extended outage (>15 minutes)
        coordinator._outage_start = datetime.now() - timedelta(minutes=20)
        
        with patch.object(coordinator, '_fetch_clients', side_effect=ConnectionError("Upgrading")):
            await coordinator.async_refresh()
            
            # Should have detected extended outage
            assert coordinator.is_extended_outage is True


@pytest.mark.integration
@pytest.mark.edge_case
class TestFlappingWiFi:
    """Test scenarios with unstable WiFi connections."""

    async def test_wifi_rapid_connect_disconnect(self, hass, mock_config_entry, devices_data, people_data):
        """Test rapid connect/disconnect (flapping) detection."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        from custom_components.unifi_people_pointer.presence import detect_flapping
        
        coordinator = UniFiCoordinator(hass, mock_config_entry, flap_detection_window=60)
        
        # Simulate 5 state changes within 60 seconds
        state_changes = []
        base_time = datetime.now()
        
        for i in range(5):
            timestamp = base_time + timedelta(seconds=i * 10)
            state = "online" if i % 2 == 0 else "offline"
            state_changes.append({"timestamp": timestamp, "state": state, "mac": "1c:3c:78:b8:ae:b5"})
        
        is_flapping = detect_flapping(state_changes, threshold=4, window_seconds=60)
        
        assert is_flapping is True

    async def test_wifi_poor_signal_flapping(self, hass, mock_config_entry, mock_unifi_api_clients_flapping):
        """Test flapping caused by poor WiFi signal."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # Poor signal client
        with patch.object(coordinator, '_fetch_clients', return_value=mock_unifi_api_clients_flapping):
            await coordinator.async_refresh()
            
            # Client is present but signal is poor
            assert coordinator.data is not None
            client = coordinator.data[0]
            assert client["signal"] <= -70  # Poor signal threshold

    async def test_wifi_flapping_dampening(self, hass, mock_config_entry, devices_data, people_data):
        """Test dampening/debouncing of flapping state changes."""
        from custom_components.unifi_people_pointer.presence import PresenceTracker
        
        tracker = PresenceTracker(hass, devices_data["devices"], people_data["people"], debounce_seconds=30)
        
        # Rapid state change: online
        tracker.update_presence("person.janine", True)
        
        # Within debounce window: offline
        await asyncio.sleep(0.1)
        tracker.update_presence("person.janine", False)
        
        # Within debounce window: online again
        await asyncio.sleep(0.1)
        tracker.update_presence("person.janine", True)
        
        # Final state should be dampened - still showing last stable state
        assert tracker.get_debounced_state("person.janine") is True

    async def test_wifi_roaming_between_aps(self, hass, mock_config_entry):
        """Test device roaming between access points."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # First update: device on AP1
        clients_ap1 = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "ap_mac": "24:5a:4c:aa:bb:cc"}
        ]
        
        with patch.object(coordinator, '_fetch_clients', return_value=clients_ap1):
            await coordinator.async_refresh()
            first_update = coordinator.data[0]
        
        # Second update: same device roamed to AP2
        clients_ap2 = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "ap_mac": "24:5a:4c:dd:ee:ff"}
        ]
        
        with patch.object(coordinator, '_fetch_clients', return_value=clients_ap2):
            await coordinator.async_refresh()
            second_update = coordinator.data[0]
        
        # MAC should be same, but AP changed
        assert first_update["mac"] == second_update["mac"]
        assert first_update["ap_mac"] != second_update["ap_mac"]

    async def test_wifi_channel_hopping(self, hass, mock_config_entry):
        """Test device experiencing channel changes."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # Track channel changes over time
        channels_seen = []
        
        for channel in [36, 40, 44, 48]:
            clients = [
                {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "channel": channel}
            ]
            
            with patch.object(coordinator, '_fetch_clients', return_value=clients):
                await coordinator.async_refresh()
                channels_seen.append(coordinator.data[0]["channel"])
        
        # Should have seen all different channels
        assert len(set(channels_seen)) == 4


@pytest.mark.integration
@pytest.mark.edge_case
class TestUnknownMACs:
    """Test handling of unknown/unrecognized MAC addresses."""

    async def test_unknown_mac_address(self, hass, mock_config_entry, mock_unifi_api_unknown_macs, devices_data):
        """Test clients with MAC addresses not in devices.json."""
        from custom_components.unifi_people_pointer.device_matcher import match_device
        
        for client in mock_unifi_api_unknown_macs:
            device = match_device(client, devices_data["devices"])
            assert device is None

    async def test_unknown_mac_logging(self, hass, mock_config_entry, mock_unifi_api_unknown_macs):
        """Test that unknown MACs are logged for discovery."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry, log_unknown_macs=True)
        
        with patch.object(coordinator, '_fetch_clients', return_value=mock_unifi_api_unknown_macs):
            with patch('logging.Logger.info') as mock_log:
                await coordinator.async_refresh()
                
                # Should have logged unknown MACs
                assert mock_log.called

    async def test_unknown_mac_manufacturer_hint(self, hass, manufacturers_data, mock_unifi_api_unknown_macs):
        """Test getting manufacturer hint for unknown MACs."""
        from custom_components.unifi_people_pointer.device_matcher import get_manufacturer_hint
        
        for client in mock_unifi_api_unknown_macs:
            hint = get_manufacturer_hint(client, manufacturers_data["manufacturers"])
            
            # Unknown MACs won't match our manufacturers list
            assert hint is None

    async def test_unknown_mac_with_known_oui(self, hass, manufacturers_data):
        """Test unknown MAC but with known OUI prefix."""
        from custom_components.unifi_people_pointer.device_matcher import get_manufacturer_hint
        
        # Unknown device but with Apple OUI
        client = {
            "mac": "38:7f:8b:aa:bb:cc",  # Apple OUI
            "hostname": "NewAppleDevice"
        }
        
        hint = get_manufacturer_hint(client, manufacturers_data["manufacturers"])
        
        assert hint is not None
        assert hint["id"] == "apple"

    async def test_unknown_mac_guest_network(self, hass, mock_config_entry):
        """Test handling of guest network devices (expected unknowns)."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry, track_guest_network=False)
        
        guest_clients = [
            {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "GuestDevice", "essid": "Guest-Network"}
        ]
        
        with patch.object(coordinator, '_fetch_clients', return_value=guest_clients):
            await coordinator.async_refresh()
            
            # Guest network devices should be filtered out
            assert len(coordinator.data) == 0 or coordinator.data[0]["essid"] != "Guest-Network"

    async def test_unknown_mac_iot_device(self, hass, mock_config_entry):
        """Test unknown MAC from IoT device (not tracked for presence)."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        iot_clients = [
            {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "smart-lightbulb-123"}
        ]
        
        with patch.object(coordinator, '_fetch_clients', return_value=iot_clients):
            await coordinator.async_refresh()
            
            # IoT device present but not matched for presence tracking
            assert coordinator.data is not None


@pytest.mark.integration
@pytest.mark.edge_case
class TestDuplicateMACs:
    """Test handling of duplicate MAC addresses."""

    async def test_duplicate_mac_different_aps(self, hass, mock_config_entry, mock_unifi_api_duplicate_macs):
        """Test duplicate MAC appearing on different APs simultaneously."""
        from custom_components.unifi_people_pointer.api_parser import deduplicate_clients
        
        unique_clients = deduplicate_clients(mock_unifi_api_duplicate_macs)
        
        # Should keep only one entry
        assert len(unique_clients) == 1

    async def test_duplicate_mac_keep_most_recent(self, hass, mock_config_entry, mock_unifi_api_duplicate_macs):
        """Test that most recent entry is kept for duplicates."""
        from custom_components.unifi_people_pointer.api_parser import deduplicate_clients
        
        unique_clients = deduplicate_clients(mock_unifi_api_duplicate_macs)
        
        # Should keep the one with higher last_seen timestamp
        assert unique_clients[0]["last_seen"] == 1734567895

    async def test_duplicate_mac_strongest_signal(self, hass, mock_config_entry):
        """Test keeping duplicate with strongest signal."""
        from custom_components.unifi_people_pointer.api_parser import deduplicate_clients_by_signal
        
        duplicates = [
            {"mac": "1c:3c:78:b8:ae:b5", "signal": -65, "ap_mac": "ap1"},
            {"mac": "1c:3c:78:b8:ae:b5", "signal": -45, "ap_mac": "ap2"}
        ]
        
        unique_clients = deduplicate_clients_by_signal(duplicates)
        
        # Should keep the one with better (less negative) signal
        assert unique_clients[0]["signal"] == -45

    async def test_duplicate_mac_api_bug(self, hass, mock_config_entry):
        """Test handling duplicate MACs from API bug/glitch."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # Exact duplicates (API bug)
        buggy_response = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "last_seen": 1734567890},
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "last_seen": 1734567890},
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "last_seen": 1734567890}
        ]
        
        with patch.object(coordinator, '_fetch_clients', return_value=buggy_response):
            await coordinator.async_refresh()
            
            # Should deduplicate to single entry
            macs = [c["mac"] for c in coordinator.data]
            assert macs.count("1c:3c:78:b8:ae:b5") == 1

    async def test_duplicate_mac_private_address_rotation(self, hass, mock_config_entry, devices_data):
        """Test duplicate detection when private address rotates."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        from custom_components.unifi_people_pointer.device_matcher import match_device
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        # Device using private address that rotated
        rotated_clients = [
            {"mac": "82:9c:1a:5e:d0:28", "hostname": "Watch"},  # Old private MAC
            {"mac": "5a:47:03:5a:59:9b", "hostname": "Watch"}   # New private MAC
        ]
        
        # Both should match to watch devices but are different MACs
        matches = [match_device(c, devices_data["devices"]) for c in rotated_clients]
        
        # Both match by hostname
        assert all(m is not None for m in matches)
        assert all(m["type"] == "wearable" for m in matches)

    async def test_duplicate_mac_multiple_vlans(self, hass, mock_config_entry):
        """Test duplicate MAC across different VLANs."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        
        coordinator = UniFiCoordinator(hass, mock_config_entry)
        
        vlan_clients = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "ip": "192.168.1.101"},  # VLAN 1
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "ip": "192.168.2.101"}   # VLAN 2
        ]
        
        with patch.object(coordinator, '_fetch_clients', return_value=vlan_clients):
            await coordinator.async_refresh()
            
            # Should handle gracefully
            assert coordinator.data is not None
