"""
app.py - Main Flask REST API for Credert.

Endpoints
---------
POST   /websites              Add a URL to monitor.
GET    /websites              List all monitored websites.
GET    /websites/<id>         Get a single monitored website.
DELETE /websites/<id>         Stop monitoring a website.
GET    /alerts                List all alerts.
GET    /acknowledge/<token>   Acknowledge an alert via a unique token.
GET    /health                Health check.
"""

import logging
import os

from flask import Flask, jsonify, request

import database
import scheduler as scheduler_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialise the database on startup.
database.init_db()

# Start the background scheduler.
_scheduler = scheduler_module.create_scheduler()
_scheduler.start()
logger.info("Background scheduler started.")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Website endpoints
# ---------------------------------------------------------------------------

@app.route("/websites", methods=["POST"])
def add_website():
    """Add a new URL to monitor."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return _error("'url' field is required.")

    if not url.startswith(("http://", "https://")):
        return _error("'url' must start with http:// or https://")

    try:
        website = database.add_website(url)
        return jsonify(website), 201
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            return _error(f"URL '{url}' is already being monitored.", 409)
        logger.exception("Error adding website")
        return _error("Internal server error.", 500)


@app.route("/websites", methods=["GET"])
def list_websites():
    """Return all monitored websites."""
    return jsonify(database.get_all_websites())


@app.route("/websites/<int:website_id>", methods=["GET"])
def get_website(website_id: int):
    """Return a single website by id."""
    website = database.get_website(website_id)
    if website is None:
        return _error("Website not found.", 404)
    return jsonify(website)


@app.route("/websites/<int:website_id>", methods=["DELETE"])
def delete_website(website_id: int):
    """Remove a website from monitoring."""
    deleted = database.delete_website(website_id)
    if not deleted:
        return _error("Website not found.", 404)
    return jsonify({"message": "Website removed from monitoring."})


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------

@app.route("/alerts", methods=["GET"])
def list_alerts():
    """Return all alerts (acknowledged and pending)."""
    return jsonify(database.get_all_alerts())


@app.route("/acknowledge/<ack_token>", methods=["GET"])
def acknowledge_alert(ack_token: str):
    """Acknowledge an alert using its unique token."""
    updated = database.acknowledge_alert(ack_token)
    if not updated:
        return _error(
            "Alert not found or already acknowledged.", 404
        )
    return jsonify({"message": "Alert acknowledged. Thank you!"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Simple liveness check."""
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
