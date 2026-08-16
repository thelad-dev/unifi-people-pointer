# UniFi People Pointer

**Presence tracking via UniFi WiFi clients with mapping to Home Assistant persons.**

## Features

- 🎯 **Precise presence tracking** via UniFi Network Integration API
- 📱 **Multi-device support** – multiple devices per person
- 🔀 **Private MAC addresses** – recognizes devices despite randomized MACs via hostname
- 🏠 **Native HA integration** – direct mapping to `person.*` entities
- 🔧 **Flexible configuration** – JSON-based device and person management

## Quick Start

1. **Install** via HACS and restart Home Assistant
2. **Create API token** in UniFi Controller (Settings → Admins → Add Admin → View Only)
3. **Add integration** in Settings → Devices & Services with host, API token, and SSL verify
4. **Optionally** set scan interval under the integration options
5. **Edit `devices.json`** and `people.json` to define devices and persons (when those files are in use)

## Documentation

- [Installation Guide](https://github.com/thelad-dev/unifi-people-pointer/blob/main/docs/installation.md)
- [Configuration Reference](https://github.com/thelad-dev/unifi-people-pointer/blob/main/docs/configuration.md)
- [Examples & Automations](https://github.com/thelad-dev/unifi-people-pointer/blob/main/docs/examples.md)

## Support

- [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- [Changelog](https://github.com/thelad-dev/unifi-people-pointer/blob/main/CHANGELOG.md)

---

**Note:** This integration requires a UniFi Network Controller (Cloud Gateway Ultra, Dream Machine, etc.) with API access.
