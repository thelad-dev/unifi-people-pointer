# UniFi People Pointer

Track **people**, not devices! 🎯

## Why UniFi People Pointer?

Modern smartphones change their MAC addresses for privacy (iOS 14+, Android 10+). Traditional device trackers fail when your phone gets a new random MAC every few hours.

**UniFi People Pointer solves this** by tracking the *person* through multiple devices and using hostname matching to handle MAC rotation.

## Key Features

✅ **Person-based tracking** - One person, multiple devices  
✅ **Private MAC support** - Works with randomized MAC addresses  
✅ **UniFi native** - Direct integration with UniFi Controller API  
✅ **Smart events** - Arrival/departure automations  
✅ **Unknown device alerts** - Get notified about new devices  
✅ **HACS ready** - Easy installation and updates  

## Quick Start

1. **Install** via HACS or manually
2. **Add Integration** in Home Assistant
3. **Connect** your UniFi Controller
4. **Configure** people in `/config/unifi_people_pointer/people.json`
5. **Automate** with events and services!

## Example Automation

```yaml
automation:
  - alias: "Welcome Home"
    trigger:
      - platform: event
        event_type: unifi_people_pointer_person_arrived
        event_data:
          person: john
    action:
      - service: light.turn_on
        target:
          entity_id: light.entrance
      - service: notify.mobile_app
        data:
          message: "Welcome home, John!"
```

## Services

- `assign_device` - Assign device to person
- `track_device` - Start tracking a device
- `remove_device` - Remove device
- `scan_now` - Trigger immediate scan
- `claim_unknown_device` - Claim unknown device

## Requirements

- Home Assistant 2024.1.0+
- UniFi Network Controller
- API access to controller

## Support

- [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- [Documentation](https://github.com/thelad-dev/unifi-people-pointer)
- [Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)

---

**Made with ❤️ for the Home Assistant community**
