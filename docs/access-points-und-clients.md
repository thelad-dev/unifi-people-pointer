# Access Points und Clients

## Access Points (Inventar)

Ermittelt über MongoDB `ace.device` (`type: "uap"`) und bestätigt über Integration-API `…/devices` sowie `mca-dump`.

Zum Zeitpunkt der Ermittlung **8 APs**, alle online:

| Name | Modell (Anzeige) | IP | MAC |
|---|---|---|---|
| AP-DG-Fenster | UAP-AC-LR | 192.168.88.248 | 80:2a:a8:13:a8:d0 |
| AP-DG-Mitte | UAP-LR | 192.168.88.121 | 04:18:d6:ac:ec:b7 |
| AP-EG-Absteller | UAP-AC-InWall | 192.168.88.204 | 68:d7:9a:76:78:da |
| AP-EG-Diele | UAP-HD | 192.168.88.33 | 74:ac:b9:4e:dd:a7 |
| AP-EG-Garage | UAP-AC-Lite | 192.168.88.201 | 24:5a:4c:20:07:ff |
| AP-EG-Whz | UAP-AC-InWall-Pro | 192.168.88.247 | 78:8a:20:86:bd:a3 |
| AP-KG-Büro | U6-LR | 192.168.88.173 | 1c:6a:1b:55:dc:b7 |
| AP-KG-Kidsfenster | UAP-AC-InWall-Pro | 192.168.88.249 | 78:8a:20:86:b7:d1 |

Zusätzlich am Controller: Gateway (`udm`-Typ) und mehrere Switches (`usw`). Integration-API meldete insgesamt 15 Netzwerk-Geräte.

## Clients pro Access Point

### Live (zuverlässig)

**Option A – API:** Feld `ap_mac` (klassische `stat/sta`) bzw. `uplinkDeviceId` (Integration-API) dem AP zuordnen.

**Option B – direkt am AP:**

```bash
ssh ladwein@<ap-ip> mca-dump
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
| iPhone-JD | `1c:3c:78:b8:ae:b5` | Janine; OUI matcht Apple trotz leerem UniFi-`oui` |
| iPhone-JD-alt | `14:2d:4d:af:08:80` | Apple OUI; ältere/alternative MAC |
| iPhone-SKHL | `38:7f:8b:da:18:20` | Sebastian |
| iPhone | `02:a2:54:a8:e1:98` | privat/randomisiert; lange offline |
| android-00A90B444CB7 | `00:a9:0b:44:4c:b7` | oft auf SSID `helgas-` |
| android-33a750c3d3271b06 | `50:32:75:15:c9:68` | Samsung OUI |
| Watch | `82:9c:1a:5e:d0:28` u. a. | private MACs; Hostname `Watch`, UniFi-Fingerprint Apple Watch |

Hostname `Watch` trifft auch Fehltreffer (z. B. Babycam mit Hostname „Watch“) – Presence-Logik sollte Fingerprint/`dev_cat` oder explizite MAC-Whitelist nutzen.

## Private Wi-Fi Address

Viele iPhones/Watches setzen lokal verwaltete MACs (zweites Hex-Nibble ungerade: `2`/`6`/`A`/`E`). Dann:

- kein stabiler Hersteller-OUI in UniFi,
- MAC kann nach Netzwerk-/Datenschutz-Reset wechseln,
- **Hostname** und explizite Einträge in `devices.json` sind robuster als reines OUI-Matching.

## SSIDs

In `mca-dump` erscheinen manche ESSID-Felder als Hex-ASCII (z. B. `6675636B796F75`). Vor Anzeige ggf. als Hex dekodieren, wenn nur Hex-Zeichen und gerade Länge. IoT-SSID u. a. `iot-bost8`, Gäste/Nebennetze getrennt.

## Praxis-Checkliste

1. APs online? → Integration `devices` oder Mongo `type:uap` + frisches `last_seen`.
2. Wer hängt wo? → `stat/sta` nach `ap_mac` gruppieren **oder** `mca-dump` pro AP.
3. Presence-Kandidaten? → Hostname/Fingerprint filtern, gegen `devices.json` legen, OUI nur als Zusatzsignal.
