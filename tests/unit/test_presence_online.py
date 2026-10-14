"""Behavioral tests for client-centric online device matching."""

from __future__ import annotations

import pytest

from custom_components.unifi_people_pointer.presence import (
    _online_device_ids,
    determine_presence,
)

pytestmark = pytest.mark.unit


def test_short_partial_seed_does_not_piggyback_exact_peer() -> None:
    """Live hostname seed 'iPhone' must not mark home via peer iPhone-RB exact."""
    devices = [
        {
            "id": "iphone-sk",
            "name": "Christoph Phone",
            "mac": "aa:bb:cc:dd:ee:10",
            "hostname_match": ["iPhone-RB"],
            "track": True,
        },
        {
            "id": "dev-amy",
            "name": "iPhone",
            "mac": "aa:bb:cc:dd:ee:11",
            "hostname_match": ["iPhone"],
            "track": True,
        },
    ]
    clients = [
        {
            "mac": "aa:bb:cc:dd:ee:10",
            "hostname": "iPhone-RB",
            "is_wired": False,
        }
    ]
    online = _online_device_ids(devices, clients)
    assert online == {"iphone-sk"}

    people = [
        {"id": "christoph", "name": "Christoph", "device_ids": ["iphone-sk"]},
        {"id": "amelie", "name": "Amelie", "device_ids": ["dev-amy"]},
    ]
    presence = {row["id"]: row for row in determine_presence(people, devices, clients)}
    assert presence["christoph"]["is_home"] is True
    assert presence["amelie"]["is_home"] is False


def test_multi_partial_siblings_still_share_when_no_exact() -> None:
    """When nothing exact-matches, overlapping partial tokens can all go online."""
    devices = [
        {
            "id": "phone-a",
            "mac": "aa:bb:cc:dd:ee:01",
            "hostname_match": ["Phone-"],
            "track": True,
        },
        {
            "id": "phone-b",
            "mac": "aa:bb:cc:dd:ee:02",
            "hostname_match": ["Phone-"],
            "track": True,
        },
    ]
    clients = [{"mac": "11:22:33:44:55:66", "hostname": "Phone-Max", "is_wired": False}]
    assert _online_device_ids(devices, clients) == {"phone-a", "phone-b"}


def test_name_exact_does_not_compete_with_hostname_match_peer() -> None:
    """Display name equal to peer hostname_match must not dual-home one client."""
    devices = [
        {
            "id": "iphone-sk",
            "name": "Christoph Phone",
            "mac": "aa:bb:cc:dd:ee:10",
            "hostname_match": ["iPhone-RB"],
            "track": True,
        },
        {
            "id": "dev-amy",
            "name": "iPhone-RB",
            "mac": "aa:bb:cc:dd:ee:11",
            "hostname_match": ["iPhone-AN"],
            "track": True,
        },
    ]
    clients = [{"mac": "99:99:99:99:99:99", "hostname": "iPhone-RB", "is_wired": False}]
    assert _online_device_ids(devices, clients) == {"iphone-sk"}


def test_ambiguous_exact_name_does_not_dual_home() -> None:
    """Two devices with the same display name yield one exclusive exact winner."""
    devices = [
        {
            "id": "amy-phone",
            "name": "iPhone",
            "mac": "aa:bb:cc:dd:ee:01",
            "hostname_match": [],
            "track": True,
        },
        {
            "id": "tom-phone",
            "name": "iPhone",
            "mac": "aa:bb:cc:dd:ee:02",
            "hostname_match": [],
            "track": True,
        },
    ]
    clients = [{"mac": "11:22:33:44:55:66", "hostname": "iPhone", "is_wired": False}]
    online = _online_device_ids(devices, clients)
    assert online == {"amy-phone"}

    people = [
        {"id": "amelie", "name": "Amelie", "device_ids": ["amy-phone"]},
        {"id": "christoph", "name": "Christoph", "device_ids": ["tom-phone"]},
    ]
    presence = {row["id"]: row for row in determine_presence(people, devices, clients)}
    assert presence["amelie"]["is_home"] is True
    assert presence["christoph"]["is_home"] is False


def test_ambiguous_exact_hostname_match_does_not_dual_home() -> None:
    """Shared exact hostname_match token homes only one stable device."""
    devices = [
        {
            "id": "watch-b",
            "name": "Watch B",
            "mac": "aa:bb:cc:dd:ee:21",
            "hostname_match": ["Watch"],
            "track": True,
        },
        {
            "id": "watch-a",
            "name": "Watch A",
            "mac": "aa:bb:cc:dd:ee:20",
            "hostname_match": ["Watch"],
            "track": True,
        },
    ]
    clients = [{"mac": "11:22:33:44:55:66", "hostname": "Watch", "is_wired": False}]
    assert _online_device_ids(devices, clients) == {"watch-a"}
