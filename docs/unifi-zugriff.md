# UniFi-Zugriff

Stand der Ermittlung: August 2026. Controller: **Cloud Gateway Ultra** (`192.168.88.1`), UniFi Network auf dem Gerät selbst.

## 1. Integration API (bevorzugt)

### Voraussetzung

In UniFi OS unter **Settings → Control Plane → Integrations** einen API-Key mit Network-Zugriff anlegen und in `.env` speichern:

```bash
unifi_api_token="…"
```

Vorlage: `.env.example`. Die Datei `.env` ist per `.gitignore` ausgeschlossen.

### Auth

- Header: **`X-API-KEY: <token>`**
- `Authorization: Bearer …` funktioniert **nicht** (401)
- TLS: selbstsigniertes Zertifikat → Clients mit Verify-off bzw. eigenem CA-Handling

### Basis-URL

```text
https://192.168.88.1
```

Alias: `https://unifi` / `unifi.bost8.thelad.loc` zeigen auf dieselbe Gateway-IP.

### Site-ID

Der Pfad-Parameter ist **nicht** der String `default`, sondern die UUID aus dem Sites-Endpoint:

```bash
curl -sk -H "X-API-KEY: $TOKEN" -H "Accept: application/json" \
  "https://192.168.88.1/proxy/network/integration/v1/sites"
```

Beispielantwort (gekürzt):

```json
{
  "data": [
    {
      "id": "88f7af54-98f8-306a-a1c7-c9349722b1f6",
      "internalReference": "default",
      "name": "Default"
    }
  ]
}
```

### Nützliche Endpoints

| Zweck | Methode / Pfad |
|---|---|
| Sites | `GET /proxy/network/integration/v1/sites` |
| Clients | `GET /proxy/network/integration/v1/sites/{siteId}/clients` |
| Geräte (APs, Switches, Gateway) | `GET /proxy/network/integration/v1/sites/{siteId}/devices` |
| Live-Stationen (klassische API) | `GET /proxy/network/api/s/default/stat/sta` |

Die klassische `stat/sta`-Route akzeptiert denselben `X-API-KEY` und liefert die vollständigen Live-Client-Objekte (Hostname, `ap_mac`, RSSI, ESSID, …).

Beispiel Clients (Integration API):

```bash
SITE=88f7af54-98f8-306a-a1c7-c9349722b1f6
curl -sk -H "X-API-KEY: $TOKEN" -H "Accept: application/json" \
  "https://192.168.88.1/proxy/network/integration/v1/sites/${SITE}/clients?limit=100"
```

### Was schiefging

- Alter Token in `.env` → durchgängig **401 Unauthorized** (auch lokal auf dem Gateway gegen `127.0.0.1`).
- Integration-Pfade mit Literal `…/sites/default/clients` → **400** (`argument-type-mismatch`); Site-UUID verwenden.
- Token als Login-Passwort an `/api/auth/login` → **403** (kein Session-Login).

## 2. SSH auf das Gateway (`ssh ucg`)

SSH-Config-Eintrag (Auszug):

```text
Host ucg
  HostName 192.168.88.1
  User root
  IdentityFile ~/.ssh/id_rsa
```

Nach Login: Debian 11 auf dem UniFi-OS-Host, Services u. a. `unifi`, `unifi-mongodb`, `unifi-core`.

`mca-cli` auf dem Gateway bezieht sich nur auf das Gateway selbst (info/reboot/upgrade), nicht auf die APs.

## 3. MongoDB auf dem Gateway

UniFi MongoDB lauscht auf **`127.0.0.1:27117`** (nicht 27017).

```bash
ssh ucg
mongo --port 27117 ace --quiet --eval 'db.device.find({type:"uap"},{name:1,model:1,mac:1,ip:1}).forEach(printjson)'
```

| Collection | Nutzen |
|---|---|
| `ace.device` (`type: "uap"`) | AP-Inventar (Name, Modell, MAC, IP, `last_seen`) |
| `ace.user` | Bekannte Clients; Zuordnung über `last_uplink_mac` / `last_uplink_name` |
| `ace.api_key` | Metadaten angelegter Keys (Name, `admin_id`); **Geheimnis nicht gespeichert** |
| `ace.setting` (`key: "mgmt"`) | u. a. Site-SSH (`x_ssh_username`, `x_ssh_enabled`) |

Live-Assoziationen stehen **nicht** zuverlässig in `ace.user` (viele Einträge mit `disconnect_timestamp`). Für „gerade verbunden“ API oder `mca-dump` auf dem AP nutzen.

Lokale Network-HTTP-API ohne Login: `http://127.0.0.1:8081/api/s/default/stat/sta` → `api.err.LoginRequired`.

## 4. SSH auf die Access Points

Site-SSH ist aktiv (`x_ssh_username=ladwein`, Passwort-Auth und hinterlegter SSH-Key).

Von prodesk (Key `id_rsa`) oder vom Gateway (Site-Passwort via `sshpass`) erreichbar:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa \
  ladwein@192.168.88.33 mca-dump
```

Hinweis: Der alte **UAP-LR** (`AP-DG-Mitte`, `192.168.88.121`) bietet nur `ssh-rsa` / `ssh-dss` als Host-Key; moderne OpenSSH-Defaults brauchen die beiden `+ssh-rsa`-Optionen.

Hop vom Gateway auf alle APs mit Site-Passwort ist verifiziert (8/8).

## 5. Weitere Zugangswege

- **UniFi Network MCP** (`unifi_list_clients`, `unifi_list_devices`, …): bereits authentifiziert, gut für Ad-hoc-Abfragen.
- **Home Assistant MCP**: Personen-Entities (`person.ladwein`, `person.janine`, `person.android`) für `people.json`.

## Empfohlene Reihenfolge für Code

1. Token aus `.env` lesen.
2. Sites laden → `siteId` merken.
3. Live-Clients über Integration-API oder `stat/sta` holen.
4. Gegen `devices.json` / Hostname / OUI aus `manufacturers.json` matchen.
5. Presence an `people.json` → HA-`person.*` ableiten.

SSH/Mongo nur als Fallback oder für Diagnose auf dem AP.
