# Agent Documentation: UniFi People Pointer

## Project Overview

**UniFi People Pointer** is a Home Assistant custom integration for person-based presence tracking using UniFi Network as the data source.

## Current Implementation Status

### ✅ Phase 2 Complete: Services & Event System (v0.2.0)

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

3. **Template Helpers** (`template_helpers.py`)
   - 5 Jinja2 template functions
   - Registered in HA's global template function registry
   - Available in templates, automations, scripts

4. **Integration Structure**
   - `__init__.py` - Entry point; setup stores entry in `hass.data` (platforms deferred)
   - `const.py` - Constants and defaults
   - `config_flow.py` - User / options / reauth flows with UniFi API validation
   - `coordinator.py` - Data coordinator with stub methods
   - `manifest.json` - Integration metadata
   - `strings.json` + translations - UI strings (EN/DE)

**Config flow (ships with this branch):**

- Form schema keys: `host`, `api_token`, `verify_ssl`
- Entry data keys: `CONF_HOST`, `CONF_TOKEN` (`token`), `verify_ssl` — form `api_token` is mapped to `CONF_TOKEN` on create
- `validate_api_connection` hits `GET /proxy/network/integration/v1/sites` with `X-API-KEY`
- Options flow updates `scan_interval`; reauth step is `reauth_confirm`
- No `NotImplementedError` on config/setup path (avoids HA HTTP 500 when adding the integration)

**What's Stubbed:**

- Coordinator methods (no full UniFi client wiring yet)
- Device tracker / sensor platforms not forwarded from setup yet
- No JSON file storage (people.json, devices.json, etc.)

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
3. Coordinator updates data
4. Coordinator triggers refresh
5. Entities update via coordinator

This ensures:
- Single source of truth (coordinator)
- Atomic updates
- Proper state propagation
- Event firing in correct order

### Template Helper Registration

Template helpers are registered in `hass.data["template_functions"]` dict. This makes them globally available without needing to pass context.

**Key Insight:** Template functions access coordinator via `hass.data[DOMAIN]["coordinator"]`, not via dependency injection. This allows templates to work anywhere.

## File Organization

```
custom_components/unifi_people_pointer/
├── __init__.py              # Integration setup, service/helper registration
├── const.py                 # All constants (events, services, defaults)
├── config_flow.py           # User/options/reauth config flow + API validation
├── coordinator.py           # Data coordinator (stub methods for Phase 2)
├── events.py                # Event system + debouncer
├── services.py              # Service handlers + schemas
├── services.yaml            # Service definitions (UI metadata)
├── template_helpers.py      # Jinja2 functions
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

### Template Helper Pattern

```python
def template_function(param: str) -> ReturnType:
    """Template helper docstring."""
    coordinator = hass.data.get(DOMAIN, {}).get("coordinator")
    if not coordinator:
        return default_value
    
    try:
        return coordinator.get_data(param)
    except Exception as err:
        _LOGGER.error("Error: %s", err)
        return default_value
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

3. **Template Helpers**: Developer Tools → Template
   - Test each helper function
   - Verify they return expected types
   - Test with invalid/missing data

4. **Config Flow**: Settings → Integrations
   - Add integration via UI
   - Verify config entry created
   - Test options flow (modify poll_interval, etc.)

## Next Implementation Phases

### Phase 3: Core Data & Entities
- UniFi API client integration
- Person tracker entities
- Device tracker entities
- JSON file storage (people.json, devices.json)
- AP zone mapping

### Phase 4: Advanced Features
- Unknown clients sensor
- Guest clients sensor
- OUI database integration
- File watcher for JSON changes

### Phase 5: Web UI
- React frontend
- Node.js backend
- Docker deployment

## Common Issues & Solutions

### Issue: Services not showing in UI
**Solution:** Check `services.yaml` syntax, restart HA, clear browser cache

### Issue: Template helpers not found
**Solution:** Verify `setup_template_helpers()` is called in `__init__.py`, check `hass.data["template_functions"]`

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
2. **Update README.md** with new examples when adding services/events/helpers
3. **Update AGENTS.md** when making architectural decisions
4. **Update translations** (en.json, de.json) when changing UI strings
5. **Update services.yaml** when modifying service schemas

Keep this file for durable project knowledge only. Prefer pointers to authoritative files over copying large specs.

## Scout Report Reference

Full design document: `/home/ladwein/dtry-agent-workspace/data/unifi-people-pointer-scout-20260815/report.md`

This implementation follows the scout report's Phase 2 specification for Services & Event System, with some consolidation from Phase 3 and Phase 4 service definitions.

## Integration with Home Assistant

### Required Dependencies
- `aiounifi>=70` - UniFi API client (not yet used)
- `aiohttp>=3.8.0` - Async HTTP
- `icmplib>=3.0` - Ping functionality (not yet used)

### Home Assistant Version
- Minimum: 2024.1.0
- Tested: 2024.1+

### Platform Support
- Currently: None (no platforms enabled yet)
- Planned: `device_tracker`, `sensor`

## Code Style & Conventions

- **Logging**: Use module-level `_LOGGER` with appropriate levels (debug, info, warning, error)
- **Type hints**: All functions have return type hints
- **Docstrings**: Google-style docstrings for all public methods
- **Constants**: All magic values in `const.py`
- **Async**: All I/O operations are async
- **Error handling**: Catch specific exceptions, raise `HomeAssistantError` for user-facing errors

## Git Workflow

Branch: `fm/unifi-pp-config-flow-500-20260816`

This is a firstmate-managed autonomous worker branch. Changes will be submitted as a PR for review.
