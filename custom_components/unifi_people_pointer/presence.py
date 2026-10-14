"""Presence detection logic."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant

from .api_parser import normalize_mac
from .device_matcher import is_tracked, match_device, match_device_partial


def _device_by_id(devices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {d["id"]: d for d in devices if isinstance(d, dict) and d.get("id")}


def _online_device_ids(
    devices: list[dict[str, Any]],
    clients: list[dict[str, Any]],
) -> set[str]:
    """Return tracked device ids that match any online client.

    Matching is device-centric so overlapping hostname patterns on multiple
    tracked devices can all count as online for the same client.
    """
    online: set[str] = set()
    for device in devices:
        if not isinstance(device, dict):
            continue
        device_id = device.get("id")
        if not device_id or not is_tracked(device):
            continue
        alone = [device]
        for client in clients:
            if match_device(client, alone) or match_device_partial(client, alone):
                online.add(device_id)
                break
    return online


def determine_presence(
    people: list[dict[str, Any]],
    devices: list[dict[str, Any]],
    clients: list[dict[str, Any]],
    use_last_known_good: bool = False,
) -> list[dict[str, Any]]:
    """Determine presence for all people."""
    _ = use_last_known_good
    online_ids = _online_device_ids(devices, clients)
    by_id = _device_by_id(devices)
    results: list[dict[str, Any]] = []

    for person in people:
        person_id = person.get("id")
        if not person_id:
            continue
        device_ids = list(person.get("device_ids") or [])
        # Alternate schema: primary/secondary MAC lists
        if not device_ids and person.get("primary_device"):
            macs = [person["primary_device"], *person.get("secondary_devices", [])]
            for device in devices:
                device_id = device.get("id") if isinstance(device, dict) else None
                if not device_id:
                    continue
                if normalize_mac(str(device.get("mac") or "")) in {
                    normalize_mac(str(m)) for m in macs
                }:
                    device_ids.append(device_id)

        online_for_person = [d for d in device_ids if d in online_ids]
        is_home = len(online_for_person) > 0
        results.append(
            {
                "id": person_id,
                "name": person.get("name") or person_id,
                "ha_person": person.get("ha_person"),
                "is_home": is_home,
                "devices_online": len(online_for_person),
                "online_device_ids": online_for_person,
                "device_ids": device_ids,
                "devices": [by_id[d] for d in device_ids if d in by_id],
            }
        )
    return results


def detect_flapping(
    state_changes: list[dict[str, Any]],
    threshold: int = 4,
    window_seconds: int = 60,
) -> bool:
    """Detect if a device is flapping."""
    if len(state_changes) < threshold:
        return False
    now = datetime.now()
    recent = []
    for change in state_changes:
        ts = change.get("timestamp") or change.get("time")
        if isinstance(ts, datetime):
            when = ts
        elif isinstance(ts, (int, float)):
            when = datetime.fromtimestamp(ts)
        elif isinstance(ts, str):
            try:
                when = datetime.fromisoformat(ts)
            except ValueError:
                continue
        else:
            continue
        if now - when <= timedelta(seconds=window_seconds):
            recent.append(change)
    return len(recent) >= threshold


def calculate_confidence(
    last_seen: int,
    signal_strength: int,
    is_private_mac: bool,
) -> float:
    """Calculate presence confidence score between 0 and 1."""
    age = max(0, int(datetime.now().timestamp()) - int(last_seen))
    # Drop to 0 after ~5 minutes; recent sightings stay near 1.
    age_score = max(0.0, 1.0 - (age / 300.0))
    # Map RSSI roughly -30..-90 to 1..0
    signal_score = min(1.0, max(0.0, (int(signal_strength) + 90) / 60.0))
    private_penalty = 0.15 if is_private_mac else 0.0
    return max(0.0, min(1.0, (0.7 * age_score + 0.3 * signal_score) - private_penalty))


class PresenceTracker:
    """Track presence state with history."""

    def __init__(
        self,
        hass: HomeAssistant,
        devices: list[dict[str, Any]],
        people: list[dict[str, Any]],
        debounce_seconds: int = 0,
        track_history: bool = False,
    ) -> None:
        """Initialize presence tracker."""
        self.hass = hass
        self.devices = devices
        self.people = people
        self.debounce_seconds = debounce_seconds
        self.track_history = track_history
        self._states: dict[str, str] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._pending: dict[str, str] = {}
        self._pending_since: dict[str, datetime] = {}

    def _entity_id_for_person(self, person: dict[str, Any]) -> str:
        ha_person = person.get("ha_person")
        if ha_person:
            return str(ha_person)
        return f"person.{person['id']}"

    def update(self, clients: list[dict[str, Any]]) -> None:
        """Update presence based on current clients."""
        presence = determine_presence(self.people, self.devices, clients)
        now = datetime.now()
        for row in presence:
            person = next(p for p in self.people if p["id"] == row["id"])
            entity_id = self._entity_id_for_person(person)
            new_state = "home" if row["is_home"] else "not_home"
            old_state = self._states.get(entity_id)

            if self.debounce_seconds > 0 and old_state and new_state != old_state:
                pending = self._pending.get(entity_id)
                if pending != new_state:
                    self._pending[entity_id] = new_state
                    self._pending_since[entity_id] = now
                    continue
                since = self._pending_since.get(entity_id, now)
                if (now - since).total_seconds() < self.debounce_seconds:
                    continue
                self._pending.pop(entity_id, None)
                self._pending_since.pop(entity_id, None)

            if old_state != new_state:
                if self.track_history:
                    self._history.setdefault(entity_id, []).append(
                        {
                            "timestamp": now.isoformat(),
                            "state": new_state,
                            "from": old_state,
                        }
                    )
            self._states[entity_id] = new_state

    def update_presence(self, entity_id: str, is_home: bool) -> None:
        """Update presence for a specific entity."""
        self._states[entity_id] = "home" if is_home else "not_home"

    def get_state(self, entity_id: str) -> str:
        """Get current presence state."""
        return self._states.get(entity_id, "not_home")

    def get_debounced_state(self, entity_id: str) -> bool:
        """Get debounced presence state."""
        return self.get_state(entity_id) == "home"

    def get_history(self, entity_id: str, hours: int = 24) -> list[dict[str, Any]]:
        """Get presence history."""
        cutoff = datetime.now() - timedelta(hours=hours)
        rows = []
        for entry in self._history.get(entity_id, []):
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
            except (KeyError, ValueError):
                continue
            if ts >= cutoff:
                rows.append(entry)
        return rows
