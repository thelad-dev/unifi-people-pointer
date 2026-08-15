"""Integration tests for presence tracking logic."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta


@pytest.mark.integration
class TestPresenceTracking:
    """Test end-to-end presence tracking."""

    async def test_person_home_single_device(self, hass, devices_data, people_data):
        """Test person marked as home when their device is online."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        clients = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}  # Janine's phone
        ]
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        janine = next(p for p in presence if p["id"] == "janine")
        assert janine["is_home"] is True

    async def test_person_away_no_devices(self, hass, devices_data, people_data):
        """Test person marked as away when no devices are online."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        clients = []  # No devices online
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        janine = next(p for p in presence if p["id"] == "janine")
        assert janine["is_home"] is False

    async def test_person_home_multiple_devices(self, hass, devices_data, people_data):
        """Test person with multiple devices - any device triggers home."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        # Sebastian has iPhone and Watch
        clients = [
            {"mac": "82:9c:1a:5e:d0:28", "hostname": "Watch"}  # Only watch online
        ]
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        sebastian = next(p for p in presence if p["id"] == "sebastian")
        assert sebastian["is_home"] is True

    async def test_person_multiple_devices_all_online(self, hass, devices_data, people_data):
        """Test person with all their devices online."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        # Sebastian has both iPhone and Watch online
        clients = [
            {"mac": "38:7f:8b:da:18:20", "hostname": "iPhone-SKHL"},
            {"mac": "82:9c:1a:5e:d0:28", "hostname": "Watch"}
        ]
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        sebastian = next(p for p in presence if p["id"] == "sebastian")
        assert sebastian["is_home"] is True
        assert sebastian["devices_online"] == 2

    async def test_person_untracked_device_ignored(self, hass, devices_data, people_data):
        """Test that devices with track: false don't trigger presence."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        # iphone-legacy has track: false
        clients = [
            {"mac": "02:a2:54:a8:e1:98", "hostname": "iPhone"}
        ]
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        # No person should be home based on untracked device
        assert all(not p.get("is_home", False) for p in presence)

    async def test_presence_state_entity_update(self, hass, mock_config_entry):
        """Test that HA person entity state is updated correctly."""
        from custom_components.unifi_people_pointer import async_setup_entry
        
        mock_config_entry.add_to_hass(hass)
        
        with patch('custom_components.unifi_people_pointer.coordinator.UniFiCoordinator._fetch_clients', 
                   return_value=[{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}]):
            await async_setup_entry(hass, mock_config_entry)
            await hass.async_block_till_done()
            
            # Check person.janine state
            state = hass.states.get("person.janine")
            assert state is not None
            assert state.state == "home"

    async def test_presence_transition_home_to_away(self, hass, devices_data, people_data):
        """Test presence transition from home to away."""
        from custom_components.unifi_people_pointer.presence import PresenceTracker
        
        tracker = PresenceTracker(hass, devices_data["devices"], people_data["people"])
        
        # Initially home
        clients_home = [{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}]
        tracker.update(clients_home)
        assert tracker.get_state("person.janine") == "home"
        
        # Now away
        clients_away = []
        tracker.update(clients_away)
        assert tracker.get_state("person.janine") == "not_home"

    async def test_presence_transition_away_to_home(self, hass, devices_data, people_data):
        """Test presence transition from away to home."""
        from custom_components.unifi_people_pointer.presence import PresenceTracker
        
        tracker = PresenceTracker(hass, devices_data["devices"], people_data["people"])
        
        # Initially away
        clients_away = []
        tracker.update(clients_away)
        assert tracker.get_state("person.janine") == "not_home"
        
        # Now home
        clients_home = [{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}]
        tracker.update(clients_home)
        assert tracker.get_state("person.janine") == "home"

    async def test_presence_with_hostname_match_only(self, hass, devices_data, people_data):
        """Test presence detection via hostname when MAC is randomized."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        # Randomized MAC but known hostname
        clients = [
            {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "iPhone-JD"}
        ]
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        janine = next(p for p in presence if p["id"] == "janine")
        assert janine["is_home"] is True

    async def test_presence_multiple_people_home(self, hass, devices_data, people_data):
        """Test multiple people home simultaneously."""
        from custom_components.unifi_people_pointer.presence import determine_presence
        
        clients = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"},     # Janine
            {"mac": "38:7f:8b:da:18:20", "hostname": "iPhone-SKHL"}    # Sebastian
        ]
        
        presence = determine_presence(people_data["people"], devices_data["devices"], clients)
        
        janine = next(p for p in presence if p["id"] == "janine")
        sebastian = next(p for p in presence if p["id"] == "sebastian")
        
        assert janine["is_home"] is True
        assert sebastian["is_home"] is True

    async def test_presence_attributes(self, hass, mock_config_entry):
        """Test presence entity has correct attributes."""
        from custom_components.unifi_people_pointer import async_setup_entry
        
        mock_config_entry.add_to_hass(hass)
        
        with patch('custom_components.unifi_people_pointer.coordinator.UniFiCoordinator._fetch_clients',
                   return_value=[{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD", "signal": -45}]):
            await async_setup_entry(hass, mock_config_entry)
            await hass.async_block_till_done()
            
            state = hass.states.get("person.janine")
            assert state is not None
            assert "mac" in state.attributes
            assert "last_seen" in state.attributes or "last_updated" in state.attributes

    async def test_presence_history_tracking(self, hass, devices_data, people_data):
        """Test tracking presence history."""
        from custom_components.unifi_people_pointer.presence import PresenceTracker
        
        tracker = PresenceTracker(hass, devices_data["devices"], people_data["people"], track_history=True)
        
        # Simulate state changes
        tracker.update([{"mac": "1c:3c:78:b8:ae:b5"}])  # Home
        await asyncio.sleep(0.1)
        tracker.update([])  # Away
        await asyncio.sleep(0.1)
        tracker.update([{"mac": "1c:3c:78:b8:ae:b5"}])  # Home again
        
        history = tracker.get_history("person.janine", hours=1)
        assert len(history) >= 2  # At least 2 state changes


@pytest.mark.integration
class TestPresenceConfidenceScore:
    """Test presence confidence scoring."""

    async def test_confidence_high_recent_seen(self, hass):
        """Test high confidence when device recently seen."""
        from custom_components.unifi_people_pointer.presence import calculate_confidence
        
        now = datetime.now()
        recent_seen = int((now - timedelta(seconds=5)).timestamp())
        
        confidence = calculate_confidence(
            last_seen=recent_seen,
            signal_strength=-40,
            is_private_mac=False
        )
        
        assert confidence >= 0.9

    async def test_confidence_low_old_seen(self, hass):
        """Test low confidence when device seen long ago."""
        from custom_components.unifi_people_pointer.presence import calculate_confidence
        
        now = datetime.now()
        old_seen = int((now - timedelta(minutes=5)).timestamp())
        
        confidence = calculate_confidence(
            last_seen=old_seen,
            signal_strength=-40,
            is_private_mac=False
        )
        
        assert confidence < 0.5

    async def test_confidence_medium_private_mac(self, hass):
        """Test reduced confidence for private MACs."""
        from custom_components.unifi_people_pointer.presence import calculate_confidence
        
        now = datetime.now()
        recent_seen = int((now - timedelta(seconds=5)).timestamp())
        
        confidence = calculate_confidence(
            last_seen=recent_seen,
            signal_strength=-40,
            is_private_mac=True
        )
        
        # Should be lower than non-private MAC
        confidence_regular = calculate_confidence(
            last_seen=recent_seen,
            signal_strength=-40,
            is_private_mac=False
        )
        
        assert confidence < confidence_regular

    async def test_confidence_low_poor_signal(self, hass):
        """Test reduced confidence for poor signal."""
        from custom_components.unifi_people_pointer.presence import calculate_confidence
        
        now = datetime.now()
        recent_seen = int((now - timedelta(seconds=5)).timestamp())
        
        confidence = calculate_confidence(
            last_seen=recent_seen,
            signal_strength=-85,  # Very poor
            is_private_mac=False
        )
        
        # Should be lower than good signal
        confidence_good = calculate_confidence(
            last_seen=recent_seen,
            signal_strength=-40,
            is_private_mac=False
        )
        
        assert confidence < confidence_good
