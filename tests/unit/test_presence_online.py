"""Behavioral tests for client-centric online device matching."""

from __future__ import annotations

import pytest

from custom_components.unifi_people_pointer.presence import (
    _online_device_ids,
    determine_presence,
)

pytestmark = pytest.mark.unit


def test_short_partial_seed_does_not_piggyback_exact_peer() -> None:
    """Live hostname seed 'iPhone' must not mark home via peer iPhone-SK exact."""
    devices = [
        {
            "id": "iphone-sk",
            "name": "Sebastian Phone",
            "mac": "aa:bb:cc:dd:ee:10",
            "hostname_match": ["iPhone-SK"],
            "track": True,
        },
        {
            "id": "dev-jan",
            "name": "iPhone",
            "mac": "aa:bb:cc:dd:ee:11",
            "hostname_match": ["iPhone"],
            "track": True,
        },
    ]
    clients = [
        {
            "mac": "aa:bb:cc:dd:ee:10",
            "hostname": "iPhone-SK",
            "is_wired": False,
        }
    ]
    online = _online_device_ids(devices, clients)
    assert online == {"iphone-sk"}

    people = [
        {"id": "sebastian", "name": "Sebastian", "device_ids": ["iphone-sk"]},
        {"id": "janine", "name": "Janine", "device_ids": ["dev-jan"]},
    ]
    presence = {row["id"]: row for row in determine_presence(people, devices, clients)}
    assert presence["sebastian"]["is_home"] is True
    assert presence["janine"]["is_home"] is False


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
            "name": "Sebastian Phone",
            "mac": "aa:bb:cc:dd:ee:10",
            "hostname_match": ["iPhone-SK"],
            "track": True,
        },
        {
            "id": "dev-jan",
            "name": "iPhone-SK",
            "mac": "aa:bb:cc:dd:ee:11",
            "hostname_match": ["iPhone-JD"],
            "track": True,
        },
    ]
    clients = [{"mac": "99:99:99:99:99:99", "hostname": "iPhone-SK", "is_wired": False}]
    assert _online_device_ids(devices, clients) == {"iphone-sk"}


def test_ambiguous_exact_name_does_not_dual_home() -> None:
    """Two devices with the same display name yield one exclusive exact winner."""
    devices = [
        {
            "id": "jan-phone",
            "name": "iPhone",
            "mac": "aa:bb:cc:dd:ee:01",
            "hostname_match": [],
            "track": True,
        },
        {
            "id": "seb-phone",
            "name": "iPhone",
            "mac": "aa:bb:cc:dd:ee:02",
            "hostname_match": [],
            "track": True,
        },
    ]
    clients = [{"mac": "11:22:33:44:55:66", "hostname": "iPhone", "is_wired": False}]
    online = _online_device_ids(devices, clients)
    assert online == {"jan-phone"}

    people = [
        {"id": "janine", "name": "Janine", "device_ids": ["jan-phone"]},
        {"id": "sebastian", "name": "Sebastian", "device_ids": ["seb-phone"]},
    ]
    presence = {row["id"]: row for row in determine_presence(people, devices, clients)}
    assert presence["janine"]["is_home"] is True
    assert presence["sebastian"]["is_home"] is False


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
