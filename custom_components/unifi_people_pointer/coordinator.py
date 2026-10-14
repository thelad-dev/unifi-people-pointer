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
    MANUFACTURERS_FILE,
    PEOPLE_FILE,
    STATE_AWAY,
    STATE_HOME,
    STORAGE_DIR,
)
from .data_loader import DataLoader
from .device_matcher import match_device, match_device_partial
from .presence import determine_presence

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
        self._presence_by_person: dict[str, dict[str, Any]] = {}
        self._site_id: str | None = None
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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch clients from UniFi and compute presence."""
        # Pick up people/devices.json edits without a full reload.
        await self.hass.async_add_executor_job(self._loader.reload)

        try:
            raw_clients = await self._fetch_clients()
        except Exception as err:  # noqa: BLE001
            self.last_exception = str(err)
            raise UpdateFailed(f"UniFi client fetch failed: {err}") from err

        clients = deduplicate_clients(parse_clients(raw_clients))
        wireless = filter_wireless_only(clients)
        # Keep wired too for matching, but presence mainly cares about wireless phones.
        all_clients = clients

        self._clients_by_mac = {
            c["mac"]: c for c in all_clients if c.get("mac")
        }

        presence_rows = determine_presence(self.people, self.devices, all_clients)
        previous = self._presence_by_person
        self._presence_by_person = {row["id"]: row for row in presence_rows}

        # Fire debounced events when presence flips.
        event_manager = self.hass.data.get(DOMAIN, {}).get("event_manager")
        if event_manager:
            for person_id, row in self._presence_by_person.items():
                was = previous.get(person_id, {}).get("is_home")
                now_home = row.get("is_home")
                if was is None or was == now_home:
                    continue
                device = ""
                online_ids = row.get("online_device_ids") or []
                if online_ids:
                    device = str(online_ids[0])
                elif previous.get(person_id, {}).get("online_device_ids"):
                    device = str(previous[person_id]["online_device_ids"][0])
                if now_home:
                    event_manager.fire_person_arrived(person=person_id, device=device)
                else:
                    event_manager.fire_person_left(person=person_id, device=device)

        unknown = []
        known_macs = {
            normalize_mac(str(d.get("mac") or "")) for d in self.devices
        }
        for client in wireless:
            matched = match_device(client, self.devices) or match_device_partial(
                client, self.devices
            )
            if matched is None and client["mac"] not in known_macs:
                unknown.append(client)

        guests = [c for c in wireless if c.get("is_guest")]

        return {
            "clients": all_clients,
            "wireless": wireless,
            "presence": presence_rows,
            "unknown_clients": unknown,
            "guest_clients": guests,
        }

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
            site_id = self._site_id or await self._resolve_site_id(
                session, base, headers, ssl_param
            )
            self._site_id = site_id

            # Prefer classic live station list (richer fields).
            classic_url = f"{base}/proxy/network/api/s/default/stat/sta"
            try:
                async with session.get(
                    classic_url, headers=headers, ssl=ssl_param
                ) as response:
                    if response.status in (401, 403):
                        raise PermissionError("Invalid API token")
                    if response.status < 400:
                        payload = await response.json(content_type=None)
                        if isinstance(payload, dict) and isinstance(
                            payload.get("data"), list
                        ):
                            return payload["data"]
                        if isinstance(payload, list):
                            return payload
            except (PermissionError, asyncio.TimeoutError):
                raise
            except aiohttp.ClientError as err:
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
                return []

    async def _resolve_site_id(
        self,
        session: aiohttp.ClientSession,
        base: str,
        headers: dict[str, str],
        ssl_param: bool | object,
    ) -> str:
        """Resolve UniFi site UUID for Integration API paths."""
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
                    return str(site["id"])
        raise ConnectionError("No UniFi site id found")

    def is_device_online(self, mac: str) -> bool:
        """Return True if MAC is present in the latest client list."""
        return normalize_mac(mac) in self._clients_by_mac

    # Alias used by template helpers.
    is_device_connected = is_device_online

    def async_get_client_by_mac(self, mac: str) -> dict[str, Any] | None:
        """Return normalized client dict for MAC if online."""
        return self._clients_by_mac.get(normalize_mac(mac))

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
            for device in self.devices:
                if device.get("id") == device_id:
                    mac = normalize_mac(str(device.get("mac") or ""))
                    client = self._clients_by_mac.get(mac)
                    if client and client.get("ap_mac"):
                        return str(client.get("ap_mac"))
        return None

    def get_person_devices(self, person_id: str) -> list[dict[str, Any]]:
        """Return device info for a person."""
        row = self._presence_by_person.get(person_id) or {}
        online = set(row.get("online_device_ids") or [])
        result = []
        for device in row.get("devices") or []:
            mac = normalize_mac(str(device.get("mac") or ""))
            client = self._clients_by_mac.get(mac)
            result.append(
                {
                    **device,
                    "connected": device.get("id") in online or bool(client),
                    "client": client,
                }
            )
        return result

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

    async def assign_device(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None = None,
    ) -> None:
        """Assign a device MAC to a person (persisted in JSON)."""
        await self.hass.async_add_executor_job(
            self._assign_device_sync, mac, person, device_type, device_name
        )
        await self.async_request_refresh()

    def _assign_device_sync(
        self,
        mac: str,
        person: str,
        device_type: str,
        device_name: str | None,
    ) -> None:
        mac_n = normalize_mac(mac)
        devices_data = self._loader.get_devices()
        devices = list(devices_data.get("devices") or [])
        existing = next(
            (d for d in devices if normalize_mac(str(d.get("mac") or "")) == mac_n),
            None,
        )
        device_id = existing["id"] if existing else f"dev-{mac_n.replace(':', '')}"
        if existing is None:
            devices.append(
                {
                    "id": device_id,
                    "name": device_name or mac_n,
                    "type": "other",
                    "mac": mac_n,
                    "hostname_match": [],
                    "track": True,
                    "notes": f"assigned as {device_type}",
                }
            )
            devices_data["devices"] = devices
            self._write_json(self.storage_path / DEVICES_FILE, devices_data)

        people_data = self._loader.get_people()
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
        ids = list(target.get("device_ids") or [])
        if device_id not in ids:
            if device_type == "primary":
                ids.insert(0, device_id)
            else:
                ids.append(device_id)
            target["device_ids"] = ids
        self._write_json(self.storage_path / PEOPLE_FILE, people_data)
        self._loader.reload()

    async def track_device(
        self, mac: str, name: str, device_type: str = "other"
    ) -> None:
        """Start tracking a device."""
        await self.hass.async_add_executor_job(
            self._track_device_sync, mac, name, device_type
        )
        await self.async_request_refresh()

    def _track_device_sync(self, mac: str, name: str, device_type: str) -> None:
        mac_n = normalize_mac(mac)
        devices_data = self._loader.get_devices()
        devices = list(devices_data.get("devices") or [])
        for device in devices:
            if normalize_mac(str(device.get("mac") or "")) == mac_n:
                device["track"] = True
                device["name"] = name
                device["type"] = device_type
                self._write_json(self.storage_path / DEVICES_FILE, devices_data)
                self._loader.reload()
                return
        devices.append(
            {
                "id": f"dev-{mac_n.replace(':', '')}",
                "name": name,
                "type": device_type,
                "mac": mac_n,
                "hostname_match": [name] if name else [],
                "track": True,
            }
        )
        devices_data["devices"] = devices
        self._write_json(self.storage_path / DEVICES_FILE, devices_data)
        self._loader.reload()

    async def remove_device(self, mac: str) -> None:
        """Stop tracking / remove a device."""
        await self.hass.async_add_executor_job(self._remove_device_sync, mac)
        await self.async_request_refresh()

    def _remove_device_sync(self, mac: str) -> None:
        mac_n = normalize_mac(mac)
        devices_data = self._loader.get_devices()
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

        people_data = self._loader.get_people()
        for person in people_data.get("people") or []:
            ids = [i for i in (person.get("device_ids") or []) if i not in removed_ids]
            person["device_ids"] = ids
        self._write_json(self.storage_path / PEOPLE_FILE, people_data)
        self._loader.reload()

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

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# Backward-compatible alias used by older tests/docs.
UniFiCoordinator = UniFiPeoplePointerCoordinator
