"""Unit tests for loading and validating configuration data files."""
import pytest
import json
from pathlib import Path


@pytest.mark.unit
class TestDataLoading:
    """Test loading of manufacturers.json, devices.json, and people.json."""

    def test_load_manufacturers_valid(self, mock_data_files):
        """Test loading valid manufacturers.json."""
        from custom_components.unifi_people_pointer.data_loader import load_manufacturers
        
        manufacturers = load_manufacturers(mock_data_files["manufacturers"])
        
        assert manufacturers is not None
        assert "manufacturers" in manufacturers
        assert len(manufacturers["manufacturers"]) > 0

    def test_load_devices_valid(self, mock_data_files):
        """Test loading valid devices.json."""
        from custom_components.unifi_people_pointer.data_loader import load_devices
        
        devices = load_devices(mock_data_files["devices"])
        
        assert devices is not None
        assert "devices" in devices
        assert len(devices["devices"]) > 0

    def test_load_people_valid(self, mock_data_files):
        """Test loading valid people.json."""
        from custom_components.unifi_people_pointer.data_loader import load_people
        
        people = load_people(mock_data_files["people"])
        
        assert people is not None
        assert "people" in people
        assert len(people["people"]) > 0

    def test_load_manufacturers_missing_file(self, tmp_path):
        """Test handling of missing manufacturers.json."""
        from custom_components.unifi_people_pointer.data_loader import load_manufacturers
        
        missing_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError):
            load_manufacturers(missing_file)

    def test_load_devices_malformed_json(self, tmp_path):
        """Test handling of malformed devices.json."""
        from custom_components.unifi_people_pointer.data_loader import load_devices
        
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text("{invalid json")
        
        with pytest.raises(json.JSONDecodeError):
            load_devices(malformed_file)

    def test_validate_device_schema(self):
        """Test validation of device schema."""
        from custom_components.unifi_people_pointer.data_loader import validate_device
        
        valid_device = {
            "id": "test-device",
            "mac": "aa:bb:cc:dd:ee:ff",
            "hostname_match": ["TestDevice"],
            "track": True
        }
        
        assert validate_device(valid_device) is True

    def test_validate_device_missing_required_field(self):
        """Test validation fails for missing required fields."""
        from custom_components.unifi_people_pointer.data_loader import validate_device
        
        invalid_device = {
            "id": "test-device",
            # Missing "mac"
            "hostname_match": ["TestDevice"],
            "track": True
        }
        
        assert validate_device(invalid_device) is False

    def test_validate_device_invalid_mac_format(self):
        """Test validation fails for invalid MAC format."""
        from custom_components.unifi_people_pointer.data_loader import validate_device
        
        invalid_device = {
            "id": "test-device",
            "mac": "invalid-mac-address",
            "hostname_match": ["TestDevice"],
            "track": True
        }
        
        assert validate_device(invalid_device) is False

    def test_validate_people_schema(self):
        """Test validation of people schema."""
        from custom_components.unifi_people_pointer.data_loader import validate_person
        
        valid_person = {
            "id": "test-person",
            "ha_person": "person.test",
            "device_ids": ["device1", "device2"]
        }
        
        assert validate_person(valid_person) is True

    def test_validate_people_invalid_ha_person_format(self):
        """Test validation fails for invalid HA person entity format."""
        from custom_components.unifi_people_pointer.data_loader import validate_person
        
        invalid_person = {
            "id": "test-person",
            "ha_person": "invalid_entity_format",  # Should be "person.xxx"
            "device_ids": ["device1"]
        }
        
        assert validate_person(invalid_person) is False

    def test_validate_people_device_ids_exist(self, devices_data):
        """Test validation that device_ids reference existing devices."""
        from custom_components.unifi_people_pointer.data_loader import validate_person_devices
        
        person = {
            "id": "test-person",
            "ha_person": "person.test",
            "device_ids": ["iphone-jd", "iphone-skhl"]
        }
        
        assert validate_person_devices(person, devices_data["devices"]) is True

    def test_validate_people_device_ids_missing(self, devices_data):
        """Test validation fails when device_ids reference non-existent devices."""
        from custom_components.unifi_people_pointer.data_loader import validate_person_devices
        
        person = {
            "id": "test-person",
            "ha_person": "person.test",
            "device_ids": ["nonexistent-device"]
        }
        
        assert validate_person_devices(person, devices_data["devices"]) is False

    def test_validate_manufacturers_oui_format(self):
        """Test validation of OUI prefix format."""
        from custom_components.unifi_people_pointer.data_loader import validate_oui_prefix
        
        assert validate_oui_prefix("aa:bb:cc") is True
        assert validate_oui_prefix("AA:BB:CC") is True
        assert validate_oui_prefix("invalid") is False
        assert validate_oui_prefix("aa:bb") is False  # Too short

    def test_load_data_with_version_check(self, mock_data_files):
        """Test version compatibility checking."""
        from custom_components.unifi_people_pointer.data_loader import load_with_version_check
        
        data = load_with_version_check(mock_data_files["devices"], expected_version=1)
        
        assert data is not None
        assert data["version"] == 1

    def test_load_data_version_mismatch(self, tmp_path):
        """Test handling of version mismatch."""
        from custom_components.unifi_people_pointer.data_loader import load_with_version_check
        
        wrong_version_file = tmp_path / "wrong_version.json"
        wrong_version_file.write_text(json.dumps({"version": 2, "devices": []}))
        
        with pytest.raises(ValueError, match="version"):
            load_with_version_check(wrong_version_file, expected_version=1)

    def test_reload_data_files(self, mock_data_files):
        """Test reloading data files without restart."""
        from custom_components.unifi_people_pointer.data_loader import DataLoader
        
        loader = DataLoader(
            manufacturers_path=mock_data_files["manufacturers"],
            devices_path=mock_data_files["devices"],
            people_path=mock_data_files["people"]
        )
        
        initial_devices = loader.get_devices()
        
        # Modify devices file
        devices_data = json.loads(mock_data_files["devices"].read_text())
        devices_data["devices"].append({
            "id": "new-device",
            "mac": "ff:ff:ff:ff:ff:ff",
            "hostname_match": ["NewDevice"],
            "track": True
        })
        mock_data_files["devices"].write_text(json.dumps(devices_data))
        
        # Reload
        loader.reload()
        updated_devices = loader.get_devices()
        
        assert len(updated_devices["devices"]) > len(initial_devices["devices"])
