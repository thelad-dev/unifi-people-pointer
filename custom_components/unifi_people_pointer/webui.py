"""Built-in web UI: aiohttp server on 0.0.0.0 plus a Home Assistant sidebar panel.

The UI bundle (``webui/``) ships inside the integration, so a HACS install or a
manual copy of ``custom_components/unifi_people_pointer`` is all it needs. The
server binds on all interfaces at the configured port. Every ``/api`` request
must carry a valid Home Assistant access token; changes need an admin user.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.core import HomeAssistant
from yarl import URL

from .api_parser import normalize_mac
from .const import (
    DEFAULT_WEBUI_PORT,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_STATIC_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
    WEBUI_BIND_HOST,
)
from .coordinator import UniFiPeoplePointerCoordinator
from .presence import person_owns_device

_LOGGER = logging.getLogger(__name__)

WEBUI_DIR = Path(__file__).parent / "webui"
PANEL_DIR = Path(__file__).parent / "panel"
DEVICE_TYPES = ("smartphone", "tablet", "laptop", "watch", "wearable", "other")
_PERSON_ID_RE = re.compile(r"[^a-z0-9_-]+")

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def slugify_person_id(name: str) -> str:
    """Derive a stable person id from a display name."""
    return _PERSON_ID_RE.sub("_", name.strip().lower()).strip("_")


def _iso(value: Any) -> str | None:
    """Return a UniFi epoch or string timestamp as ISO text."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = int(value)
        if ts > 10_000_000_000:
            ts //= 1000
        try:
            return datetime.fromtimestamp(ts).isoformat()
        except (OverflowError, OSError, ValueError):
            return str(value)
    return str(value)


class WebUIServer:
    """Serve the UI bundle and its JSON API for one coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UniFiPeoplePointerCoordinator,
        port: int = DEFAULT_WEBUI_PORT,
        host: str = WEBUI_BIND_HOST,
    ) -> None:
        """Initialize the server (not started)."""
        self.hass = hass
        self.coordinator = coordinator
        self.port = port
        self.host = host
        self._runner: web.AppRunner | None = None

    @property
    def running(self) -> bool:
        """True while the TCP site is up."""
        return self._runner is not None

    def build_app(self) -> web.Application:
        """Create the aiohttp application (routes + auth middleware)."""
        app = web.Application(middlewares=[self._auth_middleware])
        app.router.add_get("/api/health", self._health)
        app.router.add_get("/api/overview", self._overview)
        app.router.add_get("/api/persons", self._list_persons)
        app.router.add_post("/api/persons", self._create_person)
        app.router.add_put("/api/persons/{person_id}", self._update_person)
        app.router.add_delete("/api/persons/{person_id}", self._delete_person)
        app.router.add_get("/api/devices", self._list_devices)
        app.router.add_post("/api/devices", self._create_device)
        app.router.add_put("/api/devices/{device_id}", self._update_device)
        app.router.add_delete("/api/devices/{device_id}", self._delete_device)
        app.router.add_get("/api/clients/unknown", self._unknown_clients)
        app.router.add_post("/api/clients/{mac}/claim", self._claim_client)
        app.router.add_get("/api/access-points", self._access_points)
        app.router.add_route("*", "/api/{tail:.*}", self._api_not_found)
        app.router.add_get("/{tail:.*}", self._static)
        return app

    async def async_start(self) -> bool:
        """Bind on host:port; log and return False when the port is taken."""
        runner = web.AppRunner(self.build_app(), access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        try:
            await site.start()
        except OSError as err:
            await runner.cleanup()
            _LOGGER.error(
                "UniFi People Pointer web UI could not bind %s:%s: %s",
                self.host,
                self.port,
                err,
            )
            return False
        self._runner = runner
        _LOGGER.info(
            "UniFi People Pointer web UI listening on %s:%s", self.host, self.port
        )
        return True

    async def async_stop(self) -> None:
        """Stop the server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    # --- auth -----------------------------------------------------------------

    @web.middleware
    async def _auth_middleware(
        self, request: web.Request, handler: Handler
    ) -> web.StreamResponse:
        if not request.path.startswith("/api/") or request.path == "/api/health":
            return await handler(request)
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        refresh_token = (
            self.hass.auth.async_validate_access_token(token) if token else None
        )
        user = refresh_token.user if refresh_token is not None else None
        if user is None or not user.is_active:
            return web.json_response({"error": "unauthorized"}, status=401)
        if request.method not in ("GET", "HEAD") and not user.is_admin:
            return web.json_response({"error": "admin required"}, status=403)
        return await handler(request)

    # --- static ---------------------------------------------------------------

    async def _static(self, request: web.Request) -> web.StreamResponse:
        tail = request.match_info.get("tail", "")
        root = WEBUI_DIR.resolve()
        if tail:
            candidate = (root / tail).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                cache = (
                    "public, max-age=31536000, immutable"
                    if tail.startswith("assets/")
                    else "no-cache"
                )
                return web.FileResponse(candidate, headers={"Cache-Control": cache})
        index = root / "index.html"
        if not index.is_file():
            return web.Response(status=503, text="web UI bundle missing")
        # SPA routes fall back to index.html.
        return web.FileResponse(index, headers={"Cache-Control": "no-cache"})

    async def _api_not_found(self, request: web.Request) -> web.Response:
        return web.json_response({"error": "not found"}, status=404)

    # --- read endpoints -------------------------------------------------------

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def _overview(self, request: web.Request) -> web.Response:
        persons = self._persons_payload()
        devices = self._devices_payload()
        return web.json_response(
            {
                "persons_home": sum(1 for p in persons if p["state"] == "home"),
                "persons_total": len(persons),
                "devices_online": sum(1 for d in devices if d["online"]),
                "devices_total": len(devices),
                "unknown_clients": len(self.coordinator.get_unknown_clients()),
                "guest_clients": len(self.coordinator.get_guest_clients()),
                "access_points": len(self.coordinator.get_access_points()),
                "last_update_success": self.coordinator.last_update_success,
                "persons": persons,
            }
        )

    async def _list_persons(self, request: web.Request) -> web.Response:
        return web.json_response(self._persons_payload())

    async def _list_devices(self, request: web.Request) -> web.Response:
        return web.json_response(self._devices_payload())

    async def _unknown_clients(self, request: web.Request) -> web.Response:
        coordinator = self.coordinator
        rows = [
            {
                "mac": client.get("mac"),
                "hostname": client.get("hostname") or None,
                "ip": client.get("ip"),
                "signal": client.get("signal"),
                "ap_mac": client.get("ap_mac"),
                "ap_name": coordinator.get_client_ap_name(client),
                "last_seen": _iso(client.get("last_seen")),
            }
            for client in coordinator.get_unknown_clients()
        ]
        return web.json_response(rows)

    async def _access_points(self, request: web.Request) -> web.Response:
        return web.json_response(self.coordinator.get_access_points())

    def _persons_payload(self) -> list[dict[str, Any]]:
        coordinator = self.coordinator
        rows = []
        for person in coordinator.people:
            person_id = str(person.get("id"))
            presence = coordinator.get_person_presence(person_id) or {}
            rows.append(
                {
                    "id": person_id,
                    "name": person.get("name") or person_id,
                    "ha_person": person.get("ha_person"),
                    "device_ids": list(person.get("device_ids") or []),
                    "state": coordinator.get_person_state(person_id),
                    "devices_online": presence.get("devices_online", 0),
                    "ap_name": coordinator.get_person_ap_name(person_id),
                }
            )
        return rows

    def _owner(self, device: dict[str, Any]) -> str | None:
        for person in self.coordinator.people:
            if person_owns_device(
                person,
                device_id=device.get("id"),
                device_mac=device.get("mac"),
                devices=self.coordinator.devices,
            ):
                return str(person.get("id"))
        return None

    def _devices_payload(self) -> list[dict[str, Any]]:
        coordinator = self.coordinator
        rows = []
        for device in coordinator.devices:
            mac = normalize_mac(str(device.get("mac") or ""))
            online = bool(mac) and coordinator.is_device_online(mac)
            client = (
                coordinator.async_get_client_by_mac(mac) if online else None
            ) or {}
            rows.append(
                {
                    "id": device.get("id"),
                    "name": device.get("name") or device.get("id"),
                    "mac": mac,
                    "type": device.get("type") or "other",
                    "track": device.get("track", True) is not False,
                    "person": self._owner(device),
                    "online": online,
                    "ip": client.get("ip"),
                    "hostname": client.get("hostname") or None,
                    "signal": client.get("signal"),
                    "ap_mac": client.get("ap_mac"),
                    "ap_name": (
                        coordinator.get_client_ap_name(client) if online else None
                    ),
                    "last_seen": _iso(client.get("last_seen")),
                }
            )
        return rows

    # --- write endpoints ------------------------------------------------------

    @staticmethod
    async def _json_body(request: web.Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except ValueError as err:
            raise web.HTTPBadRequest(text="invalid JSON") from err
        if not isinstance(body, dict):
            raise web.HTTPBadRequest(text="JSON object expected")
        return body

    @staticmethod
    def _text(body: dict[str, Any], key: str, required: bool = False) -> str:
        value = str(body.get(key) or "").strip()
        if required and not value:
            raise web.HTTPBadRequest(text=f"{key} is required")
        return value

    @staticmethod
    def _ha_person(body: dict[str, Any]) -> str | None:
        value = str(body.get("ha_person") or "").strip()
        if value and not value.startswith("person."):
            raise web.HTTPBadRequest(text="ha_person must be a person.* entity id")
        return value or None

    @staticmethod
    def _device_type(body: dict[str, Any]) -> str:
        value = str(body.get("type") or "other").strip()
        if value not in DEVICE_TYPES:
            raise web.HTTPBadRequest(
                text=f"type must be one of {', '.join(DEVICE_TYPES)}"
            )
        return value

    @staticmethod
    def _role(body: dict[str, Any]) -> str:
        return "primary" if body.get("role") == "primary" else "secondary"

    def _person_exists(self, person_id: str) -> bool:
        return any(str(p.get("id")) == person_id for p in self.coordinator.people)

    def _device(self, device_id: str) -> dict[str, Any]:
        for device in self.coordinator.devices:
            if device.get("id") == device_id:
                return device
        raise web.HTTPNotFound(text="device not found")

    async def _create_person(self, request: web.Request) -> web.Response:
        body = await self._json_body(request)
        name = self._text(body, "name", required=True)
        person_id = slugify_person_id(self._text(body, "id") or name)
        if not person_id:
            raise web.HTTPBadRequest(text="name must contain letters or digits")
        if self._person_exists(person_id):
            return web.json_response({"error": "person exists"}, status=409)
        person = await self.coordinator.save_person(
            person_id, name, self._ha_person(body)
        )
        return web.json_response(person, status=201)

    async def _update_person(self, request: web.Request) -> web.Response:
        person_id = request.match_info["person_id"]
        if not self._person_exists(person_id):
            raise web.HTTPNotFound(text="person not found")
        body = await self._json_body(request)
        person = await self.coordinator.save_person(
            person_id, self._text(body, "name", required=True), self._ha_person(body)
        )
        return web.json_response(person)

    async def _delete_person(self, request: web.Request) -> web.Response:
        if not await self.coordinator.delete_person(request.match_info["person_id"]):
            raise web.HTTPNotFound(text="person not found")
        return web.Response(status=204)

    async def _create_device(self, request: web.Request) -> web.Response:
        body = await self._json_body(request)
        mac = normalize_mac(self._text(body, "mac", required=True))
        if len(mac.split(":")) != 6:
            raise web.HTTPBadRequest(text="mac must be a MAC address")
        name = self._text(body, "name", required=True)
        device_type = self._device_type(body)
        person = self._text(body, "person")
        if person and not self._person_exists(person):
            raise web.HTTPBadRequest(text="unknown person")
        await self.coordinator.track_device(mac, name, device_type)
        if person:
            await self.coordinator.assign_device(mac, person, self._role(body), name)
        return web.json_response({"mac": mac}, status=201)

    async def _update_device(self, request: web.Request) -> web.Response:
        device = self._device(request.match_info["device_id"])
        body = await self._json_body(request)
        name = self._text(body, "name", required=True)
        device_type = self._device_type(body)
        await self.coordinator.update_device(str(device["id"]), name, device_type)
        if "person" in body:
            person = self._text(body, "person")
            if person and not self._person_exists(person):
                raise web.HTTPBadRequest(text="unknown person")
            if person:
                await self.coordinator.assign_device(
                    str(device["mac"]), person, self._role(body), name
                )
            elif self._owner(device):
                await self.coordinator.unassign_device(str(device["id"]))
        return web.json_response({"id": device["id"]})

    async def _delete_device(self, request: web.Request) -> web.Response:
        device = self._device(request.match_info["device_id"])
        await self.coordinator.remove_device(str(device["mac"]))
        return web.Response(status=204)

    async def _claim_client(self, request: web.Request) -> web.Response:
        mac = normalize_mac(request.match_info["mac"])
        body = await self._json_body(request)
        person = self._text(body, "person", required=True)
        if not self._person_exists(person):
            raise web.HTTPBadRequest(text="unknown person")
        name = self._text(body, "name") or None
        await self.coordinator.claim_unknown_device(mac, person, self._role(body), name)
        return web.json_response({"mac": mac}, status=201)


# --- Home Assistant integration (panel + link) ----------------------------------


async def async_webui_url(hass: HomeAssistant, port: int) -> str | None:
    """Return a LAN URL of the web UI for links (device configuration_url)."""
    from homeassistant.helpers.network import NoURLAvailableError, get_url

    host: str | None
    try:
        host = URL(get_url(hass, allow_external=False, allow_cloud=False)).host
    except NoURLAvailableError:
        host = None
    if not host and "network" in hass.config.components:
        from homeassistant.components import network

        host = await network.async_get_source_ip(hass)
    if not host:
        return None
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"http://{host}:{port}/"


async def async_register_panel(hass: HomeAssistant, port: int) -> None:
    """Register the sidebar panel that embeds the web UI."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("panel_static_registered"):
        path = str(PANEL_DIR / "upp-panel.js")
        try:
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [StaticPathConfig(PANEL_STATIC_URL, path, False)]
            )
        except ImportError:  # Home Assistant before 2024.7
            hass.http.register_static_path(PANEL_STATIC_URL, path, False)
        domain_data["panel_static_registered"] = True

    from homeassistant.components import frontend, panel_custom

    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    # Bust the browser cache of the panel module after updates.
    version = int((PANEL_DIR / "upp-panel.js").stat().st_mtime)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_STATIC_URL}?v={version}",
        config={"port": port},
        require_admin=True,
        config_panel_domain=DOMAIN,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel."""
    from homeassistant.components import frontend

    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
