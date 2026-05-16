# Dropbox to Restic S3 Backup

Eine Python-Lösung zur Automatisierung von Backups von Bildern aus Dropbox auf S3-kompatible Speicher unter Verwendung von Restic.

## Projektstruktur

```
dropbox-to-restic-s3-backup/
├── src/
│   ├── main.py              # Hauptskript für die Backup-Verwaltung
│   └── restic_backup.py     # Restic-Integration und Backup-Logik
├── Dropbox_Bilder/          # Lokales Verzeichnis für Dropbox-Bilder
│   ├── 2026/
│   └── erledigt/
├── .env                     # Umgebungsvariablen (nicht im Git)
├── .gitignore               # Git-Ignorierrules
├── LICENSE                  # MIT Lizenz
└── README.md               # Diese Datei
```

## Features

- **Dropbox-Integration**: Automatisches Abrufen von Bildern aus Dropbox über OAuth2
- **Restic-Backups**: Sichere, inkrementelle Backups mit Restic
- **S3-Kompatibilität**: Unterstützung für beliebige S3-kompatible Speicherlösungen
- **Konfigurierbar**: Umgebungsvariablen für flexible Konfiguration

## Voraussetzungen

- Python 3.7+
- Restic ([Installation](https://restic.net/))
- Dropbox App Credentials
- S3-kompatible Speicherlösung

## Setup-Anleitung

1. **Repository klonen:**
   ```bash
   git clone <repository-url>
   cd dropbox-to-restic-s3-backup
   ```

2. **Virtuelle Umgebung erstellen:**
   ```bash
   python -m venv .venv
   ```

3. **Virtuelle Umgebung aktivieren:**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Umgebungsvariablen konfigurieren (.env Datei):**
   ```
   # Dropbox OAuth2
   DROPBOX_CLIENT_ID=<your-client-id>
   DROPBOX_CLIENT_SECRET=<your-client-secret>
   DROPBOX_REFRESH_TOKEN=<your-refresh-token>
   
   # Restic
   RESTIC_REPOSITORY=<s3:s3.example.com/bucket/path>
   RESTIC_PASSWORD=<secure-password>

   # AWS S3 Buckets
   buckets=bucket1,bucket2

   MOUNT_FOLDER=/mnt/mobsean
   ```

6. **Dropbox App konfigurieren:**
   - Erstelle eine App auf der [Dropbox Developer Console](https://www.dropbox.com/developers/apps)
   - Aktiviere OAuth2 mit Refresh Token Flow
   - Trage die Credentials in der `.env` Datei ein

7. **Restic installieren:**
   - Folge der Anleitung auf [restic.net](https://restic.net/)
   - S3-Credentials können auch als Umgebungsvariablen gesetzt werden

## Verwendung

Starten Sie das Backup-Skript:

```bash
python src/main.py
```

Das Skript wird sich mit Dropbox verbinden, Bilder herunterladen und sie mit Restic auf S3 sichern.

## Lizenz

Dieses Projekt ist lizenziert unter der MIT Lizenz. Siehe [LICENSE](LICENSE) für Details.