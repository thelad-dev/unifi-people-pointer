# Nachweis UniFi People Pointer (HA live)

Backup vor Eingriff: slug `1b8418db` (Name upp-ha-integration-20261014-pre)

## Entities
query: unifi_people
count: 8 of 8 total
entities[8]{entity_id,state,name}:
  update.unifi_people_pointer_update,off,UniFi People Pointer Update
  device_tracker.android_00a90b444cb7_2,home,android-00A90B444CB7
  device_tracker.iphone_jd_2,home,iPhone-JD
  device_tracker.iphone_skhl_2,home,iPhone-SKHL
  device_tracker.janine,home,Janine
  device_tracker.sebastian,home,Sebastian
  device_tracker.tablet,home,Tablet
  device_tracker.watch,home,Watch
help[1]: Run `ha-axi state get <entity_id>` for details

## device_tracker.janine
state:
  entity_id: device_tracker.janine
  state: home
  friendly_name: Janine
  last_changed: "2026-10-14T07:52:54.263876+00:00"
  last_updated: "2026-10-14T07:52:54.263876+00:00"
  attributes:
    tracking_type: position
    in_zones: []
    source_type: router
    person_id: janine
    ha_person: person.janine
    primary_device:
      mac: "1c:3c:78:b8:ae:b5"
      connected: true
    secondary_devices: []
    devices_online: 1
    online_device_ids[1]: iphone-jd
    source: unifi_people_pointer
    friendly_name: Janine
  attributes_truncated: null
  attributes_chars: null
help: null

## device_tracker.sebastian
state:
  entity_id: device_tracker.sebastian
  state: home
  friendly_name: Sebastian
  last_changed: "2026-10-14T07:52:54.263667+00:00"
  last_updated: "2026-10-14T07:52:54.263667+00:00"
  attributes:
    tracking_type: position
    in_zones: []
    source_type: router
    person_id: sebastian
    ha_person: person.ladwein
    primary_device:
      mac: "38:7f:8b:da:18:20"
      connected: true
    secondary_devices[1]{mac,connected}:
      "82:9c:1a:5e:d0:28",true
    devices_online: 2
    online_device_ids[2]: iphone-skhl,watch-1
    source: unifi_people_pointer
    friendly_name: Sebastian
  attributes_truncated: null
  attributes_chars: null
help: null

## Sensors
state:
  entity_id: sensor.unknown_wifi_clients
  state: "75"
  friendly_name: Unknown WiFi Clients
  last_changed: "2026-10-14T07:49:54.132323+00:00"
  last_updated: "2026-10-14T07:52:54.264710+00:00"
  attributes:
    friendly_name: Unknown WiFi Clients
    _more: "+1 more keys: clients"
  attributes_truncated: true
  attributes_chars: 14565
help[1]: Run `ha-axi state get sensor.unknown_wifi_clients --full` for complete attributes
state:
  entity_id: sensor.guest_wifi_clients
  state: "0"
  friendly_name: Guest WiFi Clients
  last_changed: "2026-10-14T07:48:29.849271+00:00"
  last_updated: "2026-10-14T07:48:29.849271+00:00"
  attributes:
    clients: []
    friendly_name: Guest WiFi Clients
  attributes_truncated: null
  attributes_chars: null
help: null

## Presence flip (home -> not_home -> home) via devices.json MAC patch + scan_now
Documented in task run 2026-10-14; janine flipped as expected.

## Browser
chrome-devtools-axi unavailable here (no Chrome/Chromium binary; CDP bridge BRIDGE_NOT_READY).
UI verification substituted with ha-axi entity/state dumps above.
