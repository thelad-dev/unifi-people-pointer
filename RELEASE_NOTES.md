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

---

## Installation

### Via HACS
1. Add custom repository in HACS
2. Search for "UniFi People Pointer"
3. Install and restart Home Assistant

### Manual
1. Download from [Releases](https://github.com/thelad-dev/unifi-people-pointer/releases)
2. Extract to `/config/custom_components/unifi_people_pointer`
3. Restart Home Assistant

## Full Changelog

See [CHANGELOG.md](https://github.com/thelad-dev/unifi-people-pointer/blob/main/CHANGELOG.md)
