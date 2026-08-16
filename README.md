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
- **Web-UI**: Optionales Web-Interface zur Verwaltung (in Entwicklung)

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
   - **SSL-Zertifikat prüfen**: Standard an; bei selbstsignierten Zertifikaten aus

4. Optional unter **Optionen konfigurieren**:
   - **Scan-Intervall**: Wie oft nach Geräten gesucht wird (Standard: 45s, Bereich 10–600)

#### 📱 Personen & Geräte einrichten

Die Integration speichert Konfiguration in JSON-Dateien unter `/config/unifi_people_pointer/`:

**people.json** - Definiere Personen:
```json
{
  "sebastian": {
    "name": "Sebastian",
    "icon": "mdi:account",
    "devices": {
      "primary": ["AA:BB:CC:DD:EE:FF"],
      "secondary": ["11:22:33:44:55:66", "77:88:99:AA:BB:CC"]
    }
  }
}
```

**devices.json** - Verknüpfe Geräte mit Hostnamen (für private MACs):
```json
{
  "AA:BB:CC:DD:EE:FF": {
    "name": "Sebastian iPhone",
    "hostname_pattern": "sebastians?-iphone",
    "type": "smartphone",
    "manufacturer": "Apple"
  }
}
```

#### 🎯 Services

Die Integration bietet folgende Services:

- `unifi_people_pointer.assign_device` - Gerät einer Person zuweisen
- `unifi_people_pointer.track_device` - Neues Gerät tracken
- `unifi_people_pointer.remove_device` - Gerät entfernen
- `unifi_people_pointer.scan_now` - Sofortiges Netzwerk-Scan
- `unifi_people_pointer.claim_unknown_device` - Unbekanntes Gerät beanspruchen

#### 📊 Events

- `unifi_people_pointer_person_arrived` - Person angekommen
- `unifi_people_pointer_person_left` - Person gegangen
- `unifi_people_pointer_device_connected` - Gerät verbunden
- `unifi_people_pointer_unknown_device` - Unbekanntes Gerät entdeckt

#### 🔧 Web-UI (Optional)

Das Projekt enthält ein optionales Web-Interface zur einfacheren Verwaltung:

```bash
cd backend
npm install
npm run dev
```

Das Interface läuft auf `http://localhost:3000` und bietet:
- Personen & Geräte Verwaltung
- Zonen-Konfiguration (Access Points)
- OUI Datenbank Management
- Live UniFi Client Monitoring

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
- **Web UI**: Optional web interface for management (in development)

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
   - **Verify SSL certificate**: On by default; turn off for self-signed certificates

4. Optionally under **Configure**:
   - **Scan interval**: How often to scan for devices (default: 45s, range 10–600)

#### 📱 Setting up People & Devices

The integration stores configuration in JSON files under `/config/unifi_people_pointer/`:

**people.json** - Define people:
```json
{
  "sebastian": {
    "name": "Sebastian",
    "icon": "mdi:account",
    "devices": {
      "primary": ["AA:BB:CC:DD:EE:FF"],
      "secondary": ["11:22:33:44:55:66", "77:88:99:AA:BB:CC"]
    }
  }
}
```

**devices.json** - Link devices with hostnames (for private MACs):
```json
{
  "AA:BB:CC:DD:EE:FF": {
    "name": "Sebastian iPhone",
    "hostname_pattern": "sebastians?-iphone",
    "type": "smartphone",
    "manufacturer": "Apple"
  }
}
```

#### 🎯 Services

The integration provides these services:

- `unifi_people_pointer.assign_device` - Assign device to person
- `unifi_people_pointer.track_device` - Track new device
- `unifi_people_pointer.remove_device` - Remove device
- `unifi_people_pointer.scan_now` - Immediate network scan
- `unifi_people_pointer.claim_unknown_device` - Claim unknown device

#### 📊 Events

- `unifi_people_pointer_person_arrived` - Person arrived
- `unifi_people_pointer_person_left` - Person left
- `unifi_people_pointer_device_connected` - Device connected
- `unifi_people_pointer_unknown_device` - Unknown device detected

#### 🔧 Web UI (Optional)

The project includes an optional web interface for easier management:

```bash
cd backend
npm install
npm run dev
```

The interface runs on `http://localhost:3000` and offers:
- People & Device Management
- Zone Configuration (Access Points)
- OUI Database Management
- Live UniFi Client Monitoring

#### 📋 Requirements

- Home Assistant 2024.1.0 or higher
- UniFi Network Controller (Dream Machine, Cloud Key, self-hosted)
- Python 3.11+

#### 🆘 Support

- [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- [Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)

#### 📄 License

MIT License - see [LICENSE](LICENSE) for details
