# Dokumentation

Presence-Tracking über UniFi-WLAN und Zuordnung zu Home-Assistant-Personen.

## Inhalt

| Datei | Thema |
|---|---|
| [unifi-zugriff.md](unifi-zugriff.md) | SSH, MongoDB, REST/Integration-API, Auth |
| [access-points-und-clients.md](access-points-und-clients.md) | APs auflisten, Clients pro AP, Live- vs. Historie |
| [datenmodell.md](datenmodell.md) | `manufacturers.json`, `devices.json`, `people.json` |

## Kurzüberblick

1. **Schnellster Weg zu Live-Daten:** UniFi Network Integration API mit `X-API-KEY` aus `.env` (`unifi_api_token`).
2. **Fallback ohne API:** `ssh ucg` → MongoDB für AP-Inventar; Hop auf die APs → `mca-dump` für Live-Stationen.
3. **Zuordnung:** Geräte in `devices.json`, Personen/HA-Entities in `people.json`, OUI-Filter in `manufacturers.json`.

Gateway im Heimnetz: Cloud Gateway Ultra unter `192.168.88.1` (SSH-Host `ucg`, DNS `unifi.bost8.thelad.loc`).
