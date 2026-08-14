# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TBD

## [1.0.0] - 2026-08-15

### 🎉 Initial Release

#### Core Features
- **Person-based Tracking**: Track people instead of individual devices
- **Multi-device Support**: Assign multiple devices (primary/secondary) to each person
- **Private MAC Support**: Handle iOS/Android devices with randomized MAC addresses via hostname matching
- **UniFi Native Integration**: Direct integration with UniFi Controller API (aiounifi)
- **Intelligent Presence Detection**: Grace periods and fallback mechanisms

#### Home Assistant Integration
- **Config Flow**: Guided setup through Home Assistant UI
- **Device Tracker Entities**: Track presence per person
- **Sensor Entities**: Additional metrics and statistics
- **Services**: 6 services for device/person management
  - `assign_device`: Assign device to person
  - `track_device`: Start tracking a new device
  - `remove_device`: Remove device from tracking
  - `scan_now`: Trigger immediate scan
  - `force_update_person`: Force person state update
  - `claim_unknown_device`: Claim and assign unknown device
- **Events**: Real-time events for automation
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

#### Web UI (Optional)
- **Management Backend**: Express.js API server for advanced management
- **REST API**: Endpoints for people, devices, zones, and settings
- **WebSocket**: Real-time client updates
- **Home Assistant Integration**: Direct HA API integration for live state

#### HACS Support
- **HACS Compatible**: Ready for Home Assistant Community Store
- **Automatic Updates**: Version management via HACS
- **German Market Focus**: Primary support for DE region

#### Documentation
- **Bilingual README**: Complete German and English documentation
- **Installation Guides**: HACS and manual installation
- **Configuration Examples**: Sample JSON files for quick start
- **Service Documentation**: Detailed service parameter reference
- **Event Documentation**: Event data structure and usage examples

### Requirements
- Home Assistant 2024.1.0+
- UniFi Network Controller
- Python 3.11+

---

[Unreleased]: https://github.com/thelad-dev/unifi-people-pointer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v1.0.0
