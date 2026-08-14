# UniFi People Pointer v1.0.0 🎉

[🇩🇪 Deutsch](#deutsch) | [🇬🇧 English](#english)

---

## Deutsch

### 🎯 Erste stabile Version!

Wir freuen uns, die erste stabile Version von **UniFi People Pointer** zu veröffentlichen - eine intelligente Home Assistant Integration für personenbasierte Anwesenheitserkennung über UniFi Netzwerke!

#### Was ist UniFi People Pointer?

UniFi People Pointer löst ein häufiges Problem in Smart Homes: **Menschen haben mehrere Geräte**, und moderne Smartphones wechseln ständig ihre MAC-Adressen aus Datenschutzgründen. Statt jedes Gerät einzeln zu tracken, verfolgt diese Integration **die Person** - unabhängig davon, welches Gerät sie gerade nutzt.

#### 🌟 Hauptmerkmale

##### Intelligentes Personen-Tracking
- **Multi-Device Support**: Ordne mehrere Geräte (Smartphone, Tablet, Laptop) einer Person zu
- **Private MAC-Adressen**: Funktioniert auch mit iOS/Android Geräten die ihre MAC wechseln
- **Primäre & Sekundäre Geräte**: Flexibles Device-Assignment System
- **Hostname-Matching**: Erkennt Geräte auch wenn die MAC wechselt

##### UniFi Native Integration
- **Direkte API-Anbindung**: Nutzt die UniFi Controller API (aiounifi)
- **Echtzeit-Updates**: Schnelle Reaktion auf Netzwerkänderungen
- **Alle UniFi Controller**: Unterstützt Dream Machine, Cloud Key, selbst-gehostete Controller
- **Kein SSH nötig**: Reine API-Kommunikation

##### Home Assistant First
- **Config Flow**: Einfache Einrichtung über die UI
- **Device Tracker**: Personen-Entities für Präsenzerkennung
- **Sensoren**: Zusätzliche Metriken und Status-Informationen
- **6 Services**: Vollständige Kontrolle über Geräte und Personen
- **4 Event-Typen**: Für intelligente Automationen

##### Intelligente Features
- **Grace Period**: Verhindert falsches "Abwesenheit" bei kurzen Verbindungsabbrüchen
- **Mobile App Fallback**: Nutzt die HA Mobile App als Backup
- **Ping Fallback**: ICMP Ping zur zusätzlichen Verifizierung
- **Event Debouncing**: Verhindert Spam bei wechselnden Verbindungen
- **Unbekannte Geräte**: Warnung bei neuen Geräten im Netzwerk

##### HACS & Erweiterbarkeit
- **HACS Ready**: Installation mit einem Klick
- **Web-UI**: Optionales Management-Interface (Backend enthalten)
- **JSON-Konfiguration**: Einfach zu editieren und zu versionieren
- **OUI-Datenbank**: Automatische Hersteller-Erkennung

#### 📦 Was ist enthalten?

- **Home Assistant Custom Component** (`custom_components/unifi_people_pointer/`)
  - Config Flow für einfache Einrichtung
  - Device Tracker & Sensor Platforms
  - 6 Services für Device/Person Management
  - Event System für Automationen
  - OUI Database Support

- **Web-Backend (Optional)** (`backend/`)
  - Express.js REST API
  - WebSocket für Live-Updates
  - Home Assistant Integration
  - Device & Person Management UI
  - OUI Database Management

- **HACS Support**
  - `hacs.json` für HACS Integration
  - Automatische Updates
  - Versionsverwaltung

- **Dokumentation**
  - Vollständige DE/EN README
  - Detailliertes CHANGELOG
  - Service & Event Referenz
  - Konfigurations-Beispiele

#### 🚀 Schnellstart

1. **Installation via HACS**
   ```
   HACS → Integrationen → + → "UniFi People Pointer" suchen → Installieren
   ```

2. **Integration hinzufügen**
   ```
   Einstellungen → Geräte & Dienste → Integration hinzufügen → "UniFi People Pointer"
   ```

3. **UniFi Controller verbinden**
   - URL: `https://192.168.1.1:8443` (deine Controller-Adresse)
   - API Key: Erstelle einen unter Einstellungen → Admins → API Token
   - Site ID: `default` (oder deine Site)

4. **Personen konfigurieren**
   Bearbeite `/config/unifi_people_pointer/people.json`:
   ```json
   {
     "max": {
       "name": "Max Mustermann",
       "devices": {
         "primary": ["AA:BB:CC:DD:EE:FF"],
         "secondary": ["11:22:33:44:55:66"]
       }
     }
   }
   ```

5. **Erste Automation**
   ```yaml
   automation:
     - alias: "Max ist zuhause"
       trigger:
         - platform: event
           event_type: unifi_people_pointer_person_arrived
           event_data:
             person: max
       action:
         - service: notify.mobile_app
           data:
             message: "Willkommen zuhause, Max!"
   ```

#### 🔧 Anforderungen

- **Home Assistant**: 2024.1.0 oder höher
- **UniFi Controller**: Dream Machine, Cloud Key, oder selbst-gehostet
- **Python**: 3.11+ (in HA enthalten)
- **Netzwerkzugriff**: HA muss den UniFi Controller erreichen können

#### 📝 Bekannte Einschränkungen

- Device Tracker & Sensor Platform Implementierung in Arbeit (werden in v1.1.0 ergänzt)
- Web-UI ist optional und erfordert separate Installation
- OUI Auto-Update benötigt Internet-Zugang

#### 🆘 Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- **Diskussionen**: [GitHub Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)
- **Feature Requests**: Gerne über Issues einreichen!

#### 🙏 Danke!

Ein großes Dankeschön an alle Early Adopters und Tester! Euer Feedback hat diese Version möglich gemacht.

#### 📅 Was kommt als nächstes?

**v1.1.0** (geplant):
- Device Tracker Platform Implementierung
- Sensor Platform mit erweiterten Metriken
- Frontend Web-UI (React/Vue)
- Docker Compose für Web-Stack
- Erweiterte Zone-Unterstützung
- Bluetooth Fallback

---

## English

### 🎯 First Stable Release!

We're excited to announce the first stable version of **UniFi People Pointer** - an intelligent Home Assistant integration for person-based presence detection via UniFi networks!

#### What is UniFi People Pointer?

UniFi People Pointer solves a common smart home problem: **people have multiple devices**, and modern smartphones constantly change their MAC addresses for privacy. Instead of tracking each device individually, this integration tracks **the person** - regardless of which device they're currently using.

#### 🌟 Key Features

##### Intelligent Person Tracking
- **Multi-Device Support**: Assign multiple devices (smartphone, tablet, laptop) to one person
- **Private MAC Addresses**: Works with iOS/Android devices that rotate their MAC
- **Primary & Secondary Devices**: Flexible device assignment system
- **Hostname Matching**: Recognizes devices even when MAC changes

##### UniFi Native Integration
- **Direct API Integration**: Uses UniFi Controller API (aiounifi)
- **Real-time Updates**: Fast reaction to network changes
- **All UniFi Controllers**: Supports Dream Machine, Cloud Key, self-hosted controllers
- **No SSH Required**: Pure API communication

##### Home Assistant First
- **Config Flow**: Easy setup via UI
- **Device Tracker**: Person entities for presence detection
- **Sensors**: Additional metrics and status information
- **6 Services**: Full control over devices and people
- **4 Event Types**: For intelligent automations

##### Smart Features
- **Grace Period**: Prevents false "away" status during brief disconnects
- **Mobile App Fallback**: Uses HA Mobile App as backup
- **Ping Fallback**: ICMP ping for additional verification
- **Event Debouncing**: Prevents spam during connection changes
- **Unknown Devices**: Alert for new devices on network

##### HACS & Extensibility
- **HACS Ready**: One-click installation
- **Web UI**: Optional management interface (backend included)
- **JSON Configuration**: Easy to edit and version
- **OUI Database**: Automatic manufacturer detection

#### 📦 What's Included?

- **Home Assistant Custom Component** (`custom_components/unifi_people_pointer/`)
  - Config Flow for easy setup
  - Device Tracker & Sensor Platforms
  - 6 Services for device/person management
  - Event system for automations
  - OUI database support

- **Web Backend (Optional)** (`backend/`)
  - Express.js REST API
  - WebSocket for live updates
  - Home Assistant integration
  - Device & person management UI
  - OUI database management

- **HACS Support**
  - `hacs.json` for HACS integration
  - Automatic updates
  - Version management

- **Documentation**
  - Complete DE/EN README
  - Detailed CHANGELOG
  - Service & event reference
  - Configuration examples

#### 🚀 Quick Start

1. **Install via HACS**
   ```
   HACS → Integrations → + → Search "UniFi People Pointer" → Install
   ```

2. **Add Integration**
   ```
   Settings → Devices & Services → Add Integration → "UniFi People Pointer"
   ```

3. **Connect UniFi Controller**
   - URL: `https://192.168.1.1:8443` (your controller address)
   - API Key: Create one under Settings → Admins → API Token
   - Site ID: `default` (or your site)

4. **Configure People**
   Edit `/config/unifi_people_pointer/people.json`:
   ```json
   {
     "john": {
       "name": "John Doe",
       "devices": {
         "primary": ["AA:BB:CC:DD:EE:FF"],
         "secondary": ["11:22:33:44:55:66"]
       }
     }
   }
   ```

5. **First Automation**
   ```yaml
   automation:
     - alias: "John is home"
       trigger:
         - platform: event
           event_type: unifi_people_pointer_person_arrived
           event_data:
             person: john
       action:
         - service: notify.mobile_app
           data:
             message: "Welcome home, John!"
   ```

#### 🔧 Requirements

- **Home Assistant**: 2024.1.0 or higher
- **UniFi Controller**: Dream Machine, Cloud Key, or self-hosted
- **Python**: 3.11+ (included in HA)
- **Network Access**: HA must be able to reach UniFi Controller

#### 📝 Known Limitations

- Device Tracker & Sensor platform implementation in progress (coming in v1.1.0)
- Web UI is optional and requires separate installation
- OUI auto-update requires internet access

#### 🆘 Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)
- **Feature Requests**: Please submit via Issues!

#### 🙏 Thank You!

A huge thank you to all early adopters and testers! Your feedback made this version possible.

#### 📅 What's Next?

**v1.1.0** (planned):
- Device Tracker platform implementation
- Sensor platform with extended metrics
- Frontend Web UI (React/Vue)
- Docker Compose for web stack
- Extended zone support
- Bluetooth fallback

---

## Installation

### Via HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click `+` and search for "UniFi People Pointer"
4. Click "Install"
5. Restart Home Assistant

### Manual Installation
1. Download `unifi-people-pointer-v1.0.0.zip` from this release
2. Extract `custom_components/unifi_people_pointer` to your HA config directory
3. Restart Home Assistant

## Upgrading
- **From v0.x**: This is the first stable release, no upgrade path needed
- **HACS**: Will auto-update when available in HACS default repository

## Full Changelog
See [CHANGELOG.md](https://github.com/thelad-dev/unifi-people-pointer/blob/main/CHANGELOG.md) for complete details.

## Assets
- `Source code (zip)` - Full source code
- `Source code (tar.gz)` - Full source code
