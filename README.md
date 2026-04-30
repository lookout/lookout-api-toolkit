# Lookout Toolkit

Open-source toolkit for integrating and extending [Lookout Mobile Intelligence](https://www.lookout.com/) APIs. Includes sample code, automation scripts, and reference implementations to accelerate mobile risk analysis, threat intelligence ingestion, and security-driven workflows.

---

## Tools in This Repository

| Tool | Description | Language |
|------|-------------|----------|
| [Lookout Device Dashboard](#1-lookout-device-dashboard) | Real-time web dashboard for device fleet management and risk analysis | Python / Flask |
| [Lookout Application Tool](#2-lookout-application-tool) | Web UI for submitting mobile apps to Lookout for security analysis | Python / Flask |
| [MRAv2 Syslog Connector](#3-mrav2-syslog-connector) | High-performance connector that streams Lookout events to SIEM syslog servers | Python |
| [Lookout Threat Feed Manager](#4-lookout-threat-feed-manager) | CLI tool for managing Lookout threat feeds via REST API | Python |

---

## Prerequisites

All tools require:

- **Python 3.8+**
- A **Lookout API Application Key** — obtained from the [Lookout Console](https://app.lookout.com) under **System > Application Keys**

Each tool has its own `requirements.txt`. Install dependencies inside a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Tool Details

### 1. Lookout Device Dashboard

**Directory:** `Lookout_Device_dashboard-release-v1.0/`

A Flask web application that connects to the Lookout Mobile Risk API v2 and presents a real-time device management dashboard.

**Key features:**
- Real-time device inventory with risk-level summaries (connected, stale, disconnected)
- Advanced filtering by platform, risk level, protection status, and last check-in date
- Excel export of filtered device data with summary sheets
- CVE vulnerability scanning across your device fleet
- Multi-tenant support — manage multiple Lookout tenants from a single interface
- Two-layer caching (in-memory + SQLite) with background refresh and delta sync
- Optional HTTP Basic authentication with hashed passwords
- Rate limiting on all API endpoints

**Quick start:**

```bash
cd Lookout_Device_dashboard-release-v1.0
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your LOOKOUT_APPLICATION_KEY
python app.py
# Open http://localhost:5001
```

No API key? Run in sample data mode:

```bash
USE_SAMPLE_DATA=true python app.py
```

See [`Lookout_Device_dashboard-release-v1.0/README.md`](Lookout_Device_dashboard-release-v1.0/README.md) for full configuration reference, multi-tenant setup, fleet size recommendations, and troubleshooting.

---

### 2. Lookout Application Tool

**Directory:** `Lookout-Application-Tool/`

A local Flask web application for submitting mobile apps (IPA, APK, AAB) to Lookout for security analysis. Supports both file upload and App Store / Google Play URL submissions.

**Key features:**
- Submit `.ipa`, `.apk`, or `.aab` files up to 2 GB
- Submit apps via Apple App Store or Google Play Store URLs
- Auto-exchanges your Application Key for an OAuth2 Bearer Token
- Track submission status by reference ID
- View full submission history for the current session
- Export analysis results as JSON, Summary, or CSV

**Quick start:**

```bash
cd Lookout-Application-Tool
pip install -r requirements.txt
cp config.example.py config.py
# Edit config.py with your APP_KEY or BEARER_TOKEN
python app_improved.py
# Open http://localhost:5000
```

See [`Lookout-Application-Tool/README.md`](Lookout-Application-Tool/README.md) for full usage, API endpoints, and troubleshooting.

---

### 3. MRAv2 Syslog Connector

**Directory:** `lookout-mrav2-syslog-connector-V2/`

A high-performance Python connector that streams security events from the Lookout Mobile Risk API v2 and forwards them in real time to a SIEM syslog server (QRadar, Splunk, or any syslog-compatible system).

**Key features:**
- Real-time event streaming via Server-Sent Events (SSE)
- Supports THREAT, DEVICE, and AUDIT event types
- QRadar output: LEEF 2.0 format over syslog TCP/UDP
- Splunk output: JSON format over syslog TCP/UDP
- Multi-tenant — each tenant runs in its own thread
- Auto-reconnection with exponential backoff
- OAuth2 authentication with automatic token refresh
- HTTP/HTTPS proxy support with authentication
- Stream position tracking — no duplicate events on restart
- Scales to 50,000+ devices across 10 tenants on modest hardware

**Quick start:**

```bash
cd lookout-mrav2-syslog-connector-V2
./install.sh
cp config.ini.example config.ini
# Edit config.ini with your api_key and syslog server details
./start-connector.sh
```

Docker is also supported — see the README for container and systemd service deployment options.

See [`lookout-mrav2-syslog-connector-V2/README.md`](lookout-mrav2-syslog-connector-V2/README.md) for full configuration reference, scaling guidelines, Docker instructions, and troubleshooting.

---

### 4. Lookout Threat Feed Manager

**Directory:** `Lookout-ThreatFeed-V4/`

A Python CLI tool for managing Lookout threat feeds via the Lookout REST API. Supports both an interactive color-coded menu and a fully non-interactive CLI mode for automation and scripting.

**Key features:**
- Browse all feeds in a numbered table
- View, add, remove, and bulk-update domains within a feed
- Update feed content from a remote URL (OVERWRITE or INCREMENTAL mode)
- Delete feeds with typed confirmation
- Batch domain operations — inline or from a file (one domain per line, `#` comments supported)
- Paginated domain viewer with forward/back navigation
- Full CLI automation with proper exit codes for scripting

**Quick start:**

```bash
cd Lookout-ThreatFeed-V4
pip install -r requirements.txt
echo "your-api-key-here" > api_key.txt
python improved_threat_feed_management.py            # interactive mode
python improved_threat_feed_management.py --list-feeds  # CLI mode
```

See [`Lookout-ThreatFeed-V4/README.md`](Lookout-ThreatFeed-V4/README.md) for the full CLI reference, domain file format, and upload mode details.

---

## Security Notes

- **Never commit API keys or credentials.** All tools use `.gitignore` to exclude credential files (`.env`, `config.py`, `config.ini`, `api_key.txt`).
- Each tool ships an example credential file (`.env.example`, `config.example.py`, `config.ini.example`) — copy and populate locally; do not commit the filled-in version.
- The Device Dashboard's development fallback credentials (`admin`/`admin123`) are only active when `FLASK_ENV` is not set to `production` and are logged with a warning. Configure `AUTH_USERS` or `AUTH_USERS_FILE` for any shared or internet-accessible deployment.
- All tools authenticate to the Lookout API using OAuth2 Client Credentials flow.

---

## Repository Structure

```
lookout-toolkit/
├── Lookout_Device_dashboard-release-v1.0/   # Device fleet dashboard (Flask)
├── Lookout-Application-Tool/                 # App submission tool (Flask)
├── lookout-mrav2-syslog-connector-V2/        # SIEM syslog connector (Python)
├── Lookout-ThreatFeed-V4/                    # Threat feed manager (Python CLI)
└── README.md                                 # This file
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-improvement`)
3. Commit your changes (`git commit -m 'Add my improvement'`)
4. Push to the branch (`git push origin feature/my-improvement`)
5. Open a Pull Request

Please ensure no credentials, `.env` files, `config.ini`, or `api_key.txt` files are included in your commit.

---

## License

See the [LICENSE](LICENSE) file for details.
