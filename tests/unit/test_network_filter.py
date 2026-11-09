"""Network filter: selection parsing, client matching and network detection."""

from __future__ import annotations

import ipaddress

import pytest

from custom_components.unifi_people_pointer.api_parser import parse_clients
from custom_components.unifi_people_pointer.network_filter import (
    NetworkFilter,
    UniFiNetwork,
    client_addresses,
    detect_networks,
    normalize_entry,
    normalize_selection,
    parse_networks,
)

pytestmark = pytest.mark.unit

MAIN_NET = "192.0.2.0/24"
# Documentation ranges (RFC 5737 / RFC 3849) stand in for a foreign network.
FOREIGN_NET = "198.51.100.0/24"
V6_NET = "2001:db8:1::/64"


def _client(mac: str, **raw) -> dict:
    """One parsed client built from a classic stat/sta row."""
    return parse_clients([{"mac": mac, **raw}])[0]


MAIN = UniFiNetwork("net-main", "Main", None, (ipaddress.ip_network(MAIN_NET),))


class TestSelection:
    """Validation and canonical form of selection entries."""

    def test_cidr_is_canonical(self):
        assert normalize_entry("192.0.2.17/24") == MAIN_NET
        assert normalize_entry(" 2001:DB8:1::1/64 ") == V6_NET

    def test_bare_address_is_a_host_route(self):
        assert normalize_entry("192.0.2.5") == "192.0.2.5/32"

    def test_network_reference(self):
        assert normalize_entry("network:abc123") == "network:abc123"

    @pytest.mark.parametrize(
        "value", ["", "network:", "192.0.2.0/33", "300.1.1.0/24", "lan"]
    )
    def test_invalid_entries_raise(self, value):
        with pytest.raises(ValueError):
            normalize_entry(value)

    def test_selection_dedupes_in_order(self):
        assert normalize_selection(["192.0.2.9/24", FOREIGN_NET, "192.0.2.0/24"]) == [
            MAIN_NET,
            FOREIGN_NET,
        ]


class TestNetworkFilter:
    """Which clients a selection lets through."""

    def test_no_selection_allows_everything(self):
        flt = NetworkFilter([])
        assert not flt.active
        assert flt.allows(_client("00:00:5e:00:53:01", ip="198.51.100.20"))

    def test_foreign_client_is_dropped(self):
        """A client from another network disappears with a main-net filter."""
        flt = NetworkFilter([MAIN_NET])
        home = _client("00:00:5e:00:53:01", ip="192.0.2.20")
        foreign = _client("00:00:5e:00:53:51", ip="198.51.100.20")
        assert flt.apply([home, foreign]) == [home]

    @pytest.mark.parametrize(
        ("ip", "inside"),
        [
            ("192.0.2.0", True),  # network address
            ("192.0.2.255", True),  # broadcast address
            ("192.0.1.255", False),  # just below
            ("192.0.3.0", False),  # just above
        ],
    )
    def test_cidr_edges(self, ip, inside):
        flt = NetworkFilter([MAIN_NET])
        assert flt.allows(_client("00:00:5e:00:53:02", ip=ip)) is inside

    def test_narrow_cidr_edges(self):
        flt = NetworkFilter(["192.0.2.64/26"])
        assert flt.allows(_client("00:00:5e:00:53:03", ip="192.0.2.64"))
        assert flt.allows(_client("00:00:5e:00:53:03", ip="192.0.2.127"))
        assert not flt.allows(_client("00:00:5e:00:53:03", ip="192.0.2.63"))
        assert not flt.allows(_client("00:00:5e:00:53:03", ip="192.0.2.128"))

    def test_ipv6_selection(self):
        flt = NetworkFilter([V6_NET])
        v6_only = _client("00:00:5e:00:53:04", ip="2001:db8:1::42")
        dual = _client(
            "00:00:5e:00:53:05",
            ip="198.51.100.5",
            ipv6_addresses=["fe80::1", "2001:db8:1::5"],
        )
        other = _client("00:00:5e:00:53:06", ip="2001:db8:51::1")
        assert flt.allows(v6_only)
        assert flt.allows(dual)
        assert not flt.allows(other)

    def test_ipv4_client_never_matches_ipv6_subnet(self):
        flt = NetworkFilter([V6_NET])
        assert not flt.allows(_client("00:00:5e:00:53:07", ip="192.0.2.7"))

    def test_unifi_network_by_subnet_and_by_id(self):
        flt = NetworkFilter(["network:net-main"], networks=[MAIN])
        by_ip = _client("00:00:5e:00:53:08", ip="192.0.2.8")
        no_ip = _client("00:00:5e:00:53:09", network_id="net-main")
        foreign = _client(
            "00:00:5e:00:53:0a", ip="198.51.100.10", network_id="net-guest"
        )
        assert flt.allows(by_ip)
        assert flt.allows(no_ip)
        assert not flt.allows(foreign)

    def test_client_without_ip_matches_network_by_name(self):
        flt = NetworkFilter(["network:net-main"], networks=[MAIN])
        assert flt.allows(_client("00:00:5e:00:53:0b", network="Main"))

    def test_client_without_ip_in_other_network_is_dropped(self):
        flt = NetworkFilter([MAIN_NET], include_unassigned=True)
        assert not flt.allows(_client("00:00:5e:00:53:0c", network_id="net-guest"))

    @pytest.mark.parametrize("include", [True, False])
    def test_client_without_ip_and_network(self, include):
        flt = NetworkFilter([MAIN_NET], include_unassigned=include)
        assert flt.allows(_client("00:00:5e:00:53:0d")) is include

    def test_last_ip_counts_when_ip_is_missing(self):
        client = _client("00:00:5e:00:53:0e", last_ip="192.0.2.14")
        assert [str(a) for a in client_addresses(client)] == ["192.0.2.14"]
        assert NetworkFilter([MAIN_NET], include_unassigned=False).allows(client)

    def test_garbage_ip_is_ignored(self):
        client = _client("00:00:5e:00:53:0f", ip="not-an-ip")
        assert client_addresses(client) == []


class TestParseNetworks:
    """Controller network definitions."""

    def test_classic_networkconf(self):
        rows = [
            {
                "_id": "net-main",
                "name": "Main",
                "purpose": "corporate",
                "ip_subnet": "192.0.2.1/24",
                "ipv6_subnet": "2001:db8:1::1/64",
            },
            {
                "_id": "net-iot",
                "name": "IoT",
                "purpose": "corporate",
                "vlan": "20",
                "ip_subnet": "198.51.100.1/24",
            },
            {"_id": "wan1", "name": "Internet", "purpose": "wan"},
            {"name": "no id"},
            "garbage",
        ]
        networks = parse_networks(rows)
        assert [n.id for n in networks] == ["net-main", "net-iot"]
        assert [str(s) for s in networks[0].subnets] == [MAIN_NET, V6_NET]
        assert networks[1].vlan == 20
        assert networks[0].vlan is None

    def test_integration_api_rows(self):
        rows = [
            {
                "id": "a1",
                "name": "Main",
                "vlanId": 1,
                "ipv4Configuration": {
                    "hostIpAddress": "192.0.2.1",
                    "prefixLength": 24,
                },
            }
        ]
        (network,) = parse_networks(rows)
        assert [str(s) for s in network.subnets] == [MAIN_NET]
        assert network.vlan == 1


class TestDetectNetworks:
    """Networks shown for selection, with client counts."""

    def test_counts_per_network_observed_range_and_unassigned(self):
        clients = [
            _client("00:00:5e:00:53:10", ip="192.0.2.10"),
            _client("00:00:5e:00:53:11", network_id="net-main"),
            _client("00:00:5e:00:53:12", ip="198.51.100.12"),
            _client("00:00:5e:00:53:13", ip="198.51.100.13"),
            _client("00:00:5e:00:53:14", ip="2001:db8:51::14"),
            _client("00:00:5e:00:53:15"),
        ]
        result = detect_networks(clients, [MAIN], [FOREIGN_NET])
        rows = {row["key"]: row for row in result["networks"]}
        assert rows["network:net-main"]["clients"] == 2
        assert rows["network:net-main"]["subnets"] == [MAIN_NET]
        assert rows[FOREIGN_NET]["kind"] == "observed"
        assert rows[FOREIGN_NET]["clients"] == 2
        assert rows[FOREIGN_NET]["selected"] is True
        assert rows["2001:db8:51::/64"]["clients"] == 1
        assert result["unassigned_clients"] == 1
        # UniFi networks first, then observed ranges (IPv4 before IPv6).
        assert [row["key"] for row in result["networks"]] == [
            "network:net-main",
            FOREIGN_NET,
            "2001:db8:51::/64",
        ]

    def test_network_known_only_from_clients(self):
        clients = [
            _client(
                "00:00:5e:00:53:20",
                ip="198.51.100.20",
                network_id="net-guest",
                network="Guest",
            )
        ]
        (row,) = detect_networks(clients, [])["networks"]
        assert row["key"] == "network:net-guest"
        assert row["name"] == "Guest"
        assert row["subnets"] == [FOREIGN_NET]
        assert row["clients"] == 1

    def test_selected_entries_without_clients_are_listed(self):
        result = detect_networks([], [], ["203.0.113.0/24", "network:gone"])
        rows = {row["key"]: row for row in result["networks"]}
        assert rows["203.0.113.0/24"]["kind"] == "custom"
        assert rows["203.0.113.0/24"]["clients"] == 0
        assert rows["network:gone"]["selected"] is True
