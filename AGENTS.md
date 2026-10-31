# Agent Documentation: UniFi People Pointer

## Project Overview

**UniFi People Pointer** is a Home Assistant custom integration for person-based presence tracking using UniFi Network as the data source.

## Current Implementation Status

### ✅ Phase 3 wired: entities + UniFi presence (v1.2.0)

**What's Implemented:**

1. **Services System** (`services.yaml` + `services.py`)
   - 6 services with full validation schemas
   - Service handlers in `services.py` delegate to coordinator
   - All services logged and error-handled

2. **Event System** (`events.py`)
   - 4 event types: person_arrived, person_left, device_connected, unknown_device
   - EventDebouncer class implements 3-minute debouncing
   - Prevents WiFi flapping spam
   - Events queued and fired after stable state

3. **Integration Structure**
   - `__init__.py` - Entry point; creates coordinator, registers services, forwards platforms
   - `const.py` - Constants and defaults
   - `config_flow.py` - User / options / reauth flows with UniFi API validation
   - `coordinator.py` - UniFi client poll + presence computation
   - `device_tracker.py` / `sensor.py` - person/device trackers and unknown/guest sensors
   - `api_parser.py`, `data_loader.py`, `device_matcher.py`, `presence.py` - parsing and matching
   - JSON storage under HA config `unifi_people_pointer/` (`people.json`, `devices.json`)
   - `manifest.json` - Integration metadata
   - `strings.json` + translations - UI strings (EN/DE)

**Config flow (ships with this branch):**

- Form schema keys: `host`, `api_token`, `verify_ssl`
- Entry data keys: `CONF_HOST`, `CONF_TOKEN` (`token`), `verify_ssl` — form `api_token` is mapped to `CONF_TOKEN` on create
- `validate_api_connection` hits `GET /proxy/network/integration/v1/sites` with `X-API-KEY`
- Options flow updates `scan_interval` and `webui_port`; reauth step is `reauth_confirm`
- No `NotImplementedError` on config/setup path (avoids HA HTTP 500 when adding the integration)

**Still limited / later:**

- Mobile-app and ping fallbacks not fully wired
- OUI database update and file watcher are incomplete

## Architecture Decisions

### Event Debouncing Strategy

**Problem:** WiFi devices frequently flap (connect/disconnect rapidly), causing event spam.

**Solution:** 3-minute debounce window
- Events are queued, not fired immediately
- If state changes within 3min, previous event is canceled
- Only fires event after 3min of stable state
- Per-identifier tracking (person ID or device MAC)

Implementation: `EventDebouncer` class in `events.py`

### Service → Coordinator Pattern

**Services never directly manipulate data**. All service calls:
1. Validate input (voluptuous schemas)
2. Delegate to coordinator methods
3. Coordinator updates data under `_config_lock` (reload JSON, rebuild presence, sync tracker entities)
4. Coordinator publishes updated data and requests a client refresh
5. Entities update via coordinator (no full config-entry reload on assign/track/remove/claim)

`assign_device` / `claim_unknown_device` are exclusive per MAC/device id across people.

This ensures:
- Single source of truth (coordinator)
- Atomic updates
- Proper state propagation
- Event firing in correct order


## File Organization

```
custom_components/unifi_people_pointer/
├── __init__.py              # Integration setup, service registration
├── const.py                 # All constants (events, services, defaults)
├── config_flow.py           # User/options/reauth config flow + API validation
├── coordinator.py           # UniFi poll + presence computation
├── events.py                # Event system + debouncer
├── services.py              # Service handlers + schemas
├── services.yaml            # Service definitions (UI metadata)
├── strings.json             # Base UI strings
├── manifest.json            # HA integration metadata
└── translations/
    ├── en.json              # English
    └── de.json              # German
```

## Key Code Patterns

### Service Handler Pattern

```python
async def handle_service_name(call: ServiceCall) -> None:
    """Handle service call."""
    # 1. Extract params
    param = call.data["param"]
    
    # 2. Get coordinator
    coordinator = hass.data[DOMAIN].get("coordinator")
    if not coordinator:
        raise HomeAssistantError("Not initialized")
    
    # 3. Delegate to coordinator
    try:
        await coordinator.method(param)
    except Exception as err:
        raise HomeAssistantError(f"Failed: {err}") from err
```

### Event Firing Pattern

```python
# Get event manager
event_manager = hass.data[DOMAIN]["event_manager"]

# Fire debounced event
event_manager.fire_person_arrived(
    person="sebastian",
    device="AA:BB:CC:DD:EE:FF",
    ap_name="AP-EG",
    zone="zone.eg",
    signal_strength=-45,
)
```


## Testing Checklist

When testing this integration:

1. **Services**: Developer Tools → Services
   - Call each service with valid data
   - Verify coordinator methods are called
   - Check logs for success messages

2. **Events**: Developer Tools → Events
   - Listen to `unifi_people_pointer_*` events
   - Trigger state changes
   - Verify debouncing (should NOT fire immediately)
   - Wait 3 minutes, verify event fires


4. **Config Flow**: Settings → Integrations
   - Add integration via UI
   - Verify config entry created
   - Test options flow (modify poll_interval, etc.)

## Next Implementation Phases

### Phase 4 leftovers
- OUI database update path
- File watcher for JSON changes (poll already reloads JSON)
- AP zone mapping polish

### Phase 5: Web UI
- Shipped inside the integration (see `webui.py`, `frontend/`); no Node backend or Docker

## Common Issues & Solutions

### Issue: Services not showing in UI
**Solution:** Check `services.yaml` syntax, restart HA, clear browser cache


### Issue: Events not firing
**Solution:** Check debounce timeout (3min default), verify event_manager is initialized, check logs for event scheduling

### Issue: Coordinator not found in services
**Solution:** Verify `async_setup_entry()` stores coordinator in `hass.data[DOMAIN]`, check initialization order

### Issue: Tests cannot find integration `unifi_people_pointer`
**Cause:** HA test harness caches empty `testing_config/custom_components` in `sys.modules`.
**Solution:** `tests/conftest.py` clears that cache and prefers the repo `custom_components` package (`pythonpath = .` in `pytest.ini`).

## Maintaining this file

When making changes to this project:

1. **Update version** in `manifest.json` when shipping features
2. **Update README.md** with new examples when adding services/events
3. **Update AGENTS.md** when making architectural decisions
4. **Update translations** (en.json, de.json) when changing UI strings
5. **Update services.yaml** when modifying service schemas

Keep this file for durable project knowledge only. Prefer pointers to authoritative files over copying large specs.

## Scout Report Reference

Full design document: `/home/ladwein/dtry-agent-workspace/data/unifi-people-pointer-scout-20260815/report.md`

This implementation follows the scout report through Phase 3 entity/presence wiring; services/events from Phase 2 remain.

## Integration with Home Assistant

### Required Dependencies
- `aiounifi>=70` - UniFi API client (not yet used)
- `aiohttp>=3.8.0` - Async HTTP
- `icmplib>=3.0` - Ping functionality (not yet used)

### Home Assistant Version
- Minimum: 2024.1.0
- Tested: 2024.1+

### Platform Support
- Currently: `device_tracker`, `sensor`

## Code Style & Conventions

- **Logging**: Use module-level `_LOGGER` with appropriate levels (debug, info, warning, error)
- **Type hints**: All functions have return type hints
- **Docstrings**: Google-style docstrings for all public methods
- **Constants**: All magic values in `const.py`
- **Async**: All I/O operations are async
- **Error handling**: Catch specific exceptions, raise `HomeAssistantError` for user-facing errors

## Git Workflow

Use a short-lived feature branch per change; open a PR against `main` for review.
