# Configuration / Konfiguration

**[🇩🇪 Deutsch](#de)** | **[🇬🇧 English](#en)**

---

<a name="de"></a>
## 🇩🇪 Konfiguration (Deutsch)

### Übersicht

Die Integration speichert Host, API-Token und SSL-Verify im Config Entry (UI-Setup). JSON-Dateien beschreiben Geräte/Personen; `.env` dient lokalen API-Tests und Doku-Beispielen:

| Datei | Zweck | Versioniert |
|-------|-------|-------------|
| Config Entry (UI) | Host, Token, `verify_ssl`; Option `scan_interval` | HA-Storage |
| `devices.json` | Zu trackende Geräte definieren | ✅ Ja |
| `people.json` | Zuordnung Geräte → HA-Personen | ✅ Ja |
| `manufacturers.json` | IEEE OUI-Präfixe | ✅ Ja |
| `.env` | API-Token für lokale Tools/Beispiele | ❌ Nein (`.gitignore`) |

### 1. API-Zugriff (Config Flow und optional `.env`)

**In Home Assistant:** Integration hinzufügen und Host, API-Token sowie SSL-Prüfung eingeben. Der Token landet im Config Entry, nicht in `.env`.

**Für lokale curl-/Doku-Tests** eine `.env` im Repo anlegen:

```bash
# UniFi Network Integration API Token (nur lokale Tools)
unifi_api_token="your-api-token-here"

# Optional: Controller-Adresse (Standard: 192.168.88.1)
# unifi_controller_host="192.168.88.1"

# Optional: API-Port (Standard: 443)
# unifi_api_port="443"
```

**Token erstellen:**
1. UniFi Network Controller öffnen
2. Settings → Admins
3. Add Admin → Role: View Only
4. Generate API Token
5. Token im HA-Config-Flow eintragen (oder für Tools in `.env`)

**Beispiel `.env.example`:**
```bash
unifi_api_token="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

⚠️ **Sicherheit:** Niemals die `.env`-Datei committen!

### 2. Geräte definieren (`devices.json`)

Definiert alle zu trackenden WLAN-Geräte.

**Schema:**
```json
{
  "version": 1,
  "notes": ["Beschreibung der Datei"],
  "devices": [
    {
      "id": "eindeutige-id",
      "name": "Anzeigename",
      "type": "smartphone|tablet|wearable|laptop",
      "manufacturer_id": "apple|samsung|google|...",
      "mac": "aa:bb:cc:dd:ee:ff",
      "hostname_match": ["hostname-pattern"],
      "track": true,
      "notes": "Optionale Notizen"
    }
  ]
}
```

**Beispiel:**
```json
{
  "version": 1,
  "notes": ["Zu trackende Presence-Geräte aus UniFi Network"],
  "devices": [
    {
      "id": "iphone-max",
      "name": "iPhone-Max",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "1c:3c:78:b8:ae:b5",
      "hostname_match": ["iPhone-Max"],
      "track": true,
      "notes": "Primäres iPhone; OUI oft leer wegen Private Address"
    },
    {
      "id": "watch-1",
      "name": "Apple Watch",
      "type": "wearable",
      "manufacturer_id": "apple",
      "mac": "82:9c:1a:5e:d0:28",
      "hostname_match": ["Watch"],
      "track": true,
      "notes": "Private MAC, wechselt voraussichtlich"
    }
  ]
}
```

**Felder:**
- `id`: Eindeutige ID (für `people.json`-Referenz)
- `name`: Anzeigename in Home Assistant
- `type`: Gerätetyp (für Filterung/Gruppierung)
- `manufacturer_id`: Referenz auf `manufacturers.json` (oder `null`)
- `mac`: Aktuelle MAC-Adresse
- `hostname_match`: Array von Hostname-Patterns (wichtig für private MACs!)
- `track`: `true` = aktiv tracken, `false` = ignorieren
- `notes`: Optionale Dokumentation

**Private MAC-Adressen:**

iPhones und moderne Android-Geräte randomisieren ihre MAC-Adresse. Die Integration erkennt sie trotzdem via `hostname_match`:

```json
{
  "id": "iphone-jd",
  "mac": "1c:3c:78:b8:ae:b5",
  "hostname_match": ["iPhone-JD", "iPhone-JD.*"],
  "notes": "MAC wechselt, Hostname bleibt stabil"
}
```

### 3. Personen zuordnen (`people.json`)

Ordnet Geräte aus `devices.json` zu Home-Assistant-Personen.

**Schema:**
```json
{
  "version": 1,
  "notes": ["Zuordnung devices → HA persons"],
  "people": [
    {
      "id": "person-id",
      "name": "Name der Person",
      "ha_person": "person.entity_id",
      "device_ids": ["device-id-1", "device-id-2"],
      "notes": "Optionale Notizen"
    }
  ]
}
```

**Beispiel:**
```json
{
  "version": 1,
  "notes": ["Mehrere Geräte pro Person erlaubt"],
  "people": [
    {
      "id": "max",
      "name": "Max",
      "ha_person": "person.max",
      "device_ids": ["iphone-max", "watch-1"],
      "notes": "iPhone + Apple Watch"
    },
    {
      "id": "sarah",
      "name": "Sarah",
      "ha_person": "person.sarah",
      "device_ids": ["android-sarah"],
      "notes": null
    }
  ]
}
```

**Felder:**
- `id`: Eindeutige ID der Person
- `name`: Anzeigename
- `ha_person`: Entity-ID der Person in Home Assistant (`person.*`)
- `device_ids`: Array von `devices.json`-IDs
- `notes`: Optionale Dokumentation

**Multi-Device-Logik:**

Presence = **mindestens ein** getracktes Gerät ist online.

```json
{
  "id": "max",
  "device_ids": ["iphone-max", "watch-1", "laptop-max"]
}
```
→ Max ist "home", wenn iPhone **oder** Watch **oder** Laptop verbunden ist.

### 4. Hersteller-Datenbank (`manufacturers.json`)

IEEE OUI-Präfixe für Smartphone-Hersteller. **Normalerweise unverändert lassen.**

**Schema:**
```json
{
  "version": 1,
  "notes": ["IEEE OUI prefixes für Geräte-Matching"],
  "manufacturers": [
    {
      "id": "apple",
      "name": "Apple, Inc.",
      "oui_prefixes": ["00:03:93", "00:05:02", "00:0A:27", "..."]
    }
  ]
}
```

**Verwendung:**

Wenn `devices.json` ein Gerät mit `"manufacturer_id": "apple"` definiert, wird beim Matching auch gegen die OUI-Präfixe geprüft.

⚠️ **Hinweis:** Bei private MAC-Adressen ist das OUI oft leer → `hostname_match` verwenden!

### 5. Integration in Home Assistant

#### Entities

Die Integration erstellt automatisch:

1. **Device Tracker** für jede Person:
   ```yaml
   device_tracker.unifi_person_max
   device_tracker.unifi_person_sarah
   ```

2. **Binary Sensor** für jedes Gerät:
   ```yaml
   binary_sensor.unifi_device_iphone_max
   binary_sensor.unifi_device_watch_1
   ```

#### Automationen

**Beispiel: Willkommens-Nachricht**
```yaml
automation:
  - alias: "Willkommen Max"
    trigger:
      - platform: state
        entity_id: device_tracker.unifi_person_max
        to: "home"
    action:
      - service: notify.mobile_app
        data:
          message: "Willkommen zu Hause, Max!"
```

**Beispiel: Licht beim Verlassen aus**
```yaml
automation:
  - alias: "Niemand zu Hause → Licht aus"
    trigger:
      - platform: state
        entity_id: device_tracker.unifi_person_max
        to: "not_home"
      - platform: state
        entity_id: device_tracker.unifi_person_sarah
        to: "not_home"
    condition:
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
    action:
      - service: light.turn_off
        target:
          area_id: all
```

### 6. Erweiterte Konfiguration

#### Scan-Intervall anpassen

Standard: 45 Sekunden. In der Integration unter **Konfigurieren** (Options-Flow) als `scan_interval` setzen (10–600).

#### Debug-Logging aktivieren

In `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.unifi_people_pointer: debug
```

#### Mehrere UniFi-Sites

Unterstützung kommt in v0.2.0. Aktuell: eine Site (Standard-Site).

### 7. Validierung

**JSON-Syntax prüfen:**
```bash
python3 -m json.tool devices.json
python3 -m json.tool people.json
```

**API-Zugriff testen:**
```bash
set -a && source .env && set +a
curl -sk -H "X-API-KEY: $unifi_api_token" \
     -H "Accept: application/json" \
     "https://192.168.88.1/proxy/network/integration/v1/sites"
```

**Integration neu laden:**
Settings → Devices & Services → UniFi People Pointer → ⚙️ → Reload

---

<a name="en"></a>
## 🇬🇧 Configuration (English)

### Overview

The integration stores host, API token, and SSL verify in the config entry (UI setup). JSON files describe devices/people; `.env` is for local API tests and doc examples:

| File | Purpose | Version Controlled |
|------|---------|-------------------|
| Config entry (UI) | Host, token, `verify_ssl`; option `scan_interval` | HA storage |
| `devices.json` | Define devices to track | ✅ Yes |
| `people.json` | Map devices → HA persons | ✅ Yes |
| `manufacturers.json` | IEEE OUI prefixes | ✅ Yes |
| `.env` | API token for local tools/examples | ❌ No (`.gitignore`) |

### 1. API access (config flow and optional `.env`)

**In Home Assistant:** Add the integration and enter host, API token, and SSL verification. The token is stored in the config entry, not in `.env`.

**For local curl/doc tests**, create a `.env` in the repo:

```bash
# UniFi Network Integration API Token (local tools only)
unifi_api_token="your-api-token-here"

# Optional: Controller address (default: 192.168.88.1)
# unifi_controller_host="192.168.88.1"

# Optional: API port (default: 443)
# unifi_api_port="443"
```

**Create token:**
1. Open UniFi Network Controller
2. Settings → Admins
3. Add Admin → Role: View Only
4. Generate API Token
5. Enter the token in the HA config flow (or in `.env` for tools)

**Example `.env.example`:**
```bash
unifi_api_token="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

⚠️ **Security:** Never commit the `.env` file!

### 2. Define Devices (`devices.json`)

Defines all WiFi devices to track.

**Schema:**
```json
{
  "version": 1,
  "notes": ["File description"],
  "devices": [
    {
      "id": "unique-id",
      "name": "Display name",
      "type": "smartphone|tablet|wearable|laptop",
      "manufacturer_id": "apple|samsung|google|...",
      "mac": "aa:bb:cc:dd:ee:ff",
      "hostname_match": ["hostname-pattern"],
      "track": true,
      "notes": "Optional notes"
    }
  ]
}
```

**Example:**
```json
{
  "version": 1,
  "notes": ["Presence devices to track from UniFi Network"],
  "devices": [
    {
      "id": "iphone-max",
      "name": "iPhone-Max",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "1c:3c:78:b8:ae:b5",
      "hostname_match": ["iPhone-Max"],
      "track": true,
      "notes": "Primary iPhone; OUI often empty due to Private Address"
    },
    {
      "id": "watch-1",
      "name": "Apple Watch",
      "type": "wearable",
      "manufacturer_id": "apple",
      "mac": "82:9c:1a:5e:d0:28",
      "hostname_match": ["Watch"],
      "track": true,
      "notes": "Private MAC, expected to change"
    }
  ]
}
```

**Fields:**
- `id`: Unique ID (for `people.json` reference)
- `name`: Display name in Home Assistant
- `type`: Device type (for filtering/grouping)
- `manufacturer_id`: Reference to `manufacturers.json` (or `null`)
- `mac`: Current MAC address
- `hostname_match`: Array of hostname patterns (important for private MACs!)
- `track`: `true` = actively track, `false` = ignore
- `notes`: Optional documentation

**Private MAC Addresses:**

iPhones and modern Android devices randomize their MAC address. The integration still recognizes them via `hostname_match`:

```json
{
  "id": "iphone-jd",
  "mac": "1c:3c:78:b8:ae:b5",
  "hostname_match": ["iPhone-JD", "iPhone-JD.*"],
  "notes": "MAC changes, hostname stays stable"
}
```

### 3. Map Persons (`people.json`)

Maps devices from `devices.json` to Home Assistant persons.

**Schema:**
```json
{
  "version": 1,
  "notes": ["Mapping devices → HA persons"],
  "people": [
    {
      "id": "person-id",
      "name": "Person name",
      "ha_person": "person.entity_id",
      "device_ids": ["device-id-1", "device-id-2"],
      "notes": "Optional notes"
    }
  ]
}
```

**Example:**
```json
{
  "version": 1,
  "notes": ["Multiple devices per person allowed"],
  "people": [
    {
      "id": "max",
      "name": "Max",
      "ha_person": "person.max",
      "device_ids": ["iphone-max", "watch-1"],
      "notes": "iPhone + Apple Watch"
    },
    {
      "id": "sarah",
      "name": "Sarah",
      "ha_person": "person.sarah",
      "device_ids": ["android-sarah"],
      "notes": null
    }
  ]
}
```

**Fields:**
- `id`: Unique person ID
- `name`: Display name
- `ha_person`: Person entity ID in Home Assistant (`person.*`)
- `device_ids`: Array of `devices.json` IDs
- `notes`: Optional documentation

**Multi-Device Logic:**

Presence = **at least one** tracked device is online.

```json
{
  "id": "max",
  "device_ids": ["iphone-max", "watch-1", "laptop-max"]
}
```
→ Max is "home" if iPhone **or** Watch **or** Laptop is connected.

### 4. Manufacturer Database (`manufacturers.json`)

IEEE OUI prefixes for smartphone manufacturers. **Usually leave unchanged.**

**Schema:**
```json
{
  "version": 1,
  "notes": ["IEEE OUI prefixes for device matching"],
  "manufacturers": [
    {
      "id": "apple",
      "name": "Apple, Inc.",
      "oui_prefixes": ["00:03:93", "00:05:02", "00:0A:27", "..."]
    }
  ]
}
```

**Usage:**

When `devices.json` defines a device with `"manufacturer_id": "apple"`, matching also checks against OUI prefixes.

⚠️ **Note:** With private MAC addresses, OUI is often empty → use `hostname_match`!

### 5. Integration in Home Assistant

#### Entities

The integration automatically creates:

1. **Device Tracker** for each person:
   ```yaml
   device_tracker.unifi_person_max
   device_tracker.unifi_person_sarah
   ```

2. **Binary Sensor** for each device:
   ```yaml
   binary_sensor.unifi_device_iphone_max
   binary_sensor.unifi_device_watch_1
   ```

#### Automations

**Example: Welcome message**
```yaml
automation:
  - alias: "Welcome Max"
    trigger:
      - platform: state
        entity_id: device_tracker.unifi_person_max
        to: "home"
    action:
      - service: notify.mobile_app
        data:
          message: "Welcome home, Max!"
```

**Example: Lights off when leaving**
```yaml
automation:
  - alias: "Nobody home → Lights off"
    trigger:
      - platform: state
        entity_id: device_tracker.unifi_person_max
        to: "not_home"
      - platform: state
        entity_id: device_tracker.unifi_person_sarah
        to: "not_home"
    condition:
      - condition: state
        entity_id: device_tracker.unifi_person_max
        state: "not_home"
      - condition: state
        entity_id: device_tracker.unifi_person_sarah
        state: "not_home"
    action:
      - service: light.turn_off
        target:
          area_id: all
```

### 6. Advanced Configuration

#### Adjust scan interval

Default: 45 seconds. Set `scan_interval` (10–600) under the integration **Configure** options flow.

#### Enable debug logging

In `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.unifi_people_pointer: debug
```

#### Multiple UniFi Sites

Support coming in v0.2.0. Currently: one site (default site).

### 7. Validation

**Check JSON syntax:**
```bash
python3 -m json.tool devices.json
python3 -m json.tool people.json
```

**Test API access:**
```bash
set -a && source .env && set +a
curl -sk -H "X-API-KEY: $unifi_api_token" \
     -H "Accept: application/json" \
     "https://192.168.88.1/proxy/network/integration/v1/sites"
```

**Reload integration:**
Settings → Devices & Services → UniFi People Pointer → ⚙️ → Reload

---

**[⬆️ Back to README](../README.md)**
