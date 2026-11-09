"""AP usage history: buckets, averages, data estimate, retention, storage."""

from __future__ import annotations

import json

import pytest

from custom_components.unifi_people_pointer.api_parser import parse_clients
from custom_components.unifi_people_pointer.usage import (
    ApUsageHistory,
    client_rate,
    usage_sample,
)

pytestmark = pytest.mark.unit

AP1 = "24:5a:4c:aa:bb:cc"
AP2 = "24:5a:4c:aa:bb:dd"
# Start of an hour, so 5-minute and hourly buckets line up predictably.
T0 = 1_800_000_000 - 1_800_000_000 % 3600


@pytest.fixture
async def history(hass):
    """Empty history with a 60 s poll interval."""
    result = ApUsageHistory(hass, "entry", 60)
    await result.async_load()
    return result


def test_client_rate_and_sample():
    """Rates come from the classic list; wired clients and missing APs do not count."""
    clients = parse_clients(
        [
            {
                "mac": "aa:aa:aa:00:00:01",
                "ap_mac": AP1,
                "tx_bytes-r": 100,
                "rx_bytes-r": 50,
            },
            {"mac": "aa:aa:aa:00:00:02", "ap_mac": AP1, "tx_bytes-r": "x"},
            {"mac": "aa:aa:aa:00:00:03", "ap_mac": AP2},
            {"mac": "aa:aa:aa:00:00:04", "is_wired": True, "ap_mac": AP2},
            {"mac": "aa:aa:aa:00:00:05", "is_wired": False},
            {
                "macAddress": "aa:aa:aa:00:00:06",
                "type": "WIRELESS",
                "uplinkDeviceId": "DEV-1",
            },
        ]
    )
    assert client_rate(clients[0]) == 150.0
    assert client_rate(clients[1]) is None
    ids = {"dev-1": AP2}
    counts, rates, has_rates = usage_sample(
        clients, lambda key: ids.get(key.lower(), key)
    )
    assert counts == {AP1: 2, AP2: 2}
    assert rates == {AP1: 150.0}
    assert has_rates is True
    assert usage_sample(clients[2:3], str)[2] is False


async def test_average_peak_and_bytes(history):
    """Average divides by all polls, so idle polls lower the average."""
    history.record(T0, {AP1: 4, AP2: 1}, {AP1: 1000.0}, True)
    history.record(T0 + 60, {AP1: 2}, {AP1: 500.0}, True)
    history.record(T0 + 120, {}, {}, True)
    summary = history.summary("1h", now=T0 + 150)
    assert summary["samples"] == 3
    assert summary["since"] == T0
    assert summary["aps"][AP1] == {"clients": 2.0, "clients_max": 4, "bytes": 90000}
    assert summary["aps"][AP2] == {"clients": 0.33, "clients_max": 1, "bytes": 0}
    assert history.current_counts == {}
    assert history.has_bytes is True


async def test_gap_is_capped(history):
    """After downtime the last rate is not stretched over hours."""
    history.record(T0, {AP1: 1}, {AP1: 10.0}, True)
    history.record(T0 + 7200, {AP1: 1}, {AP1: 10.0}, True)
    summary = history.summary("24h", now=T0 + 7200)
    # 60 s for the first sample, at most 3 x 60 s for the second.
    assert summary["aps"][AP1]["bytes"] == 600 + 1800


async def test_without_rates_bytes_are_unknown(history):
    """Integration API clients have no rates: bytes stay None."""
    history.record(T0, {AP1: 3}, {}, False)
    assert history.summary("1h", now=T0)["aps"][AP1]["bytes"] is None
    assert history.current_rates == {}


async def test_periods_and_retention(history):
    """1 h and 24 h read 5-minute buckets, 7 d hourly ones; old buckets go."""
    history.record(T0, {AP1: 9}, {}, False)
    history.record(T0 + 2 * 3600, {AP1: 1}, {}, False)
    now = T0 + 2 * 3600 + 30
    assert history.summary("1h", now=now)["aps"][AP1]["clients"] == 1.0
    assert history.summary("24h", now=now)["aps"][AP1]["clients"] == 5.0
    assert history.summary("7d", now=now)["aps"][AP1]["clients_max"] == 9

    history.record(T0 + 25 * 3600, {AP2: 2}, {}, False)
    later = T0 + 25 * 3600
    # The 9-client bucket is older than a day; only the 1-client one is left.
    assert history.summary("24h", now=later)["aps"][AP1]["clients_max"] == 1
    assert history.summary("7d", now=later)["aps"][AP1]["clients_max"] == 9
    history.record(T0 + 8 * 24 * 3600, {AP2: 1}, {}, False)
    assert AP1 not in history.summary("7d", now=T0 + 8 * 24 * 3600)["aps"]
    data = history._data
    assert len(data["fine"]) == 1
    assert len(data["coarse"]) <= 7 * 24 + 1


async def test_bucket_counts_stay_bounded(history):
    """A week of 60 s polls keeps at most 289 fine and 169 coarse buckets."""
    for step in range(0, 8 * 24 * 3600, 600):
        history.record(T0 + step, {AP1: 1}, {}, False)
    assert len(history._data["fine"]) <= 289
    assert len(history._data["coarse"]) <= 169


async def test_store_round_trip_without_identifiers(hass, hass_storage):
    """Saved data holds only AP MACs and numbers; it loads back."""
    history = ApUsageHistory(hass, "entry", 60)
    await history.async_load()
    history.record(T0, {AP1: 2}, {AP1: 5.0}, True)
    await history.async_flush()
    stored = hass_storage["unifi_people_pointer.ap_usage.entry"]["data"]
    text = json.dumps(stored)
    assert "aa:aa:aa" not in text
    assert set(stored["fine"][str(T0)]["aps"]) == {AP1}

    again = ApUsageHistory(hass, "entry", 60)
    again._prune = lambda now: None  # keep the fixed test time
    await again.async_load()
    assert again.has_bytes is True
    assert again.summary("1h", now=T0)["aps"][AP1]["clients"] == 2.0


async def test_broken_store_starts_empty(hass, hass_storage):
    """Invalid buckets are dropped on load."""
    hass_storage["unifi_people_pointer.ap_usage.entry"] = {
        "version": 1,
        "key": "unifi_people_pointer.ap_usage.entry",
        "data": {
            "fine": {"1": "junk", "2": {"n": 1, "aps": {AP1: [1, 1]}}},
            "coarse": [],
            "has_bytes": "yes",
        },
    }
    history = ApUsageHistory(hass, "entry", 60)
    await history.async_load()
    assert history._data["fine"] == {}
    assert history.has_bytes is False
