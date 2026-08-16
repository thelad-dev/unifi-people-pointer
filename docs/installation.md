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
