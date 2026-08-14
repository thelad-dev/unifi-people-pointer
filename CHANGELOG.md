# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- HACS integration support via `hacs.json`
- Bilingual README (German/English) with language switcher
- Comprehensive documentation structure in `docs/`
- Configuration examples for devices, people, and manufacturers
- UniFi API integration documentation
- Support for private/randomized MAC addresses via hostname matching

### Documentation
- Installation guide (HACS and manual)
- Configuration reference
- Example automations and use cases
- UniFi access methods (API, SSH, MongoDB)
- Access points and client tracking guide
- Data model and match logic explanation

## [0.1.0] - TBD

### Added
- Initial release
- UniFi Network Integration API support
- Multi-device person tracking
- Private MAC address handling
- JSON-based configuration
- IEEE OUI manufacturer database
- Device tracker entities
- Binary sensor for presence

### Requirements
- Home Assistant 2024.1.0+
- UniFi Network Controller
- Python 3.11+

---

[Unreleased]: https://github.com/thelad-dev/unifi-people-pointer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thelad-dev/unifi-people-pointer/releases/tag/v0.1.0
