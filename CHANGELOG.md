# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TBD

## [1.0.0] - 2026-08-15

### 🎉 Full Release - Complete Person-based Presence Detection

This release builds on the Phase 1 foundation (v0.1.0) with full implementation of all features.

#### Core Features
- **Person-based Tracking**: Track people instead of individual devices
- **Multi-device Support**: Assign multiple devices (primary/secondary) to each person
- **Private MAC Support**: Handle iOS/Android devices with randomized MAC addresses via hostname matching
- **UniFi Native Integration**: Direct integration with UniFi Controller API (aiounifi)
- **Intelligent Presence Detection**: Grace periods and fallback mechanisms

#### Home Assistant Integration
- **Config Flow**: Guided 3-step setup through Home Assistant UI (from v0.1.0)
- **Device Tracker Entities**: Track presence per person (enhanced from v0.1.0)
- **Sensor Entities**: Unknown and Guest client sensors (enhanced from v0.1.0)
- **Services**: 6 services for device/person management (NEW)
  - `assign_device`: Assign device to person
  - `track_device`: Start tracking a new device
  - `remove_device`: Remove device from tracking
  - `scan_now`: Trigger immediate scan
  - `force_update_person`: Force person state update
  - `claim_unknown_device`: Claim and assign unknown device
- **Events**: Real-time events for automation (NEW)
  - `person_arrived`: Fired when person arrives
  - `person_left`: Fired when person leaves
  - `device_connected`: Fired when tracked device connects
  - `unknown_device`: Fired when unknown device detected

#### Configuration
- **JSON-based Storage**: Simple configuration files
  - `people.json`: Person definitions and device assignments
  - `devices.json`: Device details and hostname patterns
  - `ap_zones.json`: Zone/room mapping via access points
  - `manufacturers.json`: Custom manufacturer mappings
  - `oui_vendors.json`: IEEE OUI database cache
- **Flexible Polling**: Configurable poll interval (10-600s)
- **Grace Period**: Configurable delay before marking as away (1-30min)
- **Fallback Options**: Mobile App and Ping fallback support
- **Event Debouncing**: Prevent rapid state changes

#### Advanced Features
- **OUI Database**: Automatic manufacturer lookup via IEEE OUI database
- **Auto-update**: Optional automatic OUI database updates
- **Unknown Device Detection**: Alert on new devices joining network
- **Auto-dismiss**: Automatically dismiss old unknown device alerts (7 days)

#### Web Backend (Optional)
- **Management Backend**: Express.js API server for advanced management (NEW)
- **REST API**: Endpoints for people, devices, zones, and settings (NEW)
- **WebSocket**: Real-time client updates (NEW)
- **Home Assistant Integration**: Direct HA API integration for live state (NEW)
- **Docker Support**: Docker Compose configuration included (NEW)

#### HACS Support
- **HACS Compatible**: Ready for Home Assistant Community Store (from v0.1.0)
- **Automatic Updates**: Version management via HACS
- **German Market Focus**: Primary support for DE region

#### Documentation
- **Bilingual README**: Complete German and English documentation (NEW)
- **Comprehensive CHANGELOG**: Full version history
- **Release Notes**: Detailed bilingual release notes (DE/EN) (NEW)
- **Example Configurations**: Sample JSON files for quick start (NEW)
- **Contributing Guidelines**: Community contribution guide (NEW)
- **Deployment Guide**: Complete deployment instructions (NEW)
- **MIT License**: Open source license (from v0.1.0)

### Changed
- Enhanced device_tracker platform with person tracking logic
- Enhanced sensor platform with unknown/guest client detection
- Updated manifest.json version to 1.0.0
- Improved coordinator with full UniFi API integration
- Extended configuration options

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



[Unreleased]: https://github.com/thelad-dev/unifi-people-pointer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v1.0.0
[0.1.0]: https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v0.1.0
