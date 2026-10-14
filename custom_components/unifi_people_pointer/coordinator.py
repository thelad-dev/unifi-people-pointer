"""UniFi People Pointer data coordinator."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_parser import (
    deduplicate_clients,
    filter_wireless_only,
    normalize_mac,
    parse_clients,
)
from .const import (
    CONF_VERIFY_SSL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DEVICES_FILE,
    DOMAIN,
    EVENT_DEVICE_CONNECTED,
    EVENT_PERSON_ARRIVED,
    EVENT_PERSON_LEFT,
    EVENT_UNKNOWN_DEVICE,
    MANUFACTURERS_FILE,
    PEOPLE_FILE,
    STATE_AWAY,
    STATE_HOME,
    STORAGE_DIR,
)
from .data_loader import DataLoader, load_devices, load_people
from .device_matcher import (
    match_device,
    match_device_partial,
    normalize_hostname_match,
)
from .presence import _online_device_ids, determine_presence, person_owns_device

_LOGGER = logging.getLogger(__name__)


def _host_for_url(host: str) -> str:
    """Return host as an HTTP URL authority, bracketing IPv6 literals."""
    if ":" in host and not host.startswith("["):
        # crude IPv6 detect without importing ipaddress again
        if host.count(":") >= 2 and not host.replace(":", "").replace(".", "").isalnum():
            return f"[{host}]"
        # still try: if looks like ipv6
        try:
            import ipaddress

            if ipaddress.ip_address(host).version == 6:
                return f"[{host}]"
        except ValueError:
            pass
    return host


class UniFiPeoplePointerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch UniFi clients and compute person presence."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.config_entry = config_entry
        scan = int(
            config_entry.options.get("scan_interval", DEFAULT_POLL_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan),
        )
        storage = Path(hass.config.path(STORAGE_DIR))
        storage.mkdir(parents=True, exist_ok=True)
        self.storage_path = storage
        self._loader = DataLoader(
            manufacturers_path=storage / MANUFACTURERS_FILE,
            devices_path=storage / DEVICES_FILE,
            people_path=storage / PEOPLE_FILE,
        )
        self._clients_by_mac: dict[str, dict[str, Any]] = {}
        self._all_clients: list[dict[str, Any]] = []
        self._online_device_ids_cache: set[str] = set()
        self._devices_by_id: dict[str, dict[str, Any]] = {}
        self._device_by_configured_mac: dict[str, dict[str, Any]] = {}
        self._device_event_macs: dict[str, str] = {}
        self._presence_by_person: dict[str, dict[str, Any]] = {}
        self._site_id: str | None = None
        self._site_key: str = "default"
        self._prev_online_device_ids: set[str] = set()
        self._prev_unknown_macs: set[str] = set()
        self._prev_device_owners: dict[str, str | None] = {}
        self._events_primed: bool = False
        self._config_lock = asyncio.Lock()
        self.last_exception = ""

    @property
    def people(self) -> list[dict[str, Any]]:
        """Configured people."""
        return list(self._loader.get_people().get("people") or [])

    @property
    def devices(self) -> list[dict[str, Any]]:
        """Configured devices."""
        return list(self._loader.get_devices().get("devices") or [])

    def reload_config_files(self) -> None:
        """Reload people/devices JSON from disk."""
        self._loader.reload()

    def _rebuild_presence_state(
        self,
        all_clients: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Recompute presence indexes from config + client snapshot."""
        wireless = filter_wireless_only(all_clients)
        self._all_clients = all_clients
        self._clients_by_mac = {
            c["mac"]: c for c in all_clients if c.get("mac")
        }
        devices = self.devices
        self._devices_by_id = {
            d["id"]: d for d in devices if isinstance(d, dict) and d.get("id")
        }
        self._device_by_configured_mac = {
            normalize_mac(str(d.get("mac") or "")): d
            for d in devices
            if isinstance(d, dict) and d.get("mac")
        }

        presence_rows = determine_presence(self.people, devices, all_clients)
        previous = self._presence_by_person
        self._presence_by_person = {row["id"]: row for row in presence_rows}
        now_online_ids = _online_device_ids(devices, all_clients)
        self._online_device_ids_cache = now_online_ids

        unknown = []
        known_macs = set(self._device_by_configured_mac)
        for client in wireless:
            matched = match_device(client, devices) or match_device_partial(
                client, devices
            )
            if matched is None and client["mac"] not in known_macs:
                unknown.append(client)
        now_unknown_macs = {c["mac"] for c in unknown if c.get("mac")}

        # First live MAC of a continuous online session (stable across private MAC rotation).
        for device_id in now_online_ids:
            key = str(device_id)
            if key in self._device_event_macs:
                continue
            mac = self._mac_for_device_id(key)
            if mac:
                self._device_event_macs[key] = mac

        now_device_owners: dict[str, str | None] = {}
        online_device_meta: dict[str, tuple[str, dict[str, Any], dict[str, Any] | None]] = {}
        for device_id in now_online_ids:
            key = str(device_id)
            device = self._devices_by_id.get(device_id) or {}
            client = self._live_client_for_device(device)
            mac = self._device_event_macs.get(key, "")
            if not mac:
                if client and client.get("mac"):
                    mac = str(client["mac"])
                else:
                    mac = normalize_mac(str(device.get("mac") or ""))
                if not mac:
                    mac = key
                self._device_event_macs[key] = mac
            person_id = self._person_id_for_device(key, mac)
            now_device_owners[key] = person_id
            online_device_meta[key] = (mac, device, client)

        event_manager = self.hass.data.get(DOMAIN, {}).get("event_manager")
        # After the first baseline, always process transitions/cancels whenever
        # the baseline advances (including config-only rebuilds).
        if event_manager and self._events_primed:
            for person_id in list(previous.keys()):
                if person_id in self._presence_by_person:
                    continue
                prev_row = previous.get(person_id) or {}
                event_manager.cancel_person_event(person_id, EVENT_PERSON_ARRIVED)
                event_manager.cancel_person_event(person_id, EVENT_PERSON_LEFT)
                if not prev_row.get("is_home"):
                    continue
                device_mac = ""
                source_ids = prev_row.get("online_device_ids") or []
                if source_ids:
                    device_id = str(source_ids[0])
                    device_mac = self._device_event_macs.get(
                        device_id
                    ) or self._mac_for_device_id(device_id)
                event_manager.fire_person_left(
                    person=person_id, device=device_mac
                )

            for person_id, row in self._presence_by_person.items():
                was = previous.get(person_id, {}).get("is_home")
                now_home = bool(row.get("is_home"))
                if was is None:
                    if not now_home:
                        continue
                elif was == now_home:
                    continue
                device_mac = ""
                online_ids = row.get("online_device_ids") or []
                source_ids = online_ids or (
                    previous.get(person_id, {}).get("online_device_ids") or []
                )
                if source_ids:
                    device_id = str(source_ids[0])
                    device_mac = self._device_event_macs.get(
                        device_id
                    ) or self._mac_for_device_id(device_id)
                    if device_mac and device_id not in self._device_event_macs:
                        self._device_event_macs[device_id] = device_mac
                if now_home:
                    event_manager.fire_person_arrived(
                        person=person_id, device=device_mac
                    )
                else:
                    event_manager.fire_person_left(
                        person=person_id, device=device_mac
                    )

            for device_id in now_online_ids:
                key = str(device_id)
                mac, device, client = online_device_meta[key]
                person_id = now_device_owners.get(key)
                became_online = device_id not in self._prev_online_device_ids
                owner_changed = (
                    not became_online
                    and key in self._prev_device_owners
                    and self._prev_device_owners.get(key) != person_id
                )
                if not became_online and not owner_changed:
                    continue
                if owner_changed:
                    event_manager.cancel_device_event(mac, EVENT_DEVICE_CONNECTED)
                signal = None
                if client is not None:
                    signal = client.get("signal")
                    if signal is None:
                        signal = client.get("signal_strength")
                event_manager.fire_device_connected(
                    mac=mac,
                    person=person_id,
                    device_type=device.get("type"),
                    ap_name=(client or {}).get("ap_mac"),
                    signal_strength=signal if isinstance(signal, int) else None,
                )

            for device_id in self._prev_online_device_ids - now_online_ids:
                key = str(device_id)
                mac = self._device_event_macs.pop(key, None)
                if not mac:
                    device = self._devices_by_id.get(device_id) or {}
                    mac = normalize_mac(str(device.get("mac") or "")) or key
                event_manager.cancel_device_event(mac, EVENT_DEVICE_CONNECTED)

            unknown_by_mac = {c["mac"]: c for c in unknown if c.get("mac")}
            for mac in now_unknown_macs - self._prev_unknown_macs:
                client = unknown_by_mac.get(mac) or {}
                signal = client.get("signal")
                if signal is None:
                    signal = client.get("signal_strength")
                event_manager.fire_unknown_device(
                    mac=mac,
                    ip=client.get("ip"),
                    hostname=client.get("hostname") or None,
                    ap_name=client.get("ap_mac"),
                    signal_strength=signal if isinstance(signal, int) else None,
                )

            for mac in self._prev_unknown_macs - now_unknown_macs:
                event_manager.cancel_device_event(mac, EVENT_UNKNOWN_DEVICE)

        self._prev_device_owners = now_device_owners
        self._prev_online_device_ids = now_online_ids
        self._prev_unknown_macs = now_unknown_macs
        self._events_primed = True

        guests = [c for c in wireless if c.get("is_guest")]
        return {
            "clients": all_clients,
            "wireless": wireless,
            "presence": presence_rows,
            "unknown_clients": unknown,
            "guest_clients": guests,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch clients from UniFi and compute presence."""
        fetch_error: Exception | None = None
        try:
            raw_clients = await self._fetch_clients()
        except Exception as err:  # noqa: BLE001
            fetch_error = err
            self.last_exception = str(err)
            raw_clients = None

        auth_failed = False
        async with self._config_lock:
            await self.hass.async_add_executor_job(self._loader.reload)
            if raw_clients is not None:
                all_clients = deduplicate_clients(parse_clients(raw_clients))
                data = self._rebuild_presence_state(all_clients)
            elif self._all_clients or self._clients_by_mac or self._presence_by_person:
                data = self._rebuild_presence_state(list(self._all_clients))
                auth_failed = isinstance(fetch_error, PermissionError)
            else:
                raise UpdateFailed(
                    f"UniFi client fetch failed: {fetch_error}"
                ) from fetch_error

        await self.async_sync_tracker_entities()
        if auth_failed:
            raise UpdateFailed(
                f"UniFi authentication failed: {fetch_error}"
            ) from fetch_error
        return data

    async def _fetch_clients(self) -> list[dict[str, Any]]:
        """Fetch clients from UniFi API."""
        host = str(self.config_entry.data[CONF_HOST])
        token = str(self.config_entry.data[CONF_TOKEN])
        verify_ssl = bool(
            self.config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        )
        ssl_param: bool | object = verify_ssl if verify_ssl else False
        base = f"https://{_host_for_url(host)}"
        headers = {"Accept": "application/json", "X-API-KEY": token}
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            if not self._site_id:
                site_id, site_key = await self._resolve_site(
                    session, base, headers, ssl_param
                )
                self._site_id = site_id
                self._site_key = site_key
            site_id = self._site_id

            # Prefer classic live station list (richer fields).
            classic_url = (
                f"{base}/proxy/network/api/s/{self._site_key}/stat/sta"
            )
            try:
                async with session.get(
                    classic_url, headers=headers, ssl=ssl_param
                ) as response:
                    if response.status in (401, 403):
                        raise PermissionError("Invalid API token")
                    if response.status < 400:
                        payload = await response.json(content_type=None)
                        if isinstance(payload, dict):
                            meta_rc = str(
                                (payload.get("meta") or {}).get("rc") or ""
                            ).lower()
                            if meta_rc == "error":
                                _LOGGER.debug(
                                    "Classic sta meta.rc=error (%s); trying integration API",
                                    (payload.get("meta") or {}).get("msg"),
                                )
                            elif isinstance(payload.get("data"), list):
                                # Empty list with ok/absent rc is all-offline.
                                return payload["data"]
                        elif isinstance(payload, list):
                            return payload
            except PermissionError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as err:
                _LOGGER.debug("Classic sta endpoint failed: %s", err)

            # Integration API fallback.
            integ_url = (
                f"{base}/proxy/network/integration/v1/sites/{site_id}/clients"
                "?limit=500"
            )
            async with session.get(
                integ_url, headers=headers, ssl=ssl_param
            ) as response:
                if response.status in (401, 403):
                    raise PermissionError("Invalid API token")
                if response.status >= 400:
                    raise ConnectionError(
                        f"UniFi clients API returned HTTP {response.status}"
                    )
                payload = await response.json(content_type=None)
                if isinstance(payload, dict) and isinstance(payload.get("data"), list):
                    return payload["data"]
                if isinstance(payload, list):
                    return payload
                raise ConnectionError(
                    "UniFi clients API returned no client list"
                )

    async def _resolve_site(
        self,
        session: aiohttp.ClientSession,
        base: str,
        headers: dict[str, str],
        ssl_param: bool | object,
    ) -> tuple[str, str]:
        """Resolve UniFi site UUID and classic site key."""
        url = f"{base}/proxy/network/integration/v1/sites"
        async with session.get(url, headers=headers, ssl=ssl_param) as response:
            if response.status in (401, 403):
                raise PermissionError("Invalid API token")
            if response.status >= 400:
                raise ConnectionError(f"UniFi sites API returned HTTP {response.status}")
            payload = await response.json(content_type=None)
        if isinstance(payload, dict):
            for site in payload.get("data") or []:
                if isinstance(site, dict) and site.get("id"):
                    site_id = str(site["id"])
                    site_key = (
                        site.get("internalReference")
                        or site.get("name")
                        or "default"
                    )
                    return site_id, str(site_key)
        raise ConnectionError("No UniFi site id found")

    def _live_client_for_device(
        self, device: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Return the live UniFi client matching a configured device."""
        if not device:
            return None
        alone = [device]
        for client in self._all_clients:
            if match_device(client, alone) or match_device_partial(client, alone):
                return client
        return None

    def _mac_for_device_id(self, device_id: str) -> str:
        """Resolve a device id to a live or configured MAC."""
        device = self._devices_by_id.get(device_id)
        if not device:
            return ""
        client = self._live_client_for_device(device)
        if client and client.get("mac"):
            return str(client["mac"])
        return normalize_mac(str(device.get("mac") or ""))

    def _person_id_for_device(
        self, device_id: str, session_mac: str = ""
    ) -> str | None:
        """Return the person id that exclusively owns a configured device."""
        device = self._devices_by_id.get(device_id) or {}
        configured_mac = normalize_mac(str(device.get("mac") or ""))
        mac = configured_mac or normalize_mac(session_mac)
        for person in self.people:
            if person_owns_device(
                person,
                device_id=str(device_id),
                device_mac=mac,
                devices=self.devices,
            ):
                pid = person.get("id")
                return str(pid) if pid is not None else None
        return None

    def is_device_online(self, mac: str) -> bool:
        """Return True if a still-configured device MAC is online."""
        mac_n = normalize_mac(mac)
        device = self._device_by_configured_mac.get(mac_n)
        if not device:
            return False
        if mac_n in self._clients_by_mac:
            return True
        device_id = device.get("id")
        return bool(device_id and device_id in self._online_device_ids_cache)

    is_device_connected = is_device_online

    def async_get_client_by_mac(self, mac: str) -> dict[str, Any] | None:
        """Return live client for a configured MAC (direct or hostname match)."""
        mac_n = normalize_mac(mac)
        direct = self._clients_by_mac.get(mac_n)
        if direct is not None:
            return direct
        device = self._device_by_configured_mac.get(mac_n)
        return self._live_client_for_device(device)

    def get_device_signal(self, mac: str) -> int | None:
        """Return signal strength in dBm for an online device MAC."""
        client = self.async_get_client_by_mac(mac)
        if not client:
            return None
        signal = client.get("signal")
        if signal is None:
            signal = client.get("signal_strength")
        if signal is None:
            return None
        try:
            return int(signal)
        except (TypeError, ValueError):
            return None

    def get_person_state(self, person_id: str) -> str:
        """Return home/away for a person id."""
        row = self._presence_by_person.get(person_id)
        if not row:
            return STATE_AWAY
        return STATE_HOME if row.get("is_home") else STATE_AWAY

    def get_person_presence(self, person_id: str) -> dict[str, Any] | None:
        """Return presence row for person."""
        return self._presence_by_person.get(person_id)

    def get_person_zone(self, person_id: str) -> str | None:
        """Return zone hint if available."""
        row = self._presence_by_person.get(person_id)
        if not row or not row.get("is_home"):
            return None
        for device_id in row.get("online_device_ids") or []:
            device = self._devices_by_id.get(str(device_id))
            client = self._live_client_for_device(device)
            if client and client.get("ap_mac"):
                return str(client.get("ap_mac"))
        return None

    def get_person_devices(self, person_id: str) -> dict[str, Any]:
        """Return primary/secondary device info for a person."""
        row = self._presence_by_person.get(person_id) or {}
        online = set(row.get("online_device_ids") or [])
        enriched: list[dict[str, Any]] = []
        for device in row.get("devices") or []:
            client = self._live_client_for_device(device)
            enriched.append(
                {
                    **device,
                    "connected": device.get("id") in online or bool(client),
                    "client": client,
                }
            )
        primary = enriched[0] if enriched else None
        secondary = enriched[1:] if len(enriched) > 1 else []
        return {"primary": primary, "secondary": secondary}

    def get_unknown_clients(self) -> list[dict[str, Any]]:
        """Unknown wireless clients from last update."""
        if not self.data:
            return []
        return list(self.data.get("unknown_clients") or [])

    def get_guest_clients(self) -> list[dict[str, Any]]:
        """Guest wireless clients from last update."""
        if not self.data:
            return []
        return list(self.data.get("guest_clients") or [])


    def _read_devices_file(self) -> dict[str, Any]:
        """Read devices.json from disk without touching the shared loader."""
        path = self.storage_path / DEVICES_FILE
        if path.exists():
            return load_devices(path)
        return {"version": 1, "devices": []}

    def _read_people_file(self) -> dict[str, Any]:
        """Read people.json from disk without touching the shared loader."""
        path = self.storage_path / PEOPLE_FILE
        if path.exists():
            return load_people(path)
        return {"version": 1, "people": []}

    async def assign_device(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None = None,
    ) -> None:
        """Assign a device MAC to a person (persisted in JSON)."""
        async with self._config_lock:
            await self.hass.async_add_executor_job(
                self._assign_device_sync, mac, person, device_type, device_name
            )
            self._loader.reload()
            data = self._rebuild_presence_state(list(self._all_clients))
            self.async_set_updated_data(data)
        await self.async_sync_tracker_entities()
        await self.async_request_refresh()

    def _hostname_match_seeds(self, mac_n: str) -> list[str]:
        """Build hostname_match seeds from the live UniFi client hostname only."""
        seeds: list[str] = []
        client = self.async_get_client_by_mac(mac_n) or self._clients_by_mac.get(mac_n)
        if client:
            host = str(client.get("hostname") or "").strip()
            if host:
                seeds.append(host)
        return seeds

    @staticmethod
    def _merge_hostname_match(
        existing: Any, seeds: list[str]
    ) -> list[str]:
        """Merge seeds into hostname_match without wiping existing tokens."""
        current = normalize_hostname_match(existing)
        if not seeds:
            return current
        if not current:
            return list(seeds)
        merged = list(current)
        for seed in seeds:
            if seed not in merged:
                merged.append(seed)
        return merged

    def _assign_device_sync(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None,
    ) -> None:
        mac_n = normalize_mac(mac)
        devices_data = self._read_devices_file()
        devices = list(devices_data.get("devices") or [])
        existing = next(
            (d for d in devices if normalize_mac(str(d.get("mac") or "")) == mac_n),
            None,
        )
        device_id = existing["id"] if existing else f"dev-{mac_n.replace(':', '')}"
        seeds = self._hostname_match_seeds(mac_n)
        if existing is None:
            devices.append(
                {
                    "id": device_id,
                    "name": device_name or mac_n,
                    "type": "other",
                    "mac": mac_n,
                    "hostname_match": list(seeds),
                    "track": True,
                    "notes": f"assigned as {device_type}",
                }
            )
        else:
            existing["track"] = True
            if device_name:
                existing["name"] = device_name
            existing["hostname_match"] = self._merge_hostname_match(
                existing.get("hostname_match"), seeds
            )
        devices_data["devices"] = devices
        self._write_json(self.storage_path / DEVICES_FILE, devices_data)

        people_data = self._read_people_file()
        people = list(people_data.get("people") or [])
        target = next((p for p in people if p.get("id") == person), None)
        if target is None:
            target = {
                "id": person,
                "name": person,
                "device_ids": [],
            }
            people.append(target)
            people_data["people"] = people
        # Exclusive ownership: detach from every other person first.
        for other in people:
            if other is target:
                continue
            other_ids = list(other.get("device_ids") or [])
            if device_id in other_ids:
                other["device_ids"] = [i for i in other_ids if i != device_id]
            self._detach_mac_from_person(other, mac_n)
        devices_by_mac = {
            normalize_mac(str(d.get("mac") or "")): d
            for d in devices
            if isinstance(d, dict) and d.get("mac")
        }
        ids = [i for i in (target.get("device_ids") or []) if i != device_id]
        legacy_macs: list[str] = []
        if target.get("primary_device"):
            legacy_macs.append(str(target.get("primary_device")))
        for m in target.get("secondary_devices") or []:
            if m:
                legacy_macs.append(str(m))
        for owned_mac in legacy_macs:
            owned_n = normalize_mac(owned_mac)
            if not owned_n or owned_n == mac_n:
                continue
            owned_dev = devices_by_mac.get(owned_n)
            owned_id = owned_dev.get("id") if owned_dev else None
            if owned_id and owned_id not in ids and owned_id != device_id:
                ids.append(owned_id)
        if device_type == "primary":
            ids.insert(0, device_id)
        else:
            ids.append(device_id)
        target["device_ids"] = ids
        target["primary_device"] = None
        target["secondary_devices"] = []
        self._write_json(self.storage_path / PEOPLE_FILE, people_data)

    async def track_device(
        self, mac: str, name: str, device_type: str = "other"
    ) -> None:
        """Start tracking a device."""
        async with self._config_lock:
            await self.hass.async_add_executor_job(
                self._track_device_sync, mac, name, device_type
            )
            self._loader.reload()
            data = self._rebuild_presence_state(list(self._all_clients))
            self.async_set_updated_data(data)
        await self.async_sync_tracker_entities()
        await self.async_request_refresh()

    def _track_device_sync(self, mac: str, name: str, device_type: str) -> None:
        mac_n = normalize_mac(mac)
        devices_data = self._read_devices_file()
        devices = list(devices_data.get("devices") or [])
        seeds = self._hostname_match_seeds(mac_n)
        for device in devices:
            if normalize_mac(str(device.get("mac") or "")) == mac_n:
                device["track"] = True
                device["name"] = name
                device["type"] = device_type
                device["hostname_match"] = self._merge_hostname_match(
                    device.get("hostname_match"), seeds
                )
                self._write_json(self.storage_path / DEVICES_FILE, devices_data)
                return
        devices.append(
            {
                "id": f"dev-{mac_n.replace(':', '')}",
                "name": name,
                "type": device_type,
                "mac": mac_n,
                "hostname_match": list(seeds),
                "track": True,
            }
        )
        devices_data["devices"] = devices
        self._write_json(self.storage_path / DEVICES_FILE, devices_data)

    async def remove_device(self, mac: str) -> None:
        """Stop tracking / remove a device."""
        async with self._config_lock:
            await self.hass.async_add_executor_job(self._remove_device_sync, mac)
            self._loader.reload()
            data = self._rebuild_presence_state(list(self._all_clients))
            self.async_set_updated_data(data)
        await self.async_sync_tracker_entities()
        await self.async_request_refresh()

    @staticmethod
    def _detach_mac_from_person(person: dict[str, Any], mac_n: str) -> None:
        """Remove a MAC from primary/secondary ownership and keep person valid."""
        primary_n = normalize_mac(str(person.get("primary_device") or ""))
        secondaries = person.get("secondary_devices")
        if not isinstance(secondaries, list):
            secondaries = []
        kept_secondaries = [
            m for m in secondaries if normalize_mac(str(m or "")) != mac_n
        ]
        if primary_n == mac_n:
            if kept_secondaries:
                person["primary_device"] = kept_secondaries[0]
                person["secondary_devices"] = kept_secondaries[1:]
            else:
                person["primary_device"] = None
                if "secondary_devices" in person or secondaries:
                    person["secondary_devices"] = []
            return
        if "secondary_devices" in person or kept_secondaries != list(secondaries):
            person["secondary_devices"] = kept_secondaries

    def _remove_device_sync(self, mac: str) -> None:
        mac_n = normalize_mac(mac)
        devices_data = self._read_devices_file()
        devices = list(devices_data.get("devices") or [])
        removed_ids = []
        kept = []
        for device in devices:
            if normalize_mac(str(device.get("mac") or "")) == mac_n:
                removed_ids.append(device.get("id"))
            else:
                kept.append(device)
        devices_data["devices"] = kept
        self._write_json(self.storage_path / DEVICES_FILE, devices_data)

        people_data = self._read_people_file()
        for person in people_data.get("people") or []:
            ids = [i for i in (person.get("device_ids") or []) if i not in removed_ids]
            person["device_ids"] = ids
            self._detach_mac_from_person(person, mac_n)
        self._write_json(self.storage_path / PEOPLE_FILE, people_data)

    async def force_update_person(self, person: str) -> None:
        """Force a refresh (person filter currently ignored)."""
        _ = person
        await self.async_request_refresh()

    async def claim_unknown_device(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None = None,
    ) -> None:
        """Claim an unknown device for a person."""
        await self.assign_device(mac, person, device_type, device_name)

    def register_tracker_platform(
        self,
        add_entities: Any,
        known_person_ids: set[str],
        known_device_ids: set[str],
    ) -> None:
        """Store device_tracker platform hooks for dynamic entity adds."""
        self._tracker_add_entities = add_entities
        self._known_person_ids = set(known_person_ids)
        self._known_device_ids = set(known_device_ids)

    async def async_sync_tracker_entities(self) -> None:
        """Add tracker entities for newly configured people/devices."""
        add_entities = getattr(self, "_tracker_add_entities", None)
        if add_entities is None:
            return
        from .device_tracker import UniFiDeviceTracker, UniFiPersonTracker

        known_people = getattr(self, "_known_person_ids", set())
        known_devices = getattr(self, "_known_device_ids", set())
        new_entities: list[Any] = []
        for person in self.people:
            person_id = person.get("id")
            if not person_id or person_id in known_people:
                continue
            new_entities.append(
                UniFiPersonTracker(
                    self,
                    {
                        "id": person_id,
                        "name": person.get("name") or person_id,
                        "ha_person": person.get("ha_person"),
                    },
                )
            )
            known_people.add(person_id)
        for device in self.devices:
            device_id = device.get("id")
            mac = normalize_mac(str(device.get("mac") or ""))
            if not device_id or device_id in known_devices:
                continue
            if not mac and not device_id:
                continue
            person_id = None
            for person in self.people:
                if person_owns_device(
                    person,
                    device_id=device_id,
                    device_mac=mac,
                    devices=self.devices,
                ):
                    person_id = person.get("id")
                    break
            new_entities.append(
                UniFiDeviceTracker(
                    self,
                    {
                        "id": device_id,
                        "mac": mac,
                        "name": device.get("name") or device_id or mac,
                        "type": device.get("type"),
                        "person": person_id,
                    },
                )
            )
            known_devices.add(device_id)
        self._known_person_ids = known_people
        self._known_device_ids = known_devices
        if new_entities:
            add_entities(new_entities)

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        import json
        import os

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)


# Backward-compatible alias used by older tests/docs.
UniFiCoordinator = UniFiPeoplePointerCoordinator
