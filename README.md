# UniFi People Pointer

Person-based presence tracking for Home Assistant using UniFi Network as the data source.

## Overview

UniFi People Pointer is a Home Assistant custom integration that tracks **people** (not just devices) based on their WiFi presence in a UniFi network. It supports:

- **Multi-Device Tracking**: Track a person across primary and secondary devices
- **3-Level Fallback**: UniFi → Mobile App → Ping with configurable grace period
- **Unknown Device Detection**: Automatically detect and claim new devices
- **Guest Network Tracking**: Separate tracking for guest WiFi clients
- **Access Point Zones**: Map APs to Home Assistant zones for room-level presence

## Status: Phase 1 - Core Foundation ✅

This is the **Phase 1** release containing the core integration structure:

### What's Included

- ✅ **Integration Scaffold**: Full Home Assistant custom component structure
- ✅ **Config Flow**: 3-step setup UI (UniFi Connection → Polling Settings → OUI Auto-Update)
- ✅ **Manifest**: HACS-ready metadata with required dependencies
- ✅ **Coordinator**: Data update coordinator for UniFi API polling
- ✅ **Device Tracker Platform**: Person and Device tracker entities (structure ready)
- ✅ **Sensor Platform**: Unknown Clients and Guest Clients sensors (structure ready)
- ✅ **Constants**: All configuration constants and defaults
- ✅ **Translations**: English language strings

### What's Next (Phase 2+)

- 🔲 **UniFi API Client**: Full implementation of UniFi Network API integration
- 🔲 **Fallback Logic**: Mobile App GPS and Ping fallback implementation
- 🔲 **Grace Period**: 10-minute grace period before marking person away
- 🔲 **Event System**: Person arrived/left events with debouncing
- 🔲 **JSON Storage**: People, devices, and zone configuration files
- 🔲 **Services**: Add/remove person, claim device, scan now, etc.
- 🔲 **OUI Manager**: Manufacturer database with auto-updates
- 🔲 **Webapp**: React-based management interface

See [Scout Report](data/unifi-people-pointer-scout-20260815/report.md) for complete design and roadmap.

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "UniFi People Pointer"
3. Click Download
4. Restart Home Assistant

### Manual

1. Copy `custom_components/unifi_people_pointer` to your `config/custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **UniFi People Pointer**
4. Follow the 3-step setup:
   - **Step 1**: Enter UniFi Controller URL and API Key
   - **Step 2**: Configure polling interval and fallback settings
   - **Step 3**: Configure OUI database auto-update

## Architecture

```
custom_components/unifi_people_pointer/
├── __init__.py              # Integration entry point
├── config_flow.py           # 3-step config flow UI
├── const.py                 # Constants and defaults
├── coordinator.py           # Data update coordinator
├── device_tracker.py        # Person/Device tracker entities
├── sensor.py                # Unknown/Guest client sensors
├── manifest.json            # Integration metadata
├── strings.json             # Translation strings
└── translations/
    └── en.json              # English translations
```

## Requirements

- Home Assistant 2024.1+
- UniFi Network Controller with API access
- Python 3.11+

### Dependencies

- `aiounifi>=70.0.0` - UniFi Network API client
- `aiohttp>=3.8.0` - Async HTTP requests
- `icmplib>=3.0.0` - Ping functionality

## Development

This integration follows Home Assistant development best practices:

- **Config Flow**: UI-based configuration (no YAML)
- **DataUpdateCoordinator**: Efficient polling with built-in retry logic
- **Entity Platform**: Standard device_tracker and sensor platforms
- **Async**: Fully async implementation
- **Logging**: Comprehensive debug logging

## Scout Report

Full design documentation and implementation roadmap:
- [Scout Report](data/unifi-people-pointer-scout-20260815/report.md)

## License

MIT License - See LICENSE file

## Author

Sebastian Ladwein ([@thelad-dev](https://github.com/thelad-dev))

## Support

- **Issues**: [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)

---

**Version**: 0.1.0 (Phase 1 - Core Foundation)
**Last Updated**: 2026-08-15
