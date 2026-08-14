"""Event system for UniFi People Pointer with debouncing."""
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .const import (
    DOMAIN,
    EVENT_PERSON_ARRIVED,
    EVENT_PERSON_LEFT,
    EVENT_DEVICE_CONNECTED,
    EVENT_UNKNOWN_DEVICE,
    DEFAULT_EVENT_DEBOUNCE,
)

_LOGGER = logging.getLogger(__name__)


class EventDebouncer:
    """Debouncer for preventing event spam from WiFi flapping."""

    def __init__(self, hass: HomeAssistant, debounce_seconds: int = DEFAULT_EVENT_DEBOUNCE):
        """Initialize debouncer."""
        self.hass = hass
        self.debounce_seconds = debounce_seconds
        self._pending_events: dict[str, dict[str, Any]] = {}
        self._timers: dict[str, Any] = {}

    def _get_event_key(self, event_type: str, identifier: str) -> str:
        """Get unique key for event."""
        return f"{event_type}_{identifier}"

    @callback
    def _fire_event(self, event_key: str) -> None:
        """Fire the debounced event."""
        if event_key not in self._pending_events:
            return

        event_data = self._pending_events.pop(event_key)
        event_type = event_data.pop("_event_type")
        
        _LOGGER.debug(
            "Firing debounced event: %s with data: %s",
            event_type,
            event_data,
        )
        
        self.hass.bus.async_fire(event_type, event_data)
        
        # Clean up timer reference
        if event_key in self._timers:
            del self._timers[event_key]

    @callback
    def schedule_event(
        self,
        event_type: str,
        identifier: str,
        event_data: dict[str, Any],
    ) -> None:
        """Schedule an event with debouncing."""
        event_key = self._get_event_key(event_type, identifier)
        
        # Cancel existing timer if present
        if event_key in self._timers:
            self._timers[event_key]()
            del self._timers[event_key]
        
        # Store event data with type
        event_data_with_type = {**event_data, "_event_type": event_type}
        self._pending_events[event_key] = event_data_with_type
        
        # Schedule new timer
        if self.debounce_seconds > 0:
            _LOGGER.debug(
                "Scheduling debounced event: %s (key: %s) in %d seconds",
                event_type,
                event_key,
                self.debounce_seconds,
            )
            self._timers[event_key] = async_call_later(
                self.hass,
                self.debounce_seconds,
                lambda _: self._fire_event(event_key),
            )
        else:
            # No debouncing, fire immediately
            self._fire_event(event_key)

    @callback
    def cancel_event(self, event_type: str, identifier: str) -> None:
        """Cancel a pending event."""
        event_key = self._get_event_key(event_type, identifier)
        
        if event_key in self._timers:
            self._timers[event_key]()
            del self._timers[event_key]
        
        if event_key in self._pending_events:
            del self._pending_events[event_key]


class UniFiEventManager:
    """Manager for UniFi People Pointer events."""

    def __init__(self, hass: HomeAssistant, debounce_seconds: int = DEFAULT_EVENT_DEBOUNCE):
        """Initialize event manager."""
        self.hass = hass
        self._debouncer = EventDebouncer(hass, debounce_seconds)

    @callback
    def fire_person_arrived(
        self,
        person: str,
        device: str,
        ap_name: str | None = None,
        zone: str | None = None,
        signal_strength: int | None = None,
    ) -> None:
        """Fire person arrived event with debouncing."""
        event_data = {
            "person": person,
            "device": device,
            "timestamp": datetime.now().isoformat(),
        }
        
        if ap_name:
            event_data["ap_name"] = ap_name
        if zone:
            event_data["zone"] = zone
        if signal_strength is not None:
            event_data["signal_strength"] = signal_strength
        
        self._debouncer.schedule_event(
            EVENT_PERSON_ARRIVED,
            person,
            event_data,
        )

    @callback
    def fire_person_left(
        self,
        person: str,
        device: str,
        last_seen: datetime | None = None,
        duration: int | None = None,
    ) -> None:
        """Fire person left event with debouncing."""
        event_data = {
            "person": person,
            "device": device,
            "timestamp": datetime.now().isoformat(),
        }
        
        if last_seen:
            event_data["last_seen"] = last_seen.isoformat()
        if duration is not None:
            event_data["duration"] = duration
        
        self._debouncer.schedule_event(
            EVENT_PERSON_LEFT,
            person,
            event_data,
        )

    @callback
    def fire_device_connected(
        self,
        mac: str,
        person: str | None = None,
        device_type: str | None = None,
        ap_name: str | None = None,
        zone: str | None = None,
        signal_strength: int | None = None,
    ) -> None:
        """Fire device connected event with debouncing."""
        event_data = {
            "mac": mac,
            "timestamp": datetime.now().isoformat(),
        }
        
        if person:
            event_data["person"] = person
        if device_type:
            event_data["device_type"] = device_type
        if ap_name:
            event_data["ap_name"] = ap_name
        if zone:
            event_data["zone"] = zone
        if signal_strength is not None:
            event_data["signal_strength"] = signal_strength
        
        self._debouncer.schedule_event(
            EVENT_DEVICE_CONNECTED,
            mac,
            event_data,
        )

    @callback
    def fire_unknown_device(
        self,
        mac: str,
        ip: str | None = None,
        hostname: str | None = None,
        manufacturer: str | None = None,
        ap_name: str | None = None,
        signal_strength: int | None = None,
    ) -> None:
        """Fire unknown device event with debouncing."""
        event_data = {
            "mac": mac,
            "timestamp": datetime.now().isoformat(),
        }
        
        if ip:
            event_data["ip"] = ip
        if hostname:
            event_data["hostname"] = hostname
        if manufacturer:
            event_data["manufacturer"] = manufacturer
        if ap_name:
            event_data["ap_name"] = ap_name
        if signal_strength is not None:
            event_data["signal_strength"] = signal_strength
        
        self._debouncer.schedule_event(
            EVENT_UNKNOWN_DEVICE,
            mac,
            event_data,
        )

    @callback
    def cancel_person_event(self, person: str, event_type: str) -> None:
        """Cancel a pending person event."""
        self._debouncer.cancel_event(event_type, person)

    @callback
    def cancel_device_event(self, mac: str, event_type: str) -> None:
        """Cancel a pending device event."""
        self._debouncer.cancel_event(event_type, mac)
