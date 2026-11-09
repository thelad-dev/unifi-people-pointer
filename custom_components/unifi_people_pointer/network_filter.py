"""Network filter: limit People Pointer to selected subnets or UniFi networks.

A selection is a list of entries, each either a CIDR (``192.0.2.0/24``,
``2001:db8::/64``) or a UniFi network reference (``network:<id>``). An empty
selection means "no filter": every client is considered.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

NETWORK_PREFIX = "network:"

# Observed client ranges without a UniFi network are grouped by these prefixes.
OBSERVED_PREFIX_V4 = 24
OBSERVED_PREFIX_V6 = 64

KIND_UNIFI = "unifi"
KIND_OBSERVED = "observed"
KIND_CUSTOM = "custom"


@dataclass(frozen=True)
class UniFiNetwork:
    """A network (LAN/VLAN) defined on the UniFi controller."""

    id: str
    name: str
    vlan: int | None
    subnets: tuple[IPNetwork, ...]


def _to_network(value: Any) -> IPNetwork | None:
    """Return the network of an interface notation (``192.0.2.1/24``)."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return ipaddress.ip_interface(text).network
    except ValueError:
        return None


def _to_vlan(value: Any) -> int | None:
    try:
        vlan = int(value)
    except (TypeError, ValueError):
        return None
    return vlan if vlan > 0 else None


def parse_networks(raw_networks: list[dict[str, Any]] | None) -> list[UniFiNetwork]:
    """Parse controller network definitions (classic or integration API)."""
    networks: list[UniFiNetwork] = []
    seen: set[str] = set()
    for row in raw_networks or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("purpose") or "").lower() == "wan":
            continue
        net_id = str(row.get("_id") or row.get("id") or "").strip()
        if not net_id or net_id in seen:
            continue
        subnets: list[IPNetwork] = []
        for key in ("ip_subnet", "ipSubnet", "subnet", "ipv6_subnet", "ipv6Subnet"):
            net = _to_network(row.get(key))
            if net is not None and net not in subnets:
                subnets.append(net)
        ipv4 = row.get("ipv4Configuration")
        if isinstance(ipv4, dict) and ipv4.get("hostIpAddress"):
            net = _to_network(
                f"{ipv4.get('hostIpAddress')}/{ipv4.get('prefixLength', 24)}"
            )
            if net is not None and net not in subnets:
                subnets.append(net)
        vlan = _to_vlan(row.get("vlan") if "vlan" in row else row.get("vlanId"))
        name = str(row.get("name") or "").strip() or net_id
        seen.add(net_id)
        networks.append(UniFiNetwork(net_id, name, vlan, tuple(subnets)))
    return networks


def normalize_entry(value: Any) -> str:
    """Validate one selection entry and return its canonical text.

    Raises:
        ValueError: The entry is neither a CIDR nor ``network:<id>``.
    """
    text = str(value or "").strip()
    if not text:
        raise ValueError("empty network entry")
    if text.lower().startswith(NETWORK_PREFIX):
        net_id = text[len(NETWORK_PREFIX) :].strip()
        if not net_id:
            raise ValueError(f"{text!r} names no UniFi network")
        return f"{NETWORK_PREFIX}{net_id}"
    try:
        return str(ipaddress.ip_network(text, strict=False))
    except ValueError as err:
        raise ValueError(f"{text!r} is not a valid subnet (CIDR)") from err


def normalize_selection(values: Iterable[Any] | None) -> list[str]:
    """Validate and de-duplicate a selection, keeping its order."""
    result: list[str] = []
    for value in values or []:
        entry = normalize_entry(value)
        if entry not in result:
            result.append(entry)
    return result


def _raw(client: dict[str, Any]) -> dict[str, Any]:
    raw = client.get("raw")
    return raw if isinstance(raw, dict) else client


def client_addresses(client: dict[str, Any]) -> list[IPAddress]:
    """All IP addresses a parsed client reports (IPv4 first, then IPv6)."""
    raw = _raw(client)
    candidates: list[Any] = [client.get("ip")]
    if not client.get("ip"):
        candidates.append(raw.get("last_ip"))
    for key in ("ipv6_addresses", "ipv6Addresses", "ipv6_address", "ipv6Address"):
        value = raw.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif value:
            candidates.append(value)
    addresses: list[IPAddress] = []
    for candidate in candidates:
        text = str(candidate or "").strip()
        if not text:
            continue
        try:
            address = ipaddress.ip_address(text.split("%", 1)[0])
        except ValueError:
            continue
        if address not in addresses:
            addresses.append(address)
    return addresses


def client_network_ref(client: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(network id, network name)`` the controller reports for a client."""
    raw = _raw(client)
    net_id = str(raw.get("network_id") or raw.get("networkId") or "").strip()
    name = str(raw.get("network") or raw.get("networkName") or "").strip()
    return net_id or None, name or None


class NetworkFilter:
    """Decide whether a client belongs to the selected networks."""

    def __init__(
        self,
        selection: Iterable[str] | None,
        include_unassigned: bool = True,
        networks: Iterable[UniFiNetwork] | None = None,
    ) -> None:
        """Build the filter from a normalized selection and known networks."""
        self.selection = normalize_selection(selection)
        self.include_unassigned = bool(include_unassigned)
        self._networks = {net.id: net for net in networks or []}
        self._network_ids: set[str] = set()
        self._subnets: list[IPNetwork] = []
        for entry in self.selection:
            if entry.startswith(NETWORK_PREFIX):
                net_id = entry[len(NETWORK_PREFIX) :]
                self._network_ids.add(net_id)
                known = self._networks.get(net_id)
                if known is not None:
                    self._subnets.extend(known.subnets)
            else:
                self._subnets.append(ipaddress.ip_network(entry))

    @property
    def active(self) -> bool:
        """True when a selection limits the clients."""
        return bool(self.selection)

    def _network_id(self, client: dict[str, Any]) -> str | None:
        net_id, name = client_network_ref(client)
        if net_id:
            return net_id
        if name:
            for net in self._networks.values():
                if net.name == name:
                    return net.id
        return None

    def allows(self, client: dict[str, Any]) -> bool:
        """Return True when the client is inside the selected networks."""
        if not self.active:
            return True
        addresses = client_addresses(client)
        for address in addresses:
            if any(address in subnet for subnet in self._subnets):
                return True
        net_id = self._network_id(client)
        if net_id and net_id in self._network_ids:
            return True
        if not addresses and not net_id:
            return self.include_unassigned
        return False

    def apply(self, clients: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return the clients inside the selected networks."""
        return [client for client in clients if self.allows(client)]


def _observed_range(address: IPAddress) -> IPNetwork:
    prefix = OBSERVED_PREFIX_V4 if address.version == 4 else OBSERVED_PREFIX_V6
    return ipaddress.ip_network(f"{address}/{prefix}", strict=False)


def _network_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    kind_order = {KIND_UNIFI: 0, KIND_OBSERVED: 1, KIND_CUSTOM: 2}
    first = row["subnets"][0] if row["subnets"] else ""
    net = ipaddress.ip_network(first) if first else None
    return (
        kind_order.get(row["kind"], 3),
        net.version if net else 9,
        int(net.network_address) if net else 0,
        str(row["name"]).lower(),
    )


def detect_networks(
    clients: Iterable[dict[str, Any]],
    networks: Iterable[UniFiNetwork],
    selection: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Describe the networks clients appear in, with client counts.

    Each client is counted once: in the UniFi network it belongs to (by
    network id or address), otherwise in its observed address range (IPv4
    /24, IPv6 /64). Clients with neither are counted as unassigned. Selected
    entries that no client or network matches are listed as well.
    """
    selected = normalize_selection(selection)
    known = list(networks)
    by_id = {net.id: net for net in known}
    by_name = {net.name: net for net in known}
    rows: dict[str, dict[str, Any]] = {}

    def unifi_row(net_id: str, name: str, vlan: int | None) -> dict[str, Any]:
        key = f"{NETWORK_PREFIX}{net_id}"
        if key not in rows:
            rows[key] = {
                "key": key,
                "kind": KIND_UNIFI,
                "name": name,
                "vlan": vlan,
                "subnets": [],
                "clients": 0,
            }
        return rows[key]

    for net in known:
        row = unifi_row(net.id, net.name, net.vlan)
        row["subnets"] = [str(s) for s in net.subnets]

    client_list = list(clients)
    unassigned = 0
    for client in client_list:
        addresses = client_addresses(client)
        net_id, net_name = client_network_ref(client)
        net = by_id.get(net_id or "") or by_name.get(net_name or "")
        if net is None and addresses:
            net = next(
                (n for n in known if any(addresses[0] in s for s in n.subnets)), None
            )
        if net is not None:
            unifi_row(net.id, net.name, net.vlan)["clients"] += 1
            continue
        if net_id:
            row = unifi_row(net_id, net_name or net_id, None)
            row["clients"] += 1
            if addresses:
                hint = str(_observed_range(addresses[0]))
                if hint not in row["subnets"]:
                    row["subnets"].append(hint)
            continue
        if addresses:
            cidr = str(_observed_range(addresses[0]))
            row = rows.setdefault(
                cidr,
                {
                    "key": cidr,
                    "kind": KIND_OBSERVED,
                    "name": cidr,
                    "vlan": None,
                    "subnets": [cidr],
                    "clients": 0,
                },
            )
            row["clients"] += 1
            continue
        unassigned += 1

    for entry in selected:
        if entry in rows:
            continue
        if entry.startswith(NETWORK_PREFIX):
            net_id = entry[len(NETWORK_PREFIX) :]
            unifi_row(net_id, net_id, None)
            continue
        subnet = ipaddress.ip_network(entry)
        count = sum(
            1
            for client in client_list
            if any(address in subnet for address in client_addresses(client))
        )
        rows[entry] = {
            "key": entry,
            "kind": KIND_CUSTOM,
            "name": entry,
            "vlan": None,
            "subnets": [entry],
            "clients": count,
        }

    ordered = sorted(rows.values(), key=_network_sort_key)
    for row in ordered:
        row["selected"] = row["key"] in selected
    return {"networks": ordered, "unassigned_clients": unassigned}
