# Credert

Credert is a Python-based backend application that monitors websites for content changes and sends **persistent WhatsApp notifications** (via Twilio) until the user explicitly acknowledges each alert. It is designed to prevent missed deadlines, exam results, and other important announcements.

---

## Features

- Add any HTTP/HTTPS URL to a monitoring list via a simple REST API.
- Periodically fetches each website and compares an MD5 hash of the content with the previously stored baseline.
- Stores website data (URL, last content hash, status) and alert records in a local SQLite database.
- Sends a WhatsApp message (via the Twilio API) when a change is detected.
- Tracks acknowledgement with a unique one-time token embedded in the notification message.
- Sends repeated reminder messages at configurable intervals until the user clicks the acknowledgement link.

---

## Project Structure

```
credert/
├── app.py          # Flask REST API (main entry point)
├── monitor.py      # Website-fetching and change-detection logic
├── notifier.py     # WhatsApp notification delivery via Twilio
├── database.py     # SQLite persistence layer
├── scheduler.py    # Background scheduler (APScheduler)
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.11+
- A [Twilio](https://www.twilio.com/) account with the **WhatsApp sandbox** (or a production WhatsApp sender) enabled.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Gayathrif/Credert.git
cd Credert
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (or export variables directly):

```dotenv
# Twilio credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Twilio sandbox number
NOTIFY_WHATSAPP_TO=whatsapp:+1234567890      # your WhatsApp number

# Base URL of this server (used to build acknowledgement links)
APP_BASE_URL=https://your-server.example.com

# Optional tuning
CHECK_INTERVAL_MINUTES=10     # how often websites are checked (default 10)
REMINDER_INTERVAL_MINUTES=5   # how often the reminder job runs (default 5)
REMINDER_RESEND_MINUTES=30    # minimum gap between reminders per alert (default 30)
MONITOR_TIMEOUT=15            # HTTP request timeout in seconds (default 15)

# Optional Flask settings
FLASK_PORT=5000
FLASK_DEBUG=false
```

> **Never commit your `.env` file.** Add it to `.gitignore`.

### 5. Run the application

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

---

## API Reference

### Health check

```
GET /health
```

### Websites

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/websites` | Add a URL to monitor |
| `GET` | `/websites` | List all monitored websites |
| `GET` | `/websites/<id>` | Get a single website by id |
| `DELETE` | `/websites/<id>` | Stop monitoring a website |

**Add a website – request body:**

```json
{ "url": "https://example.com" }
```

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alerts` | List all alerts |
| `GET` | `/acknowledge/<token>` | Acknowledge an alert (included in the WhatsApp message) |

---

## How It Works

1. **Add a URL** with `POST /websites`.
2. The scheduler checks each active URL every `CHECK_INTERVAL_MINUTES` minutes.
3. On the first check the baseline hash is recorded – no alert is raised.
4. On subsequent checks, if the hash differs from the stored baseline, an alert record is created and a WhatsApp message containing a unique acknowledgement link is sent.
5. The reminder job runs every `REMINDER_INTERVAL_MINUTES` minutes and re-sends the WhatsApp message for any alert that has not been acknowledged within the last `REMINDER_RESEND_MINUTES` minutes.
6. When the user visits the acknowledgement URL (`GET /acknowledge/<token>`), the alert is marked as resolved and reminders stop.

---

## License

MIT
