# Credert

Credert is a website monitoring and notification system that detects critical updates and sends persistent alerts via messaging platforms until acknowledged by the user. It is designed to prevent missed deadlines, results, and important announcements.

---

## Features

- **Website monitoring** — periodically fetches any URL and detects content changes using MD5 hashing.
- **Persistent alerts** — sends an alert when a change is detected and keeps sending reminders until the alert is acknowledged.
- **Acknowledgment system** — each alert contains a unique one-click link that marks it as done.
- **WhatsApp notifications** (optional) — integrates with the Twilio API to push alerts to WhatsApp.
- **REST API** — add/remove monitored URLs and acknowledge alerts via a simple HTTP API.
- **Scheduler** — runs site checks and reminder dispatch on configurable intervals using APScheduler.

---

## Project Structure

```
Credert/
├── app.py          # Main Flask application & entry point
├── monitor.py      # Website fetching and MD5 change detection
├── database.py     # SQLite persistence layer
├── notifier.py     # Console + optional WhatsApp alerts
├── scheduler.py    # APScheduler jobs (check & remind)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables (optional)

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Flask server port |
| `CHECK_INTERVAL_MINUTES` | `2` | How often to check sites for changes |
| `REMINDER_INTERVAL_MINUTES` | `5` | How often to resend pending alerts |
| `CREDERT_BASE_URL` | `http://localhost:5000` | Base URL used in acknowledgment links |
| `TWILIO_ACCOUNT_SID` | *(unset)* | Twilio account SID (WhatsApp optional) |
| `TWILIO_AUTH_TOKEN` | *(unset)* | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` | Twilio sandbox sender number |
| `TWILIO_WHATSAPP_TO` | *(unset)* | Your WhatsApp number (`whatsapp:+1...`) |

If Twilio variables are not set, the app falls back to console/log alerts only.

### 3. Run the application

```bash
python app.py
```

The Flask server starts on `http://localhost:5000`.

---

## API Reference

### Add a URL to monitor

```
POST /sites
Content-Type: application/json

{"url": "https://example.com"}
```

### List all monitored sites

```
GET /sites
```

### Remove a monitored site

```
DELETE /sites/<url>
```

### Acknowledge an alert

```
GET /acknowledge/<token>
```

Each alert message contains a pre-built acknowledgment URL — just open it in a browser or click the link in the WhatsApp message.

### Health check

```
GET /health
```

---

## How It Works

1. Add one or more URLs via `POST /sites`.
2. The scheduler checks each URL every `CHECK_INTERVAL_MINUTES`.
3. When a change is detected, an alert is printed to the console (and sent via WhatsApp if configured).
4. If the alert is not acknowledged, a reminder is sent every `REMINDER_INTERVAL_MINUTES`.
5. Opening the acknowledgment URL marks the alert as **done** and stops reminders.
