# UniFi People Pointer 🎯

[🇩🇪 Deutsch](#deutsch) | [🇬🇧 English](#english)

---

## Deutsch

### UniFi People Pointer - Personenbasierte Anwesenheitserkennung für Home Assistant

UniFi People Pointer ist eine fortschrittliche Home Assistant Integration, die Personen statt einzelner Geräte trackt. Die Integration nutzt dein UniFi Netzwerk um intelligente Anwesenheitserkennung zu ermöglichen, selbst bei Geräten mit privaten/randomisierten MAC-Adressen.

#### ✨ Hauptfunktionen

- **Personenbasiertes Tracking**: Verfolge Menschen, nicht Geräte
- **Multi-Device Support**: Eine Person kann mehrere Geräte (Smartphone, Laptop, Tablet, etc.) haben
- **Private MAC Adressen**: Unterstützt iOS/Android Geräte mit wechselnden MAC-Adressen
- **UniFi Native**: Direkte Integration mit UniFi Controller API
- **Intelligente Events**: Automatische Benachrichtigungen bei Ankommen/Verlassen
- **Unbekannte Geräte**: Warnung bei neuen Geräten im Netzwerk
- **HACS**: Installation als Custom Repository (noch nicht im HACS Default Store)
- **Access Points**: Tracker zeigen den AP, an dem ein Gerät hängt, z. B. `Phone AP: Living-Room`
- **Web-UI**: Wird mit der Integration installiert, Seitenleisten-Eintrag "People Pointer"

#### 🚀 Installation

Ausführliche Anleitung: [docs/installation.md](docs/installation.md)

##### Via HACS (empfohlen) – Custom Repository

Die Integration ist **nicht** im HACS Default Store. Suche allein findet sie nicht.

1. Öffne HACS in Home Assistant
2. Gehe zu **Integrationen**
3. ⋮-Menü (oben rechts) → **Custom repositories**
4. Repository hinzufügen:
   - **URL:** `https://github.com/thelad-dev/unifi-people-pointer`
   - **Kategorie:** Integration
5. **Add** → Integration herunterladen (**Download**)
6. Home Assistant neu starten

Hinweis: Frühere 404-Fehler beim Hinzufügen lagen oft am damals privaten Repo. Das Repo ist jetzt öffentlich.

##### Manuell

1. Lade die neueste Version von [Releases](https://github.com/thelad-dev/unifi-people-pointer/releases) bzw. als ZIP vom Repo herunter
2. Kopiere den Ordner `custom_components/unifi_people_pointer/` nach `/config/custom_components/unifi_people_pointer/`
3. Starte Home Assistant neu

#### ⚙️ Konfiguration

1. Gehe zu **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Suche nach "UniFi People Pointer"
3. Gib deine UniFi Controller Details ein:
   - **Host**: IP oder Hostname, z.B. `192.168.1.1` (IPv6 ohne Klammern; die Integration setzt sie in der URL)
   - **API-Token**: Erstelle einen unter Einstellungen → Admins → API Token
   - **SSL-Zertifikat prüfen**: Standard aus (lokales UniFi-Zertifikat); nur bei gültigem Zertifikat einschalten

4. Optional unter **Optionen konfigurieren**:
   - **Scan-Intervall**: Wie oft nach Geräten gesucht wird (Standard: 45s, Bereich 10–600)

#### 📱 Personen & Geräte einrichten

Die Integration speichert Konfiguration in JSON-Dateien unter `/config/unifi_people_pointer/`:

**people.json** - Definiere Personen:
```json
{
  "version": 1,
  "people": [
    {
      "id": "sebastian",
      "name": "Sebastian",
      "ha_person": "person.sebastian",
      "device_ids": ["iphone-sebastian", "macbook-sebastian"]
    }
  ]
}
```

**devices.json** - Geräte mit MAC und optionalem Hostname-Match (exact/Substring, kein Regex):
```json
{
  "version": 1,
  "devices": [
    {
      "id": "iphone-sebastian",
      "name": "Sebastian iPhone",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "aa:bb:cc:dd:ee:ff",
      "hostname_match": ["iPhone-Sebastian"],
      "track": true
    },
    {
      "id": "macbook-sebastian",
      "name": "Sebastian MacBook",
      "type": "laptop",
      "manufacturer_id": "apple",
      "mac": "11:22:33:44:55:66",
      "hostname_match": ["MacBook-Sebastian"],
      "track": true
    }
  ]
}
```

#### 🎯 Services

Die Integration bietet folgende Services:

- `unifi_people_pointer.assign_device` - Gerät einer Person zuweisen (exklusiv: entfernt die Kennung bei jeder anderen Person; aktualisiert Presence und Tracker ohne Reload)
- `unifi_people_pointer.track_device` - Neues Gerät tracken (aktualisiert Presence und Tracker ohne Reload)
- `unifi_people_pointer.remove_device` - Gerät entfernen (aktualisiert Presence und Tracker ohne Reload)
- `unifi_people_pointer.scan_now` - Sofortiges Netzwerk-Scan
- `unifi_people_pointer.claim_unknown_device` - Unbekanntes Gerät beanspruchen (exklusiv wie assign; aktualisiert Presence und Tracker ohne Reload)

Manuelle Änderungen an `people.json` / `devices.json` greift der nächste Poll auf (kein Config-Entry-Reload nötig). Entity-IDs folgen dem Anzeigenamen, z. B. `device_tracker.sebastian`, `device_tracker.iphone_sebastian`, plus `sensor.unknown_wifi_clients` / `sensor.guest_wifi_clients`. Templates: `states()` / `state_attr()` auf diesen Entities - siehe [docs/examples.md](docs/examples.md).

#### 📊 Events

- `unifi_people_pointer_person_arrived` - Person angekommen
- `unifi_people_pointer_person_left` - Person gegangen
- `unifi_people_pointer_device_connected` - Gerät verbunden
- `unifi_people_pointer_unknown_device` - Unbekanntes Gerät entdeckt

#### 📶 Access-Point-Namen

Solange ein Gerät verbunden ist, heißt sein Tracker `<Name> AP: <AP-Name>` (z. B. `Phone AP: Living-Room`), der Personen-Tracker zeigt den AP des ersten verbundenen Geräts. Der AP-Name kommt aus der UniFi-Geräteliste und folgt beim Roaming mit dem nächsten Poll. Zusätzlich gibt es das Attribut `ap_name` (Tracker und je Client in den Unknown-/Guest-Sensoren). Die Entity-IDs bleiben unverändert; ein in HA vergebener eigener Anzeigename ersetzt den Zusatz.

#### 🔧 Web-UI

Die Web-UI ist Teil der Integration, eine Zusatzinstallation gibt es nicht. Sie startet mit dem Config-Entry, lauscht auf `0.0.0.0` (Standardport `8765`, änderbar unter Optionen) und erscheint für Admins als Seitenleisten-Eintrag **People Pointer**; auf der Integrationsseite führt der Link **Besuchen** am Gerät "UniFi People Pointer" dorthin. Sie bietet Übersicht, Personen, Geräte, unbekannte Clients (beanspruchen) und Access Points. Jede API-Anfrage braucht das HA-Token eines Admins (im Panel automatisch, direkt aufgerufen ein Long-Lived Token). Ist der Port belegt, erscheint ein Hinweis unter Reparaturen. Details: [docs/installation.md](docs/installation.md#web-ui).

#### 📋 Anforderungen

- Home Assistant 2024.1.0 oder höher
- UniFi Network Controller (Dream Machine, Cloud Key, selbst-gehostet)
- Python 3.11+

#### 🆘 Support

- [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- [Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)

#### 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details

---

## English

### UniFi People Pointer - Person-based Presence Detection for Home Assistant

UniFi People Pointer is an advanced Home Assistant integration that tracks people instead of individual devices. The integration uses your UniFi network to enable intelligent presence detection, even with devices using private/randomized MAC addresses.

#### ✨ Key Features

- **Person-based Tracking**: Track people, not devices
- **Multi-Device Support**: One person can have multiple devices (smartphone, laptop, tablet, etc.)
- **Private MAC Addresses**: Supports iOS/Android devices with rotating MAC addresses
- **UniFi Native**: Direct integration with UniFi Controller API
- **Smart Events**: Automatic notifications for arrivals/departures
- **Unknown Devices**: Alerts for new devices on the network
- **HACS**: Install via custom repository (not yet in the HACS default store)
- **Access points**: Trackers show the AP a device is connected to, e.g. `Phone AP: Living-Room`
- **Web UI**: Installed with the integration, sidebar entry "People Pointer"

#### 🚀 Installation

Full guide: [docs/installation.md](docs/installation.md)

##### Via HACS (recommended) – custom repository

This integration is **not** in the HACS default store. Searching alone will not find it.

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. ⋮ menu (top right) → **Custom repositories**
4. Add repository:
   - **URL:** `https://github.com/thelad-dev/unifi-people-pointer`
   - **Category:** Integration
5. **Add** → download the integration (**Download**)
6. Restart Home Assistant

Note: Earlier 404 errors when adding the repository were often caused by the repo being private. The repository is now public.

##### Manual

1. Download the latest version from [Releases](https://github.com/thelad-dev/unifi-people-pointer/releases) or as a ZIP from the repo
2. Copy the folder `custom_components/unifi_people_pointer/` to `/config/custom_components/unifi_people_pointer/`
3. Restart Home Assistant

#### ⚙️ Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "UniFi People Pointer"
3. Enter your UniFi Controller details:
   - **Host**: IP or hostname, e.g. `192.168.1.1` (IPv6 without brackets; the integration adds them in the URL)
   - **API token**: Create one under Settings → Admins → API Token
   - **Verify SSL certificate**: Off by default (local UniFi certificate); enable only with a valid certificate

4. Optionally under **Configure**:
   - **Scan interval**: How often to scan for devices (default: 45s, range 10–600)

#### 📱 Setting up People & Devices

The integration stores configuration in JSON files under `/config/unifi_people_pointer/`:

**people.json** - Define people:
```json
{
  "version": 1,
  "people": [
    {
      "id": "sebastian",
      "name": "Sebastian",
      "ha_person": "person.sebastian",
      "device_ids": ["iphone-sebastian", "macbook-sebastian"]
    }
  ]
}
```

**devices.json** - Devices with MAC and optional hostname match (exact/substring, not regex):
```json
{
  "version": 1,
  "devices": [
    {
      "id": "iphone-sebastian",
      "name": "Sebastian iPhone",
      "type": "smartphone",
      "manufacturer_id": "apple",
      "mac": "aa:bb:cc:dd:ee:ff",
      "hostname_match": ["iPhone-Sebastian"],
      "track": true
    },
    {
      "id": "macbook-sebastian",
      "name": "Sebastian MacBook",
      "type": "laptop",
      "manufacturer_id": "apple",
      "mac": "11:22:33:44:55:66",
      "hostname_match": ["MacBook-Sebastian"],
      "track": true
    }
  ]
}
```

#### 🎯 Services

The integration provides these services:

- `unifi_people_pointer.assign_device` - Assign device to person (exclusive: detaches the id from every other person; refreshes presence and trackers without reload)
- `unifi_people_pointer.track_device` - Track new device (refreshes presence and trackers without reload)
- `unifi_people_pointer.remove_device` - Remove device (refreshes presence and trackers without reload)
- `unifi_people_pointer.scan_now` - Immediate network scan
- `unifi_people_pointer.claim_unknown_device` - Claim unknown device (exclusive like assign; refreshes presence and trackers without reload)

Manual edits to `people.json` / `devices.json` are picked up on the next poll (no config-entry reload required). Entity IDs follow the display name, e.g. `device_tracker.sebastian`, `device_tracker.iphone_sebastian`, plus `sensor.unknown_wifi_clients` / `sensor.guest_wifi_clients`. Templates: `states()` / `state_attr()` on those entities - see [docs/examples.md](docs/examples.md).

#### 📊 Events

- `unifi_people_pointer_person_arrived` - Person arrived
- `unifi_people_pointer_person_left` - Person left
- `unifi_people_pointer_device_connected` - Device connected
- `unifi_people_pointer_unknown_device` - Unknown device detected

#### 📶 Access point names

While a device is connected its tracker is named `<name> AP: <AP name>` (e.g. `Phone AP: Living-Room`); person trackers show the AP of their first connected device. The AP name comes from the UniFi device list and follows roaming on the next poll. The `ap_name` attribute is also set (trackers, and per client in the unknown/guest sensors). Entity ids do not change; a custom name set in HA replaces the suffix.

#### 🔧 Web UI

The web UI ships with the integration; there is nothing extra to install. It starts with the config entry, listens on `0.0.0.0` (default port `8765`, configurable in the options) and shows up for admins as the sidebar entry **People Pointer**; on the integration page the **Visit** link on the "UniFi People Pointer" device leads there. It offers an overview, persons, devices, unknown clients (claim) and access points. Every API request needs an admin's Home Assistant token (handed over automatically inside the panel, a long-lived token when opened directly). If the port is taken, a repair issue says so. Details: [docs/installation.md](docs/installation.md#web-ui-1).

#### 📋 Requirements

- Home Assistant 2024.1.0 or higher
- UniFi Network Controller (Dream Machine, Cloud Key, self-hosted)
- Python 3.11+

#### 🆘 Support

- [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- [Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)

#### 📄 License

MIT License - see [LICENSE](LICENSE) for details
