# Access Points und Clients

## Access Points (Inventar)

Ermittelt über MongoDB `ace.device` (`type: "uap"`) und bestätigt über Integration-API `…/devices` sowie `mca-dump`.

Zum Zeitpunkt der Ermittlung **8 APs**, alle online:

| Name | Modell (Anzeige) | IP | MAC |
|---|---|---|---|
| AP-OG-West | UAP-AC-LR | 192.168.10.248 | 80:2a:a8:00:00:11 |
| AP-OG-Mitte | UAP-LR | 192.168.10.121 | 04:18:d6:00:00:12 |
| AP-EG-Kueche | UAP-AC-InWall | 192.168.10.204 | 68:d7:9a:00:00:13 |
| AP-EG-Flur | UAP-HD | 192.168.10.33 | 74:ac:b9:00:00:14 |
| AP-EG-Ost | UAP-AC-Lite | 192.168.10.201 | 24:5a:4c:00:00:15 |
| AP-EG-Wohnen | UAP-AC-InWall-Pro | 192.168.10.247 | 78:8a:20:00:00:16 |
| AP-UG-Buero | U6-LR | 192.168.10.173 | 1c:6a:1b:00:00:17 |
| AP-UG-West | UAP-AC-InWall-Pro | 192.168.10.249 | 78:8a:20:00:00:18 |

Zusätzlich am Controller: Gateway (`udm`-Typ) und mehrere Switches (`usw`). Integration-API meldete insgesamt 15 Netzwerk-Geräte.

## Clients pro Access Point

### Live (zuverlässig)

**Option A – API:** Feld `ap_mac` (klassische `stat/sta`) bzw. `uplinkDeviceId` (Integration-API) dem AP zuordnen.

**Option B – direkt am AP:**

```bash
ssh example@<ap-ip> mca-dump
```

Struktur:

- Top-Level hat bei neueren Firmware-Ständen oft **keine** globale `sta_table`.
- Stationen liegen unter **`vap_table[].sta_table`**.
- `vap_table[].num_sta` und `vap_table[].essid` / `radio` (`ng` = 2,4 GHz, `na` = 5 GHz) ergänzen die Sicht.

Beispielauswertung (Python-Skizze):

```python
data = json.loads(mca_dump_output)
for vap in data.get("vap_table") or []:
    essid = vap.get("essid")
    for sta in vap.get("sta_table") or []:
        print(data["mac"], essid, sta.get("hostname"), sta.get("mac"), sta.get("ip"), sta.get("rssi"))
```

Bei einem Snapshot lagen **82** Live-WLAN-Stationen verteilt über die 8 APs (IoT-lastig; Phone/Watch nur ein kleiner Teil).

### Historie (Mongo `ace.user`)

- Letzte Zuordnung: `last_uplink_mac`, `last_uplink_name`, `last_radio`.
- Nicht gleichbedeutend mit „gerade verbunden“: oft gesetztes `disconnect_timestamp`.
- `oui` ist bei Private Wi-Fi Address häufig leer; Hostname/`dev_*`-Fingerprint bleiben nutzbar.

## Erkannte Smartphones / Watches (für Presence)

Aus API/MCP-Suchen (`iphone`, `android`, `watch`) und Live-`stat/sta`:

| Hostname | MAC | Bemerkung |
|---|---|---|
| iPhone-AN | `1c:3c:78:00:00:01` | Amelie; OUI matcht Apple trotz leerem UniFi-`oui` |
| iPhone-AN-alt | `14:2d:4d:00:00:07` | Apple OUI; ältere/alternative MAC |
| iPhone-RBKL | `38:7f:8b:00:00:02` | Christoph |
| iPhone | `02:00:00:00:00:04` | privat/randomisiert; lange offline |
| android-00A90B000006 | `00:a9:0b:00:00:06` | oft auf SSID `guests-` |
| android-0123456789abcdef | `50:32:75:00:00:05` | Samsung OUI |
| Watch | `82:00:00:00:00:03` u. a. | private MACs; Hostname `Watch`, UniFi-Fingerprint Apple Watch |

Hostname `Watch` trifft auch Fehltreffer (z. B. Babycam mit Hostname „Watch“) – Presence-Logik sollte Fingerprint/`dev_cat` oder explizite MAC-Whitelist nutzen.

## Private Wi-Fi Address

Viele iPhones/Watches setzen lokal verwaltete MACs (zweites Hex-Nibble ungerade: `2`/`6`/`A`/`E`). Dann:

- kein stabiler Hersteller-OUI in UniFi,
- MAC kann nach Netzwerk-/Datenschutz-Reset wechseln,
- **Hostname** und explizite Einträge in `devices.json` sind robuster als reines OUI-Matching.

## SSIDs

In `mca-dump` erscheinen manche ESSID-Felder als Hex-ASCII (z. B. `4E6574776F726B`). Vor Anzeige ggf. als Hex dekodieren, wenn nur Hex-Zeichen und gerade Länge. IoT-SSID u. a. `iot-home`, Gäste/Nebennetze getrennt.

## Praxis-Checkliste

1. APs online? → Integration `devices` oder Mongo `type:uap` + frisches `last_seen`.
2. Wer hängt wo? → `stat/sta` nach `ap_mac` gruppieren **oder** `mca-dump` pro AP.
3. Presence-Kandidaten? → Hostname/Fingerprint filtern, gegen `devices.json` legen, OUI nur als Zusatzsignal.
