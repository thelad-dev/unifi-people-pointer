# Handwerk vor dem Diff: upp-ap-name-webui

Ziel: (1) Tracker und Sensoren zeigen den Namen des Access Points, an dem ein Gerät eingeloggt ist, z. B. "iPhone-SKHL AP: EG-Diele". (2) Die Web-UI wird mit der Integration installiert, bindet auf 0.0.0.0 und ist aus Home Assistant heraus erreichbar (Seitenleiste und Integrationsseite).

## Annahme

- Die AP-MAC steht im Client-Datensatz (`ap_mac` der klassischen `stat/sta`-Liste, bzw. `uplinkDeviceId` der Integration-API). Den Namen liefert die UniFi-Geräteliste (`stat/device-basic`, Fallback `stat/device`, Fallback Integration-API `/devices`). Neuere Controller liefern zusätzlich `last_uplink_name` im Client-Datensatz; das dient als Rückfall.
- Eine HACS-Installation lädt nur `custom_components/unifi_people_pointer/`. "Standardmäßig installiert" heißt also: UI-Bundle und UI-Server liegen in diesem Ordner und starten mit dem Config-Entry. Node, Docker oder ein Add-on sind auf dem Zielsystem nicht vorhanden bzw. nicht gewollt.
- Der bisherige Node-Backend-Teil hat einen eigenen, von der Integration getrennten Datenbestand (persons/zones/settings mit HA-Token) und ist nie mit `people.json`/`devices.json` verbunden gewesen. Er wird durch eine Python-API in der Integration ersetzt, die auf denselben Daten und Coordinator-Methoden arbeitet wie die Services.
- Die bestehenden Entity-IDs sind in der Registry festgeschrieben; ein dynamischer Anzeigename ändert sie nicht. Für neu registrierte Entities wird die Objekt-ID weiter aus dem Basisnamen ohne AP-Zusatz gebildet.

## Zwei Wege

Teil 1 (AP-Name):
- Gewählt: dynamischer Anzeigename `<Name> AP: <AP-Name>` am Geräte- und Personen-Tracker, solange das Gerät verbunden ist und ein AP-Name bekannt ist; zusätzlich Attribute `ap_name` (Tracker) und `ap_name` je Client in den Unknown-/Guest-Sensoren. Begründung: das Beispiel ist wörtlich ein Anzeigename; Attribut bleibt für Automationen.
- Verworfen: je Gerät ein zusätzlicher Sensor "AP" mit dem Namen als State. Verdoppelt die Entity-Zahl und zeigt nicht das gewünschte Format am Tracker selbst.

Teil 2 (Web-UI):
- Gewählt: aiohttp-Server in der Integration auf `0.0.0.0:<webui_port>` (Default 8765, Option), liefert das mit Vite gebaute React-Bundle (eingecheckt unter `custom_components/unifi_people_pointer/webui/`) und eine JSON-API. Seitenleiste: `panel_custom`-Panel, dessen kleines JS-Modul (über HA-Static-Path) ein iframe auf `<Browser-Hostname>:<Port>` öffnet und das HA-Access-Token per `postMessage` übergibt. Integrationsseite: Service-Gerät mit `configuration_url` ("Besuchen"-Link). Die API verlangt ein gültiges HA-Token (Schreiben nur Admin), damit der 0.0.0.0-Port keine offene Schreibschnittstelle im LAN ist.
- Verworfen: Node-Backend und Nginx weiter per Docker betreiben und nur verlinken (bleibt Zusatzinstallation, getrennter Datenbestand). Ebenfalls verworfen: UI komplett über den HA-HTTP-Server ausliefern (erfüllt 0.0.0.0-eigener-Port nicht, iframe-Auth über signierte Pfade wäre pro Request nötig).

## Ablehnung

- Entity-IDs ändern sich durch den AP-Zusatz (neue Entities bekämen `..._ap_eg_diele`).
- Offene, unauthentifizierte Schreib-API auf 0.0.0.0.
- Ausfall der AP-Geräteliste lässt das Client-Polling scheitern.
- Eingechecktes Bundle passt nicht zum Quelltext (kein reproduzierbarer Build, kein Lockfile).
- Zwei Datenmodelle (UI-eigenes JSON neben people/devices.json).
- Portkonflikt lässt das Setup des Config-Entries scheitern.
- Nutzung von `register_static_path`, das in aktuellen HA-Versionen entfernt ist.

## Nachweis

- `pytest tests/` grün (neue Tests: AP-Name-Auflösung inkl. Wechsel, Anzeigename und stabile Objekt-ID, Sensor-Attribute, Web-API mit/ohne Token, Server-Start/-Stopp, Panel-Registrierung).
- `black`/`isort`/`flake8` wie im CI.
- `npm ci && npm run build` im `frontend/` erzeugt ein Bundle ohne Diff zum eingecheckten Stand.
- Echte HA nur lesend per ha-axi: vorhandene `ap_mac`-Werte der Tracker als Eingabe; kein Deploy vor dem Merge.
- Web-UI lokal gegen einen Testserver mit Beispieldaten starten und per chrome-devtools-axi Bildschirmfoto prüfen.

## Grenze

- Keine Änderung an Präsenzlogik, Matching, Event-Debounce, Config-Flow-Validierung oder an den bestehenden Services.
- Keine Änderung an Entity-IDs/unique_ids.
- Kein Deploy auf die Haupt-HA, keine Schreibzugriffe dort.
- `hacs.json`-Domains und sonstige Altlasten außerhalb der Aufgabe werden nur berichtet.
- Node-Backend, Docker-Compose und Frontend-Dockerfile/Nginx werden entfernt (ersetzt), nicht weitergepflegt.
