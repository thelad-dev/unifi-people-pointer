# Examples / Beispiele

**[🇩🇪 Deutsch](#de)** | **[🇬🇧 English](#en)**

---

<a name="de"></a>
## 🇩🇪 Beispiele (Deutsch)

### Beispiel-Konfigurationen

#### 1. Einfache Familie (2 Personen)

**devices.json:**
```json
{
  "version": 1,
  "devices": [
    {
      "id": "iphone-max",
      "name": "iPhone-Max",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "1c:3c:78:b8:ae:b5",
      "hostname_match": ["iPhone-Max"],
      "track": true
    },
    {
      "id": "android-sarah",
      "name": "Samsung-Sarah",
      "type": "smartphone",
      "manufacturer_id": "samsung",
      "mac": "50:32:75:15:c9:68",
      "hostname_match": ["android-.*sarah.*"],
      "track": true
    }
  ]
}
```

**people.json:**
```json
{
  "version": 1,
  "people": [
    {
      "id": "max",
      "name": "Max",
      "ha_person": "person.max",
      "device_ids": ["iphone-max"]
    },
    {
      "id": "sarah",
      "name": "Sarah",
      "ha_person": "person.sarah",
      "device_ids": ["android-sarah"]
    }
  ]
}
```

#### 2. Multi-Device Setup (Smartphone + Smartwatch)

**devices.json:**
```json
{
  "version": 1,
  "devices": [
    {
      "id": "iphone-max",
      "name": "iPhone-Max",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "1c:3c:78:b8:ae:b5",
      "hostname_match": ["iPhone-Max"],
      "track": true
    },
    {
      "id": "watch-max",
      "name": "Apple-Watch-Max",
      "type": "wearable",
      "manufacturer_id": "apple",
      "mac": "82:9c:1a:5e:d0:28",
      "hostname_match": ["Watch"],
      "track": true,
      "notes": "Private MAC, kann sich ändern"
    },
    {
      "id": "laptop-max",
      "name": "MacBook-Max",
      "type": "laptop",
      "manufacturer_id": "apple",
      "mac": "a4:83:e7:12:34:56",
      "hostname_match": ["MacBook-Max"],
      "track": true
    }
  ]
}
```

**people.json:**
```json
{
  "version": 1,
  "people": [
    {
      "id": "max",
      "name": "Max",
      "ha_person": "person.max",
      "device_ids": ["iphone-max", "watch-max", "laptop-max"],
      "notes": "Home wenn mindestens ein Gerät verbunden"
    }
  ]
}
```

#### 3. WG / Shared Living (mehrere Personen)

**devices.json:**
```json
{
  "version": 1,
  "devices": [
    {"id": "phone-max", "name": "iPhone-Max", "type": "smartphone", 
     "manufacturer_id": "apple", "mac": "1c:3c:78:b8:ae:b5", 
     "hostname_match": ["iPhone-Max"], "track": true},
    
    {"id": "phone-sarah", "name": "Samsung-Sarah", "type": "smartphone",
     "manufacturer_id": "samsung", "mac": "50:32:75:15:c9:68",
     "hostname_match": ["android-.*sarah.*"], "track": true},
    
    {"id": "phone-lisa", "name": "Pixel-Lisa", "type": "smartphone",
     "manufacturer_id": "google", "mac": "d4:f5:47:8a:b2:c1",
     "hostname_match": ["Pixel.*Lisa"], "track": true},
    
    {"id": "tablet-shared", "name": "Tablet-Wohnzimmer", "type": "tablet",
     "manufacturer_id": "samsung", "mac": "ac:5a:fc:12:34:56",
     "hostname_match": ["Galaxy-Tab"], "track": false,
     "notes": "Shared device, nicht für Presence"}
  ]
}
```

**people.json:**
```json
{
  "version": 1,
  "people": [
    {"id": "max", "name": "Max", "ha_person": "person.max", 
     "device_ids": ["phone-max"]},
    {"id": "sarah", "name": "Sarah", "ha_person": "person.sarah",
     "device_ids": ["phone-sarah"]},
    {"id": "lisa", "name": "Lisa", "ha_person": "person.lisa",
     "device_ids": ["phone-lisa"]}
  ]
}
```

### Automations-Beispiele

#### 1. Willkommensnachricht

```yaml
automation:
  - alias: "Willkommen zu Hause"
    description: "Begrüßung wenn Person nach Hause kommt"
    trigger:
      - platform: state
        entity_id: 
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "home"
    action:
      - service: notify.mobile_app_{{ trigger.to_state.attributes.friendly_name | lower }}
        data:
          message: "Willkommen zu Hause, {{ trigger.to_state.attributes.friendly_name }}!"
          title: "🏠 Zuhause"
```

#### 2. Licht einschalten beim Heimkommen (nur abends)

```yaml
automation:
  - alias: "Licht an beim Heimkommen"
    description: "Schaltet Licht ein wenn jemand nach 18 Uhr nach Hause kommt"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "home"
    condition:
      - condition: time
        after: "18:00:00"
        before: "23:59:59"
      - condition: state
        entity_id: sun.sun
        state: "below_horizon"
    action:
      - service: light.turn_on
        target:
          entity_id: light.wohnzimmer
        data:
          brightness_pct: 70
          color_temp: 370
```

#### 3. Heizung runterdrehen wenn niemand da ist

```yaml
automation:
  - alias: "Heizung Eco-Modus"
    description: "Heizung auf Eco wenn alle weg sind"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
        for: "00:15:00"  # 15 Minuten Verzögerung
    condition:
      # Alle Personen müssen weg sein
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.wohnzimmer
        data:
          preset_mode: "eco"
```

#### 4. Heizung normal wenn erste Person heimkommt

```yaml
automation:
  - alias: "Heizung Normal-Modus"
    description: "Heizung auf Normal wenn erste Person heimkommt"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "home"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.wohnzimmer
        data:
          preset_mode: "comfort"
```

#### 5. Alarmanlage scharf wenn alle weg

```yaml
automation:
  - alias: "Alarm scharf schalten"
    description: "Aktiviert Alarm wenn alle das Haus verlassen"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
        for: "00:05:00"  # 5 Minuten Verzögerung
    condition:
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
      # Nur wenn Alarm nicht bereits aktiv
      - condition: state
        entity_id: alarm_control_panel.home
        state: "disarmed"
    action:
      - service: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.home
      - service: notify.mobile_app
        data:
          message: "Alarmanlage wurde aktiviert."
          title: "🔒 Sicherheit"
```

#### 6. Benachrichtigung wenn Kinder nach Hause kommen

```yaml
automation:
  - alias: "Kind ist zu Hause"
    description: "Benachrichtigung an Eltern wenn Kind heimkommt"
    trigger:
      - platform: state
        entity_id: device_tracker.unifi_person_lisa
        to: "home"
    condition:
      # Nur wenn Eltern nicht zu Hause
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
      # Nur während Schulzeit (werktags, 13-17 Uhr)
      - condition: time
        after: "13:00:00"
        before: "17:00:00"
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: notify.mobile_app_max
        data:
          message: "Lisa ist zu Hause angekommen."
          title: "🏠 Kinder-Tracking"
```

#### 7. Staubsauger-Roboter starten

```yaml
automation:
  - alias: "Staubsauger wenn alle weg"
    description: "Startet Staubsauger 30 Min nachdem alle weg sind"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
        for: "00:30:00"  # 30 Minuten warten
    condition:
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
      # Nur wochentags
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
      # Zwischen 9-17 Uhr
      - condition: time
        after: "09:00:00"
        before: "17:00:00"
    action:
      - service: vacuum.start
        target:
          entity_id: vacuum.roboter
```

### Dashboard-Karten

#### 1. Presence-Übersicht

```yaml
type: entities
title: 🏠 Anwesenheit
entities:
  - entity: device_tracker.unifi_person_max
    name: Max
    icon: mdi:account
  - entity: device_tracker.unifi_person_sarah
    name: Sarah
    icon: mdi:account
  - entity: device_tracker.unifi_person_lisa
    name: Lisa
    icon: mdi:account-child
  - type: divider
  - entity: binary_sensor.unifi_device_iphone_max
    name: iPhone Max
    icon: mdi:cellphone
  - entity: binary_sensor.unifi_device_watch_max
    name: Watch Max
    icon: mdi:watch
```

#### 2. Bedingte Karte (nur wenn jemand da)

```yaml
type: conditional
conditions:
  - entity: device_tracker.unifi_person_max
    state: "home"
card:
  type: markdown
  content: |
    ## 👋 Willkommen, Max!
    
    Du bist seit {{ relative_time(states.device_tracker.unifi_person_max.last_changed) }} zu Hause.
```

#### 3. Glance Card

```yaml
type: glance
title: Wer ist zu Hause?
entities:
  - entity: device_tracker.unifi_person_max
    name: Max
  - entity: device_tracker.unifi_person_sarah
    name: Sarah
  - entity: device_tracker.unifi_person_lisa
    name: Lisa
show_name: true
show_state: true
```

### Erweiterte Szenarien

#### 1. Gast-Modus

Geräte von Gästen temporär tracken ohne `people.json` zu ändern:

```yaml
# input_boolean für Gast-Modus
input_boolean:
  guest_mode:
    name: Gast-Modus aktiv
    icon: mdi:account-multiple

# Automation: Licht nicht ausschalten wenn Gast-Modus
automation:
  - alias: "Licht-Steuerung mit Gast-Modus"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
    condition:
      # Beide Bewohner weg
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
      # Aber KEIN Gast-Modus
      - condition: state
        entity_id: input_boolean.guest_mode
        state: "off"
    action:
      - service: light.turn_off
        target:
          area_id: all
```

#### 2. Zonen-basiertes Presence-Tracking

Kombiniere UniFi People Pointer mit HA-Zonen:

```yaml
automation:
  - alias: "Max im Büro angekommen"
    trigger:
      - platform: zone
        entity_id: device_tracker.unifi_person_max
        zone: zone.office
        event: enter
    action:
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.max_at_office
      - service: climate.set_preset_mode
        target:
          entity_id: climate.home
        data:
          preset_mode: "eco"
```

---

<a name="en"></a>
## 🇬🇧 Examples (English)

### Example Configurations

#### 1. Simple Family (2 people)

**devices.json:**
```json
{
  "version": 1,
  "devices": [
    {
      "id": "iphone-max",
      "name": "iPhone-Max",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "1c:3c:78:b8:ae:b5",
      "hostname_match": ["iPhone-Max"],
      "track": true
    },
    {
      "id": "android-sarah",
      "name": "Samsung-Sarah",
      "type": "smartphone",
      "manufacturer_id": "samsung",
      "mac": "50:32:75:15:c9:68",
      "hostname_match": ["android-.*sarah.*"],
      "track": true
    }
  ]
}
```

**people.json:**
```json
{
  "version": 1,
  "people": [
    {
      "id": "max",
      "name": "Max",
      "ha_person": "person.max",
      "device_ids": ["iphone-max"]
    },
    {
      "id": "sarah",
      "name": "Sarah",
      "ha_person": "person.sarah",
      "device_ids": ["android-sarah"]
    }
  ]
}
```

#### 2. Multi-Device Setup (Smartphone + Smartwatch)

**devices.json:**
```json
{
  "version": 1,
  "devices": [
    {
      "id": "iphone-max",
      "name": "iPhone-Max",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "1c:3c:78:b8:ae:b5",
      "hostname_match": ["iPhone-Max"],
      "track": true
    },
    {
      "id": "watch-max",
      "name": "Apple-Watch-Max",
      "type": "wearable",
      "manufacturer_id": "apple",
      "mac": "82:9c:1a:5e:d0:28",
      "hostname_match": ["Watch"],
      "track": true,
      "notes": "Private MAC, may change"
    },
    {
      "id": "laptop-max",
      "name": "MacBook-Max",
      "type": "laptop",
      "manufacturer_id": "apple",
      "mac": "a4:83:e7:12:34:56",
      "hostname_match": ["MacBook-Max"],
      "track": true
    }
  ]
}
```

**people.json:**
```json
{
  "version": 1,
  "people": [
    {
      "id": "max",
      "name": "Max",
      "ha_person": "person.max",
      "device_ids": ["iphone-max", "watch-max", "laptop-max"],
      "notes": "Home when at least one device is connected"
    }
  ]
}
```

### Automation Examples

#### 1. Welcome Message

```yaml
automation:
  - alias: "Welcome Home"
    description: "Greeting when person arrives home"
    trigger:
      - platform: state
        entity_id: 
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "home"
    action:
      - service: notify.mobile_app_{{ trigger.to_state.attributes.friendly_name | lower }}
        data:
          message: "Welcome home, {{ trigger.to_state.attributes.friendly_name }}!"
          title: "🏠 Home"
```

#### 2. Turn on Lights When Arriving (Evening Only)

```yaml
automation:
  - alias: "Lights On When Arriving"
    description: "Turn on lights when someone comes home after 6 PM"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "home"
    condition:
      - condition: time
        after: "18:00:00"
        before: "23:59:59"
      - condition: state
        entity_id: sun.sun
        state: "below_horizon"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 70
          color_temp: 370
```

#### 3. Lower Heating When Nobody Home

```yaml
automation:
  - alias: "Heating Eco Mode"
    description: "Set heating to eco when everyone is away"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
        for: "00:15:00"  # 15 minutes delay
    condition:
      # Everyone must be away
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.living_room
        data:
          preset_mode: "eco"
```

#### 4. Arm Alarm When Everyone Leaves

```yaml
automation:
  - alias: "Arm Alarm"
    description: "Activate alarm when everyone leaves the house"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
        for: "00:05:00"  # 5 minutes delay
    condition:
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
      # Only if alarm is not already active
      - condition: state
        entity_id: alarm_control_panel.home
        state: "disarmed"
    action:
      - service: alarm_control_panel.alarm_arm_away
        target:
          entity_id: alarm_control_panel.home
      - service: notify.mobile_app
        data:
          message: "Alarm system has been activated."
          title: "🔒 Security"
```

#### 5. Start Vacuum Robot

```yaml
automation:
  - alias: "Vacuum When Away"
    description: "Start vacuum 30 min after everyone leaves"
    trigger:
      - platform: state
        entity_id:
          - device_tracker.unifi_person_max
          - device_tracker.unifi_person_sarah
        to: "not_home"
        for: "00:30:00"  # Wait 30 minutes
    condition:
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
      # Only weekdays
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
      # Between 9 AM - 5 PM
      - condition: time
        after: "09:00:00"
        before: "17:00:00"
    action:
      - service: vacuum.start
        target:
          entity_id: vacuum.robot
```

### Dashboard Cards

#### 1. Presence Overview

```yaml
type: entities
title: 🏠 Presence
entities:
  - entity: device_tracker.unifi_person_max
    name: Max
    icon: mdi:account
  - entity: device_tracker.unifi_person_sarah
    name: Sarah
    icon: mdi:account
  - type: divider
  - entity: binary_sensor.unifi_device_iphone_max
    name: iPhone Max
    icon: mdi:cellphone
  - entity: binary_sensor.unifi_device_watch_max
    name: Watch Max
    icon: mdi:watch
```

#### 2. Conditional Card (Only When Someone Home)

```yaml
type: conditional
conditions:
  - entity: device_tracker.unifi_person_max
    state: "home"
card:
  type: markdown
  content: |
    ## 👋 Welcome, Max!
    
    You've been home for {{ relative_time(states.device_tracker.unifi_person_max.last_changed) }}.
```

---

**[⬆️ Back to README](../README.md)**
