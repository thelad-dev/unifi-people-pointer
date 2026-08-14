# Installation / Installation

**[🇩🇪 Deutsch](#de)** | **[🇬🇧 English](#en)**

---

<a name="de"></a>
## 🇩🇪 Installation (Deutsch)

### Methode 1: Installation über HACS (empfohlen)

1. **HACS öffnen** in Home Assistant
2. Zu **Integrationen** navigieren
3. Auf das **⋮-Menü** (oben rechts) klicken
4. **Custom repositories** auswählen
5. Repository hinzufügen:
   - **Repository:** `https://github.com/thelad-dev/unifi-people-pointer`
   - **Kategorie:** Integration
6. Auf **Add** klicken
7. **UniFi People Pointer** in der Integrationsliste suchen
8. **Download** klicken
9. **Home Assistant neu starten**

### Methode 2: Manuelle Installation

1. **Repository klonen:**
   ```bash
   cd /config/custom_components
   git clone https://github.com/thelad-dev/unifi-people-pointer.git
   ```

2. **Oder ZIP herunterladen:**
   - [Latest Release](https://github.com/thelad-dev/unifi-people-pointer/releases/latest) herunterladen
   - Ins `custom_components`-Verzeichnis entpacken

3. **Verzeichnisstruktur prüfen:**
   ```
   /config/
   └── custom_components/
       └── unifi_people_pointer/
           ├── __init__.py
           ├── manifest.json
           ├── devices.json
           ├── people.json
           ├── manufacturers.json
           └── ...
   ```

4. **Home Assistant neu starten**

### Nach der Installation

1. **API-Token konfigurieren:**
   
   Erstelle eine `.env`-Datei im Integrationsverzeichnis:
   ```bash
   unifi_api_token="your-api-token-here"
   ```

   ⚠️ **Wichtig:** Die `.env`-Datei wird **nicht** ins Repository committed (`.gitignore`).

2. **UniFi API-Token erstellen:**
   
   - UniFi Network Controller → Settings
   - Admins → Add Admin
   - Role: View Only
   - Generate API Token
   - Token kopieren und in `.env` einfügen

3. **Konfiguration anpassen:**
   
   Siehe [configuration.md](configuration.md) für Details zu:
   - `devices.json` – Zu trackende Geräte
   - `people.json` – Zuordnung zu HA-Personen
   - `manufacturers.json` – OUI-Datenbank (normalerweise unverändert)

4. **Integration in HA aktivieren:**
   
   - Settings → Devices & Services
   - **Add Integration**
   - "UniFi People Pointer" suchen
   - Konfigurieren und aktivieren

### Systemvoraussetzungen

- **Home Assistant:** 2024.1.0 oder neuer
- **Python:** 3.11+
- **UniFi Controller:** Network Application 7.0+ (Cloud Gateway Ultra, Dream Machine, etc.)
- **Netzwerkzugriff:** Home Assistant → UniFi Controller (typisch `192.168.x.x`)

### Troubleshooting

#### Integration erscheint nicht in HACS

- HACS-Cache leeren: HACS → ⋮ → Reload HACS
- Repository-URL prüfen
- HACS-Logs prüfen: Settings → System → Logs

#### API-Token funktioniert nicht

- Token-Format prüfen: `X-API-KEY` Header (nicht `Bearer`)
- Controller-IP prüfen (Standard: `192.168.88.1`)
- Firewall-Regeln prüfen

Test-Befehl:
```bash
set -a && source .env && set +a
curl -sk -H "X-API-KEY: $unifi_api_token" \
     -H "Accept: application/json" \
     "https://192.168.88.1/proxy/network/integration/v1/sites"
```

#### Geräte werden nicht erkannt

- `devices.json` Syntax prüfen (JSON-Validator)
- MAC-Adressen in UniFi Controller verifizieren
- `hostname_match` für private MAC-Adressen konfigurieren
- UniFi Logs prüfen: Controller → Insights → Logs

---

<a name="en"></a>
## 🇬🇧 Installation (English)

### Method 1: Installation via HACS (recommended)

1. **Open HACS** in Home Assistant
2. Navigate to **Integrations**
3. Click the **⋮ menu** (top right)
4. Select **Custom repositories**
5. Add repository:
   - **Repository:** `https://github.com/thelad-dev/unifi-people-pointer`
   - **Category:** Integration
6. Click **Add**
7. Search for **UniFi People Pointer** in the integration list
8. Click **Download**
9. **Restart Home Assistant**

### Method 2: Manual Installation

1. **Clone repository:**
   ```bash
   cd /config/custom_components
   git clone https://github.com/thelad-dev/unifi-people-pointer.git
   ```

2. **Or download ZIP:**
   - Download [Latest Release](https://github.com/thelad-dev/unifi-people-pointer/releases/latest)
   - Extract to `custom_components` directory

3. **Verify directory structure:**
   ```
   /config/
   └── custom_components/
       └── unifi_people_pointer/
           ├── __init__.py
           ├── manifest.json
           ├── devices.json
           ├── people.json
           ├── manufacturers.json
           └── ...
   ```

4. **Restart Home Assistant**

### Post-Installation

1. **Configure API token:**
   
   Create a `.env` file in the integration directory:
   ```bash
   unifi_api_token="your-api-token-here"
   ```

   ⚠️ **Important:** The `.env` file is **not** committed to the repository (`.gitignore`).

2. **Create UniFi API token:**
   
   - UniFi Network Controller → Settings
   - Admins → Add Admin
   - Role: View Only
   - Generate API Token
   - Copy token and paste into `.env`

3. **Customize configuration:**
   
   See [configuration.md](configuration.md) for details on:
   - `devices.json` – Devices to track
   - `people.json` – Mapping to HA persons
   - `manufacturers.json` – OUI database (usually unchanged)

4. **Activate integration in HA:**
   
   - Settings → Devices & Services
   - **Add Integration**
   - Search for "UniFi People Pointer"
   - Configure and activate

### System Requirements

- **Home Assistant:** 2024.1.0 or newer
- **Python:** 3.11+
- **UniFi Controller:** Network Application 7.0+ (Cloud Gateway Ultra, Dream Machine, etc.)
- **Network Access:** Home Assistant → UniFi Controller (typically `192.168.x.x`)

### Troubleshooting

#### Integration not showing in HACS

- Clear HACS cache: HACS → ⋮ → Reload HACS
- Verify repository URL
- Check HACS logs: Settings → System → Logs

#### API token not working

- Verify token format: `X-API-KEY` header (not `Bearer`)
- Check controller IP (default: `192.168.88.1`)
- Check firewall rules

Test command:
```bash
set -a && source .env && set +a
curl -sk -H "X-API-KEY: $unifi_api_token" \
     -H "Accept: application/json" \
     "https://192.168.88.1/proxy/network/integration/v1/sites"
```

#### Devices not detected

- Verify `devices.json` syntax (JSON validator)
- Verify MAC addresses in UniFi Controller
- Configure `hostname_match` for private MAC addresses
- Check UniFi logs: Controller → Insights → Logs

---

**[⬆️ Back to README](../README.md)**
