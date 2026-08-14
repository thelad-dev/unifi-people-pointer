# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-15

### Added - Phase 1: Core Foundation

- Initial integration scaffold with Home Assistant structure
- 3-step config flow UI (UniFi Connection → Polling Settings → OUI Auto-Update)
- Data update coordinator for UniFi API polling
- Device tracker platform structure (Person and Device trackers)
- Sensor platform structure (Unknown Clients and Guest Clients)
- Constants and configuration defaults
- English translations
- HACS compatibility metadata
- JSON schema definitions for people, devices, and zones
- Comprehensive README and documentation

### Phase 1 Deliverables ✅

- ✅ Integration scaffold
- ✅ Config Flow (3 steps)
- ✅ Manifest (HACS-ready)
- ✅ Coordinator structure
- ✅ Device tracker platform
- ✅ Sensor platform
- ✅ Constants
- ✅ Translations (EN)

### Coming in Phase 2

- UniFi API Client implementation
- Person/Device state tracking
- Grace period management
- Fallback logic (Mobile App + Ping)
- JSON file storage and management
- Event system with debouncing

[unreleased]: https://github.com/thelad-dev/unifi-people-pointer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v0.1.0
