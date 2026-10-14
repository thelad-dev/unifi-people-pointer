# Handwerk vor dem Diff: upp-ha-integration-20261014

## Annahme

- Die Config-Entry in der Captain-Instanz ist echt eingerichtet (Host UniFi-Gateway, Token vorhanden, `verify_ssl: false`, `state: loaded`). Die leere `data`-Antwort der REST-API war Redaction, nicht fehlende Credentials.
- Das Zielbild meint HA-`device_tracker`-Entities pro Person (nicht nur die bestehenden `person.*`-Entities), gespeist aus UniFi-Clients und `people.json`/`devices.json`.
- Das Datenmodell aus den Test-Fixtures und `docs/datenmodell.md` (Personen mit `device_ids`, Geräte mit `mac`/`hostname_match`/`track`) ist die maßgebliche Form; die abweichenden Schemas unter `schemas/` und die Example-JSONs mit verschachteltem `devices.primary` sind Altlast.
- Deploy zur Instanz läuft über `ssh hass` nach `/config/custom_components/…` plus Core-Neustart; HACS-Release ist nicht Voraussetzung für den Nachweis in dieser Runde.
- Ein HA-Backup vor Eingriffen ist Pflicht; Hassio/`ha backups` ist verfügbar.

## Zwei Wege

1. **Auftragspfad (gewählt):** Integration so verdrahten, dass Setup Coordinator + Platforms lädt, UniFi-Clients pollt, Personen-Presence aus JSON-Mapping berechnet und echte Entities liefert; Regressionstest für den bisherigen Leerzustand; Nachweis am echten Haus.
2. **Nicht aus dem Auftrag (verworfen):** Nur Config-Flow/SSL weiter polieren und die fehlenden Entities als „Phase 3 später“ belassen, oder das optionale Node/React-Backend für Presence missbrauchen.

Warum 1: Der Fehlzustand ist nicht Auth/SSL (Entry ist `loaded`), sondern absichtlich leere `PLATFORMS` plus Stub-Coordinator/Stubs in Parser/Loader/Presence. Ohne Verdrahtung bleibt das Zielbild unerreichbar. Weg 2 würde den beobachteten Leerzustand nur kaschieren.

## Ablehnung

Ein erfahrener Kollege würde ablehnen, wenn:

- Platforms wieder aktiviert werden, ohne dass Sensor/Tracker den Coordinator korrekt aus `hass.data` lesen (Setup-Crash wie damals beim Config-Flow-500-Fix).
- Ein zweites, inkompatibles Personen-Schema eingeführt oder `schemas/` als Wahrheit belassen wird, während Fixtures etwas anderes testen.
- Haushalts-Tokens, private IPs oder volle Credential-Dumps im Repo/PR landen.
- Bestehende Integrationen/Automationen angefasst oder Helga (VLAN 50) berührt wird.
- „Tests grün“ allein als Nachweis gilt, obwohl die Phase-3-Suiten weiterhin übersprungen sind.

## Nachweis

- Gegenexperiment vor dem Umbau: Platforms auf der Live-Kopie kurz nur auf `device_tracker` stellen ohne Coordinator-Wiring → weiterhin keine Personen-Entities (leere Entity-Liste in `device_tracker.async_setup_entry`); damit ist „nur deferred platforms“ notwendig, aber nicht hinreichend widerlegt bzw. ergänzt.
- Nach Umbau: `pytest` (Config-Flow + neue Setup/Presence-Regressionen) grün.
- Am Haus: `ha-axi entity search` / `state get` zeigt Entities der Integration mit plausiblen `home`/`not_home`-Werten; Browser-Screenshot der Integration; mindestens ein Anwesenheitswechsel oder dokumentierter Ersatzbeleg.
- Backup-ID vor dem Eingriff im PR nennen.

## Grenze

- Nicht anfassen: offizielle `unifi`-Integration (ignore/not_loaded), Helga, Automationen, Entity-Umbenennungen/Löschungen, Netz/VLANs, Frontend/Backend-Docker-Stack außer wo die Trennung Integration↔optionales Backend dokumentiert werden muss.
- Keine Umbenennungen ohne Nutzen fürs Zielbild; keine neuen Abhängigkeiten ohne Not.
- Keine Tokens/Passwörter/Geräte-IPs im Repo oder PR; Personennamen nur soweit für den Nachweis nötig.
- `AGENTS.md`/`CLAUDE.md` nur korrigieren, wo der Umbau Fakten falsch macht — kein Wissens-Anhang.
