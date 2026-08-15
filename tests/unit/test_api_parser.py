"""Unit tests for UniFi API response parsing."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock


@pytest.mark.unit
class TestAPIParser:
    """Test parsing of UniFi API responses."""

    def test_parse_valid_client_response(self, mock_unifi_api_clients_online):
        """Test parsing a valid client response from UniFi API."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients
        
        clients = parse_clients(mock_unifi_api_clients_online)
        
        assert len(clients) == 3
        assert clients[0]["mac"] == "1c:3c:78:b8:ae:b5"
        assert clients[0]["hostname"] == "iPhone-JD"
        assert clients[1]["mac"] == "38:7f:8b:da:18:20"
        assert clients[2]["mac"] == "82:9c:1a:5e:d0:28"

    def test_parse_empty_response(self, mock_unifi_api_empty):
        """Test parsing an empty API response."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients
        
        clients = parse_clients(mock_unifi_api_empty)
        
        assert clients == []

    def test_parse_malformed_response(self):
        """Test parsing a malformed API response."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients
        
        malformed_data = [
            {"mac": "aa:bb:cc:dd:ee:ff"},  # Missing required fields
            {"hostname": "SomeDevice"},     # Missing MAC
            None,                            # Null entry
        ]
        
        clients = parse_clients(malformed_data)
        
        # Should skip invalid entries and only return valid ones
        assert len(clients) <= 1  # At most the first one if MAC is present

    def test_parse_client_with_missing_hostname(self):
        """Test parsing client with null/missing hostname."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients
        
        data = [
            {
                "mac": "aa:bb:cc:dd:ee:ff",
                "hostname": None,
                "ip": "192.168.88.100",
                "last_seen": 1734567890,
                "is_wired": False,
                "signal": -45
            }
        ]
        
        clients = parse_clients(data)
        
        assert len(clients) == 1
        assert clients[0]["mac"] == "aa:bb:cc:dd:ee:ff"
        assert clients[0]["hostname"] is None or clients[0]["hostname"] == ""

    def test_parse_client_normalize_mac_format(self):
        """Test that MAC addresses are normalized to lowercase with colons."""
        from custom_components.unifi_people_pointer.api_parser import normalize_mac
        
        assert normalize_mac("AA:BB:CC:DD:EE:FF") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("aa-bb-cc-dd-ee-ff") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("aabbccddeeff") == "aa:bb:cc:dd:ee:ff"
        assert normalize_mac("AABBCC.DDEEFF") == "aa:bb:cc:dd:ee:ff"

    def test_parse_client_extract_oui_prefix(self):
        """Test extraction of OUI prefix from MAC address."""
        from custom_components.unifi_people_pointer.api_parser import extract_oui
        
        assert extract_oui("1c:3c:78:b8:ae:b5") == "1c:3c:78"
        assert extract_oui("38:7f:8b:da:18:20") == "38:7f:8b"
        assert extract_oui("aa:bb:cc:dd:ee:ff") == "aa:bb:cc"

    def test_parse_client_with_wired_connection(self):
        """Test parsing client connected via wired (should be filtered)."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients, filter_wireless_only
        
        data = [
            {
                "mac": "aa:bb:cc:dd:ee:ff",
                "hostname": "WiredDevice",
                "ip": "192.168.88.100",
                "last_seen": 1734567890,
                "is_wired": True,
                "signal": None
            },
            {
                "mac": "11:22:33:44:55:66",
                "hostname": "WirelessDevice",
                "ip": "192.168.88.101",
                "last_seen": 1734567890,
                "is_wired": False,
                "signal": -45
            }
        ]
        
        clients = parse_clients(data)
        wireless_clients = filter_wireless_only(clients)
        
        assert len(wireless_clients) == 1
        assert wireless_clients[0]["mac"] == "11:22:33:44:55:66"

    def test_parse_client_last_seen_timestamp(self):
        """Test parsing and validating last_seen timestamps."""
        from custom_components.unifi_people_pointer.api_parser import is_client_online
        
        now = datetime.now()
        recent_timestamp = int((now - timedelta(seconds=30)).timestamp())
        old_timestamp = int((now - timedelta(minutes=10)).timestamp())
        
        # Client seen 30 seconds ago should be online
        assert is_client_online(recent_timestamp, threshold_seconds=300)
        
        # Client seen 10 minutes ago should be offline
        assert not is_client_online(old_timestamp, threshold_seconds=300)

    def test_parse_signal_strength_quality(self):
        """Test categorization of signal strength."""
        from custom_components.unifi_people_pointer.api_parser import categorize_signal
        
        assert categorize_signal(-30) == "excellent"
        assert categorize_signal(-50) == "good"
        assert categorize_signal(-70) == "fair"
        assert categorize_signal(-85) == "poor"

    def test_parse_client_with_unicode_hostname(self):
        """Test parsing client with unicode characters in hostname."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients
        
        data = [
            {
                "mac": "aa:bb:cc:dd:ee:ff",
                "hostname": "Gerät-München-2024",
                "ip": "192.168.88.100",
                "last_seen": 1734567890,
                "is_wired": False,
                "signal": -45
            }
        ]
        
        clients = parse_clients(data)
        
        assert len(clients) == 1
        assert "München" in clients[0]["hostname"]

    def test_parse_api_error_response(self):
        """Test handling of API error responses."""
        from custom_components.unifi_people_pointer.api_parser import parse_api_error
        
        error_response = {
            "error": "unauthorized",
            "error_description": "Invalid API token"
        }
        
        error = parse_api_error(error_response)
        
        assert error["type"] == "unauthorized"
        assert "Invalid API token" in error["message"]

    def test_parse_sites_response(self):
        """Test parsing UniFi sites response."""
        from custom_components.unifi_people_pointer.api_parser import parse_sites
        
        sites_data = [
            {
                "name": "default",
                "desc": "Default",
                "role": "admin"
            },
            {
                "name": "guest",
                "desc": "Guest Network",
                "role": "admin"
            }
        ]
        
        sites = parse_sites(sites_data)
        
        assert len(sites) == 2
        assert sites[0]["name"] == "default"
        assert sites[1]["name"] == "guest"

    def test_parse_duplicate_mac_addresses(self, mock_unifi_api_duplicate_macs):
        """Test parsing response with duplicate MAC addresses."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients, deduplicate_clients
        
        clients = parse_clients(mock_unifi_api_duplicate_macs)
        unique_clients = deduplicate_clients(clients)
        
        # Should keep only the most recent entry
        assert len(unique_clients) == 1
        assert unique_clients[0]["mac"] == "1c:3c:78:b8:ae:b5"
        # Should keep the one with more recent last_seen
        assert unique_clients[0]["last_seen"] == 1734567895

    def test_parse_client_with_channel_info(self):
        """Test parsing client with channel and band information."""
        from custom_components.unifi_people_pointer.api_parser import parse_clients, get_wifi_band
        
        data = [
            {
                "mac": "aa:bb:cc:dd:ee:ff",
                "hostname": "Device2.4GHz",
                "channel": 6,
                "signal": -45
            },
            {
                "mac": "11:22:33:44:55:66",
                "hostname": "Device5GHz",
                "channel": 36,
                "signal": -50
            }
        ]
        
        clients = parse_clients(data)
        
        assert get_wifi_band(clients[0]["channel"]) == "2.4GHz"
        assert get_wifi_band(clients[1]["channel"]) == "5GHz"

    def test_parse_private_mac_address_detection(self):
        """Test detection of private/randomized MAC addresses."""
        from custom_components.unifi_people_pointer.api_parser import is_private_mac
        
        # Private MAC addresses have the locally administered bit set
        assert is_private_mac("02:00:00:00:00:00")  # Bit 2 set in first octet
        assert is_private_mac("06:00:00:00:00:00")
        assert is_private_mac("82:9c:1a:5e:d0:28")  # Apple Watch example
        
        # Regular MACs
        assert not is_private_mac("1c:3c:78:b8:ae:b5")
        assert not is_private_mac("38:7f:8b:da:18:20")
