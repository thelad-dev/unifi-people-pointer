# Datenmodell

Repo-Root enthält drei JSON-Dateien für Filter, Tracking und HA-Zuordnung.

## `manufacturers.json`

IEEE-OUI-Präfixe (MA-L, erste 3 Bytes) gängiger Smartphone-/Tablet-/Wearable-Hersteller.

| Feld | Bedeutung |
|---|---|
| `source` | `https://standards-oui.ieee.org/oui/oui.csv` |
| `manufacturers[].id` | Stabiler Schlüssel (`apple`, `samsung`, …) |
| `manufacturers[].oui_prefixes` | Liste `aa:bb:cc` (lowercase) |
| `manufacturers[].ieee_assignment_names` | Originalnamen aus der IEEE-Datei |

Erzeugt durch Filtern der IEEE-CSV nach Organization Name (Apple, Samsung, Google, Xiaomi, Huawei, Honor, OnePlus, OPPO, vivo, realme, Sony, Motorola, Nokia/HMD, Fairphone, Nothing, ASUS, LG, ZTE, Lenovo, Microsoft).

**Größe:** ca. 140 KB / mehrere tausend Präfixe (allein Apple und Huawei sehr viele Blöcke).

Nutzen: Grober Vorfilter „könnte Smartphone-Vendor sein“. Reicht allein nicht für Presence (viele IoT-Geräte teilen Vendor-Räume nicht, Phones randomisieren oft).

## `devices.json`

Whitelist der zu trackenden Geräte.

| Feld | Bedeutung |
|---|---|
| `id` | Stabiler Geräte-Schlüssel (Referenz aus `people.json`) |
| `mac` | Bekannte WLAN-MAC |
| `hostname_match` | Hostnamen aus UniFi zum Wiedererkennen |
| `manufacturer_id` | Verweis auf `manufacturers.json` oder `null` |
| `type` | `smartphone` / `wearable` / … |
| `track` | `true` = aktiv für Presence |

Aktuelle Einträge (Auszug der Logik):

- Primäre iPhones: `iphone-jd`, `iphone-skhl`
- Alternative/ältere MAC: `iphone-jd-alt` (`track: true`), `iphone-legacy` (`track: false`)
- Android: `android-helgas` (`track: true`), `android-samsung` (`track: false` bis bestätigt)
- Watches: `watch-1` (`track: true`), `watch-2` (`track: false`)

## `people.json`

Zuordnung zu Home-Assistant-Person-Entities (Stand HA 2026.8, Location „Home“).

| Person | `ha_person` | Geräte-IDs |
|---|---|---|
| Sebastian | `person.ladwein` | `iphone-skhl`, `watch-1` |
| Janine | `person.janine` | `iphone-jd`, `iphone-jd-alt` |
| Tablet | `person.android` | `android-helgas`, `android-samsung` |

Presence-Regel (vorgeschlagen): Person „zu Hause“, wenn **mindestens ein** referenziertes Gerät mit `track: true` in UniFi als online gilt (MAC- oder Hostname-Match).

Watch-Zuordnung zu Sebastian ist geschätzt und sollte bei Bedarf korrigiert werden.

## Empfohlener Match-Algorithmus

1. Live-Client von der API holen.
2. MAC exakt gegen `devices.json` prüfen.
3. Sonst Hostname gegen `hostname_match` (Case-insensitive).
4. Optional: OUI-Präfix ∈ `manufacturers.json` nur als Hinweis / Discovery, nicht als alleinige Presence-Quelle.
5. Device-`id` → Person über `people.json` → HA-Entity aktualisieren.

## Umgebung

```bash
# .env (nicht committen)
unifi_api_token="…"
```

Siehe [unifi-zugriff.md](unifi-zugriff.md) für Auth und Endpoints.
