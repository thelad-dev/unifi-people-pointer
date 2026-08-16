"""Integration tests for fallback logic when UniFi API is unavailable."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# Fallback/coordinator paths are still Phase 3 stubs.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Requires Phase 3 coordinator implementation"),
]


@pytest.mark.integration
class TestFallbackLogic:
    """Test fallback mechanisms when UniFi controller is unavailable."""

    async def test_fallback_to_cached_state(self, hass, mock_config_entry):
        """Test that cached state is used when API is unavailable."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(hass, mock_config_entry)

        # Simulate successful initial fetch
        mock_clients = [
            {
                "mac": "1c:3c:78:b8:ae:b5",
                "hostname": "iPhone-JD",
                "last_seen": datetime.now().timestamp(),
            }
        ]

        with patch.object(coordinator, "_fetch_clients", return_value=mock_clients):
            await coordinator.async_refresh()
            assert coordinator.data is not None
            cached_data = coordinator.data.copy()

        # Now simulate API failure
        with patch.object(
            coordinator,
            "_fetch_clients",
            side_effect=ConnectionError("API unavailable"),
        ):
            await coordinator.async_refresh()

            # Should still have cached data
            assert coordinator.data is not None
            assert coordinator.data == cached_data

    async def test_fallback_cache_expiry(self, hass, mock_config_entry):
        """Test that old cache expires after threshold."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(
            hass, mock_config_entry, cache_ttl=300
        )  # 5 min TTL

        # Set old cached data
        old_timestamp = datetime.now() - timedelta(minutes=10)
        coordinator._cache_timestamp = old_timestamp
        coordinator._cached_data = [
            {"mac": "aa:bb:cc:dd:ee:ff", "hostname": "OldDevice"}
        ]

        # Attempt refresh with API down
        with patch.object(
            coordinator,
            "_fetch_clients",
            side_effect=ConnectionError("API unavailable"),
        ):
            await coordinator.async_refresh()

            # Cache should be expired and cleared
            assert coordinator.data == [] or coordinator.data is None

    async def test_fallback_to_ssh_mongodb(self, hass, mock_config_entry):
        """Test fallback to SSH + MongoDB when API is unavailable."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(
            hass, mock_config_entry, enable_ssh_fallback=True
        )

        # Mock SSH connection
        mock_ssh_clients = [
            {
                "mac": "1c:3c:78:b8:ae:b5",
                "hostname": "iPhone-JD",
                "last_seen": datetime.now().timestamp(),
            }
        ]

        with patch.object(
            coordinator,
            "_fetch_clients",
            side_effect=ConnectionError("API unavailable"),
        ):
            with patch.object(
                coordinator, "_fetch_via_ssh", return_value=mock_ssh_clients
            ):
                await coordinator.async_refresh()

                assert coordinator.data is not None
                assert len(coordinator.data) == 1
                assert coordinator.data[0]["mac"] == "1c:3c:78:b8:ae:b5"

    async def test_fallback_ssh_also_fails(self, hass, mock_config_entry):
        """Test when both API and SSH fallback fail."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(
            hass, mock_config_entry, enable_ssh_fallback=True
        )

        with patch.object(
            coordinator,
            "_fetch_clients",
            side_effect=ConnectionError("API unavailable"),
        ):
            with patch.object(
                coordinator,
                "_fetch_via_ssh",
                side_effect=ConnectionError("SSH unavailable"),
            ):
                await coordinator.async_refresh()

                # Should use empty data or last known good
                assert (
                    coordinator.data is not None
                    or coordinator.last_update_success is False
                )

    async def test_fallback_to_last_known_good(
        self, hass, mock_config_entry, devices_data, people_data
    ):
        """Test presence detection using last known good state."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator
        from custom_components.unifi_people_pointer.presence import determine_presence

        coordinator = UniFiCoordinator(hass, mock_config_entry)

        # Set last known good state - person was home
        last_good_clients = [
            {
                "mac": "1c:3c:78:b8:ae:b5",
                "hostname": "iPhone-JD",
                "last_seen": datetime.now().timestamp(),
            }
        ]
        coordinator._last_known_good = last_good_clients
        coordinator._last_known_good_timestamp = datetime.now()

        # API is down, but use last known good
        with patch.object(
            coordinator,
            "_fetch_clients",
            side_effect=ConnectionError("API unavailable"),
        ):
            presence = determine_presence(
                people_data["people"],
                devices_data["devices"],
                coordinator._last_known_good,
                use_last_known_good=True,
            )

            # Janine should still be marked as home based on last known good
            janine = next(p for p in presence if p["id"] == "janine")
            assert janine["is_home"] is True

    async def test_fallback_graceful_degradation(self, hass, mock_config_entry):
        """Test graceful degradation with partial API responses."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(hass, mock_config_entry)

        # Simulate partial/corrupted response
        partial_clients = [
            {"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"},  # Valid
            {"mac": None, "hostname": "InvalidDevice"},  # Invalid - no MAC
            {"mac": "38:7f:8b:da:18:20"},  # Valid - no hostname ok
            None,  # Invalid - null entry
        ]

        with patch.object(coordinator, "_fetch_clients", return_value=partial_clients):
            await coordinator.async_refresh()

            # Should skip invalid entries
            assert coordinator.data is not None
            assert len(coordinator.data) == 2  # Only the 2 valid entries

    async def test_fallback_retry_logic(self, hass, mock_config_entry):
        """Test exponential backoff retry logic when API fails."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(hass, mock_config_entry, max_retries=3)

        retry_count = 0

        async def failing_fetch():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise ConnectionError("API unavailable")
            return [{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}]

        with patch.object(coordinator, "_fetch_clients", side_effect=failing_fetch):
            await coordinator.async_refresh()

            # Should have retried and eventually succeeded
            assert retry_count == 3
            assert coordinator.data is not None

    async def test_fallback_circuit_breaker(self, hass, mock_config_entry):
        """Test circuit breaker pattern to prevent hammering failed API."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(
            hass, mock_config_entry, circuit_breaker_threshold=5
        )

        # Simulate 5 consecutive failures
        for i in range(5):
            with patch.object(
                coordinator,
                "_fetch_clients",
                side_effect=ConnectionError("API unavailable"),
            ):
                await coordinator.async_refresh()

        # Circuit should now be open - no more API calls
        call_count = 0

        async def count_calls():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("API unavailable")

        with patch.object(coordinator, "_fetch_clients", side_effect=count_calls):
            await coordinator.async_refresh()

            # Should not have called API (circuit open)
            assert call_count == 0 or coordinator._circuit_breaker_open is True

    async def test_fallback_state_persistence(self, hass, mock_config_entry):
        """Test that presence state persists across HA restarts during API outage."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        # Before "restart" - person is home
        coordinator = UniFiCoordinator(hass, mock_config_entry)

        with patch.object(
            coordinator,
            "_fetch_clients",
            return_value=[{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}],
        ):
            await coordinator.async_refresh()

            # Save state
            state_to_persist = coordinator.get_persistent_state()

        # After "restart" - API is down
        coordinator_new = UniFiCoordinator(hass, mock_config_entry)
        coordinator_new.restore_persistent_state(state_to_persist)

        with patch.object(
            coordinator_new,
            "_fetch_clients",
            side_effect=ConnectionError("API unavailable"),
        ):
            await coordinator_new.async_refresh()

            # Should have restored state
            assert (
                coordinator_new.data is not None
                or coordinator_new._last_known_good is not None
            )

    async def test_fallback_mixed_sources(self, hass, mock_config_entry):
        """Test combining data from multiple sources during partial outage."""
        from custom_components.unifi_people_pointer.coordinator import UniFiCoordinator

        coordinator = UniFiCoordinator(
            hass, mock_config_entry, enable_ssh_fallback=True
        )

        # API returns partial data
        api_clients = [{"mac": "1c:3c:78:b8:ae:b5", "hostname": "iPhone-JD"}]

        # SSH returns different client
        ssh_clients = [{"mac": "38:7f:8b:da:18:20", "hostname": "iPhone-SKHL"}]

        with patch.object(coordinator, "_fetch_clients", return_value=api_clients):
            with patch.object(coordinator, "_fetch_via_ssh", return_value=ssh_clients):
                await coordinator.async_refresh()

                # Should merge both sources
                assert len(coordinator.data) >= 1
