# Installation / Installation

**[🇩🇪 Deutsch](#de)** | **[🇬🇧 English](#en)**

---

<a name="de"></a>
## 🇩🇪 Installation (Deutsch)

Die Integration ist **nicht** im HACS Default Store. Installation läuft über ein **Custom Repository** oder manuell.

### Methode 1: Installation über HACS (empfohlen)

1. **HACS öffnen** in Home Assistant
2. Zu **Integrationen** navigieren
3. Auf das **⋮-Menü** (oben rechts) klicken
4. **Custom repositories** auswählen
5. Repository hinzufügen:
   - **Repository:** `https://github.com/thelad-dev/unifi-people-pointer`
   - **Kategorie:** Integration
6. Auf **Add** klicken
7. **UniFi People Pointer** in der Liste der (Custom-)Integrationen finden
8. **Download** klicken
9. **Home Assistant neu starten**

Hinweis: Frühere 404-Fehler beim Hinzufügen des Repositories lagen oft am damals privaten Repo. Das Repository ist jetzt öffentlich.

### Methode 2: Manuelle Installation

1. **Aus dem Repository kopieren:**
   ```bash
   cd /tmp
   git clone https://github.com/thelad-dev/unifi-people-pointer.git
   cp -r unifi-people-pointer/custom_components/unifi_people_pointer \
         /config/custom_components/
   ```

2. **Oder ZIP / Release herunterladen:**
   - [Latest Release](https://github.com/thelad-dev/unifi-people-pointer/releases/latest) oder Repo-ZIP herunterladen
   - Den Ordner `custom_components/unifi_people_pointer/` nach `/config/custom_components/unifi_people_pointer/` kopieren

3. **Verzeichnisstruktur prüfen:**
   ```
   /config/
   └── custom_components/
       └── unifi_people_pointer/
           ├── __init__.py
           ├── manifest.json
           └── ...
   ```

4. **Home Assistant neu starten**

### Nach der Installation

1. **UniFi API-Token erstellen:**
   
   - UniFi Network Controller → Settings
   - Admins → Add Admin
   - Role: View Only
   - Generate API Token
   - Token kopieren

2. **Integration in HA hinzufügen:**
   
   - Settings → Devices & Services → **Add Integration**
   - "UniFi People Pointer" suchen
   - **Host** (IP oder Hostname), **API-Token**, **SSL-Zertifikat prüfen** eingeben
   - Optional unter Optionen: **Scan-Intervall** (Standard 45s)

3. **Personen & Geräte konfigurieren:**
   
   Siehe [configuration.md](configuration.md) für `devices.json` / `people.json`.  
   Für lokale API-Tests und Doku-Beispiele bleibt `.env` mit `unifi_api_token` nutzbar (nicht für den HA-Config-Flow).

### Web-UI

Die Web-UI liegt im Integrationsordner (`custom_components/unifi_people_pointer/webui/`) und kommt mit jeder HACS- oder manuellen Installation mit. Node, Docker oder ein Add-on sind nicht nötig.

- **Start:** mit dem Config-Entry, auch nach jedem HA-Neustart oder HACS-Update (nach dem Update HA neu starten).
- **Adresse:** lauscht auf `0.0.0.0`, Standardport `8765`. Den Port ändert man unter *Einstellungen → Geräte & Dienste → UniFi People Pointer → Konfigurieren*; die Integration lädt danach neu. Ist der Port belegt, erscheint ein Hinweis unter *Einstellungen → System → Reparaturen*; die Integration läuft ohne UI weiter.
- **Seitenleiste:** Eintrag **People Pointer** (nur Admins). Das Panel bettet `http://<Host, unter dem HA im Browser geöffnet ist>:<Port>/` ein und übergibt das HA-Token automatisch.
- **Integrationsseite:** das Gerät "UniFi People Pointer" hat den Link **Besuchen** zur UI; **Konfigurieren** bleibt der Optionen-Dialog.
- **HTTPS:** Wird HA per HTTPS geöffnet, bettet der Browser die HTTP-UI nicht ein (Mixed Content). Das Panel zeigt dann einen Link, der die UI in einem neuen Tab öffnet.
- **Direkt aufrufen:** `http://<HA-Host>:8765/` funktioniert mit einem Long-Lived Access Token (Profil → Sicherheit). Das Token muss einem Admin gehören.
- **Firewall:** Der Port muss vom Browser aus erreichbar sein (bei HA OS ohne weiteres im LAN).

### Grundriss

Reiter **Floor plan** der Web-UI.

- **Grundrisse:** unter **Edit → + Floor** ein Bild je Stockwerk hochladen (PNG, JPEG oder WebP, höchstens 15 MB, kein SVG). *Level* ordnet die Stockwerke (z. B. -1 Keller, 0 Erdgeschoss). *Width (m)* ist die echte Breite des Plans und bestimmt die Größe der Unsicherheitskreise; ohne Angabe gilt der Plan als 15 m breit. Bilder und Positionen liegen nur im HA-Config-Verzeichnis (`unifi_people_pointer/floorplans.json` und `unifi_people_pointer/floorplans/`) und werden nur mit Admin-Token ausgeliefert.
- **Access Points platzieren:** in der Liste *Access points* auf **Place** und dann auf die Stelle im Plan klicken; Marker lassen sich ziehen oder mit den Pfeiltasten verschieben. Die Position wird als Anteil der Bildbreite und -höhe gespeichert, ein ersetztes Bild behält die Punkte.
- **Import aus UniFi InnerSpace:** Die Grundrisse der UniFi-OS-App InnerSpace sind nur mit einer UniFi-OS-Sitzung lesbar, nicht mit dem API-Key. **Import from InnerSpace** meldet sich einmalig an, liest Grundrisse, AP-Positionen und Bilder und meldet sich wieder ab. Das Konto muss lokal sein, für InnerSpace die Rolle Admin haben und ohne Zwei-Faktor-Anmeldung auskommen. Benutzer und Passwort werden weder gespeichert noch geloggt. Stockwerke mit gleichem Namen werden ersetzt (Bild und Positionen ihrer APs), andere bleiben. Eine gedrehte Karte wird eingerechnet; den InnerSpace-Maßstab übernimmt der Import nur, wenn die Planbreite damit zwischen 4 und 80 m liegt.
- **Personen:** Marker sitzen am AP, an dem das erste verbundene Gerät der Person hängt; mehrere Personen am selben AP werden versetzt. Der Kreis ist eine grobe Schätzung aus dem Signal (stark: etwa 2 m, schwach: bis 15 m). Clients bleiben gern an einem AP hängen, auch durch Decken; das Stockwerk stimmt meist, aber nicht immer.
- **Datenschutz:** Ortung ist aus, bis sie unter **Edit → Privacy** eingeschaltet und die Person freigegeben ist. Erst dann liefert der Server ihre Position. Beim Löschen einer Person entfällt ihre Freigabe. Es wird kein Verlauf gespeichert und es gibt keine neuen Attribute mit Koordinaten in HA.
- **Heatmap:** Schalter **Heatmap** in der Ansicht. Jeder platzierte AP bekommt einen Farbfleck nach seiner Nutzung, die Farbskala reicht vom kühlsten bis zum meistgenutzten AP des ganzen Hauses (Stockwerke bleiben vergleichbar); die Liste daneben ordnet alle APs. Wählbar sind **Now** (letzter Poll), **1 h**, **24 h** und **7 d** sowie **Clients** (Durchschnitt der WLAN-Clients je Poll) oder **Data** (Datenmenge, geschätzt aus den Client-Raten, die UniFi bei jedem Poll meldet; bei *Now* die aktuelle Rate). *Data* gibt es nur, wenn UniFi Raten liefert (klassische Client-Liste); über die Integrations-API bleiben es Client-Zahlen. Ist ein Netzfilter gesetzt, zählen nur Clients aus den gewählten Netzen ([Konfiguration](configuration.md#netzfilter)).
- **Heatmap-Speicher:** nur Zähler je AP-MAC, keine Client-, Geräte- oder Personendaten: 5-Minuten-Schritte für 24 Stunden und Stundenschritte für 7 Tage, ältere Werte werden verworfen. Die Datei liegt in `.storage/unifi_people_pointer.ap_usage.<Eintrag>` und wird höchstens alle 5 Minuten geschrieben.
- **Genauigkeit:** UniFi meldet je Gerät nur den einen AP, an dem es hängt, mit dessen Signal; Trilateration geht damit nicht. Raumgenau wird es erst mit Bluetooth-Raumpräsenz (z. B. ESPHome-Bluetooth-Proxys mit Bermuda) als zusätzlicher Quelle.

### Systemvoraussetzungen

- **Home Assistant:** 2024.1.0 oder neuer
- **Python:** 3.11+
- **UniFi Controller:** Network Application 7.0+ (Cloud Gateway Ultra, Dream Machine, etc.)
- **Netzwerkzugriff:** Home Assistant → UniFi Controller (typisch `192.168.x.x`)

### Troubleshooting

#### Integration erscheint nicht in HACS

- Custom Repository zuerst hinzufügen (siehe oben); reine Suche im Default Store findet die Integration nicht
- HACS-Cache leeren: HACS → ⋮ → Reload HACS
- Repository-URL prüfen: `https://github.com/thelad-dev/unifi-people-pointer`
- Bei 404: Repo ist öffentlich; URL und Netzwerkzugriff prüfen
- HACS-Logs prüfen: Settings → System → Logs

#### API-Token funktioniert nicht

- Token-Format prüfen: `X-API-KEY` Header (nicht `Bearer`)
- Controller-IP prüfen (Standard: `192.168.10.1`)
- Firewall-Regeln prüfen

Test-Befehl:
```bash
set -a && source .env && set +a
curl -sk -H "X-API-KEY: $unifi_api_token" \
     -H "Accept: application/json" \
     "https://192.168.10.1/proxy/network/integration/v1/sites"
```

#### Geräte werden nicht erkannt

- `devices.json` Syntax prüfen (JSON-Validator)
- MAC-Adressen in UniFi Controller verifizieren
- `hostname_match` für private MAC-Adressen konfigurieren
- UniFi Logs prüfen: Controller → Insights → Logs

---

<a name="en"></a>
## 🇬🇧 Installation (English)

This integration is **not** in the HACS default store. Install it via a **custom repository** or manually.

### Method 1: Installation via HACS (recommended)

1. **Open HACS** in Home Assistant
2. Navigate to **Integrations**
3. Click the **⋮ menu** (top right)
4. Select **Custom repositories**
5. Add repository:
   - **Repository:** `https://github.com/thelad-dev/unifi-people-pointer`
   - **Category:** Integration
6. Click **Add**
7. Find **UniFi People Pointer** in the (custom) integrations list
8. Click **Download**
9. **Restart Home Assistant**

Note: Earlier 404 errors when adding the repository were often caused by the repo being private. The repository is now public.

### Method 2: Manual Installation

1. **Copy from the repository:**
   ```bash
   cd /tmp
   git clone https://github.com/thelad-dev/unifi-people-pointer.git
   cp -r unifi-people-pointer/custom_components/unifi_people_pointer \
         /config/custom_components/
   ```

2. **Or download ZIP / release:**
   - Download [Latest Release](https://github.com/thelad-dev/unifi-people-pointer/releases/latest) or the repo ZIP
   - Copy the folder `custom_components/unifi_people_pointer/` to `/config/custom_components/unifi_people_pointer/`

3. **Verify directory structure:**
   ```
   /config/
   └── custom_components/
       └── unifi_people_pointer/
           ├── __init__.py
           ├── manifest.json
           └── ...
   ```

4. **Restart Home Assistant**

### Post-Installation

1. **Create UniFi API token:**
   
   - UniFi Network Controller → Settings
   - Admins → Add Admin
   - Role: View Only
   - Generate API Token
   - Copy the token

2. **Add the integration in HA:**
   
   - Settings → Devices & Services → **Add Integration**
   - Search for "UniFi People Pointer"
   - Enter **Host** (IP or hostname), **API token**, and **Verify SSL certificate**
   - Optionally under options: **Scan interval** (default 45s)

3. **Configure people & devices:**
   
   See [configuration.md](configuration.md) for `devices.json` / `people.json`.  
   For local API tests and doc examples, `.env` with `unifi_api_token` remains usable (not for the HA config flow).

### Web UI

The web UI lives in the integration folder (`custom_components/unifi_people_pointer/webui/`) and comes with every HACS or manual install. No Node, Docker or add-on is needed.

- **Start:** with the config entry, also after every HA restart or HACS update (restart HA after updating).
- **Address:** listens on `0.0.0.0`, default port `8765`. Change the port under *Settings → Devices & services → UniFi People Pointer → Configure*; the integration reloads. If the port is taken, a repair issue appears under *Settings → System → Repairs*; the integration keeps running without the UI.
- **Sidebar:** entry **People Pointer** (admins only). The panel embeds `http://<host HA is opened under in the browser>:<port>/` and hands over the HA token automatically.
- **Integration page:** the "UniFi People Pointer" device has a **Visit** link to the UI; **Configure** stays the options dialog.
- **HTTPS:** When HA is opened over HTTPS the browser does not embed the HTTP UI (mixed content). The panel then shows a link that opens the UI in a new tab.
- **Direct access:** `http://<HA host>:8765/` works with a long-lived access token (Profile → Security). The token must belong to an admin.
- **Firewall:** the port must be reachable from the browser (works out of the box on HA OS in the LAN).

### Floor plan

**Floor plan** tab of the web UI.

- **Floor plans:** under **Edit → + Floor** upload one image per floor (PNG, JPEG or WebP, at most 15 MB, no SVG). *Level* orders the floors (for example -1 basement, 0 ground floor). *Width (m)* is the real width of the plan and sets the size of the uncertainty circles; without it the plan counts as 15 m wide. Images and positions stay in the HA config directory (`unifi_people_pointer/floorplans.json` and `unifi_people_pointer/floorplans/`) and are served only with an admin token.
- **Placing access points:** in the *Access points* list choose **Place**, then click the spot on the plan; drag markers or move them with the arrow keys. Positions are stored as fractions of the image width and height, so a replaced image keeps the points.
- **Import from UniFi InnerSpace:** floor plans of the UniFi OS app InnerSpace can only be read with a UniFi OS session, not with the API key. **Import from InnerSpace** signs in once, reads floor plans, AP positions and images, and signs out. The account must be local, have the Admin role for InnerSpace and no two-factor sign-in. User name and password are neither stored nor logged. Floors with the same name are replaced (image and the positions of their APs), others stay. A rotated map is taken into account; the InnerSpace scale is only used when it gives a plan width between 4 and 80 m.
- **People:** markers sit at the AP of the person's first connected device; several people at one AP fan out. The circle is a rough estimate from the signal (strong: about 2 m, weak: up to 15 m). Clients tend to stick to an AP, even through ceilings; the floor is usually right, but not always.
- **Privacy:** locating is off until it is switched on and the person is released under **Edit → Privacy**. Only then does the server return their position. Deleting a person removes their release. No history is kept and no new attributes with coordinates appear in HA.
- **Heatmap:** the **Heatmap** switch in the view. Every placed AP gets a color spot by its usage; the scale runs from the least to the most used AP of the whole house (floors stay comparable), and the list next to it ranks all APs. Choose **Now** (last poll), **1 h**, **24 h** or **7 d**, and **Clients** (average wireless clients per poll) or **Data** (data volume estimated from the client rates UniFi reports at each poll; the current rate for *Now*). *Data* is only available when UniFi reports rates (classic client list); with the integration API it stays client counts. With a network filter set, only clients from the selected networks count ([configuration](configuration.md#network-filter)).
- **Heatmap storage:** counters per AP MAC only, nothing about clients, devices or people: 5-minute steps for 24 hours and hourly steps for 7 days, older values are dropped. The file is `.storage/unifi_people_pointer.ap_usage.<entry>` and is written at most every 5 minutes.
- **Accuracy:** UniFi reports only the one AP a device is connected to, with its signal; trilateration is not possible with that. Room accuracy needs Bluetooth room presence (for example ESPHome Bluetooth proxies with Bermuda) as an additional source.

### System Requirements

- **Home Assistant:** 2024.1.0 or newer
- **Python:** 3.11+
- **UniFi Controller:** Network Application 7.0+ (Cloud Gateway Ultra, Dream Machine, etc.)
- **Network Access:** Home Assistant → UniFi Controller (typically `192.168.x.x`)

### Troubleshooting

#### Integration not showing in HACS

- Add the custom repository first (see above); searching the default store alone will not find this integration
- Clear HACS cache: HACS → ⋮ → Reload HACS
- Verify repository URL: `https://github.com/thelad-dev/unifi-people-pointer`
- On 404: the repo is public; verify the URL and network access
- Check HACS logs: Settings → System → Logs

#### API token not working

- Verify token format: `X-API-KEY` header (not `Bearer`)
- Check controller IP (default: `192.168.10.1`)
- Check firewall rules

Test command:
```bash
set -a && source .env && set +a
curl -sk -H "X-API-KEY: $unifi_api_token" \
     -H "Accept: application/json" \
     "https://192.168.10.1/proxy/network/integration/v1/sites"
```

#### Devices not detected

- Verify `devices.json` syntax (JSON validator)
- Verify MAC addresses in UniFi Controller
- Configure `hostname_match` for private MAC addresses
- Check UniFi logs: Controller → Insights → Logs

---

**[⬆️ Back to README](../README.md)**

## SSL / lokaler Controller

UniFi OS liefert lokal fast immer ein **selbstsigniertes** Zertifikat.
Die Integration setzt **„SSL-Zertifikat prüfen“ standardmäßig auf aus**.

Schnelltest:

```bash
curl -sk -H "X-API-KEY: $unifi_api_token" -H "Accept: application/json"   "https://192.168.10.1/proxy/network/integration/v1/sites"
```

