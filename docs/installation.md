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
