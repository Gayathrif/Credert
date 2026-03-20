"""app.py - Main entry point for the Credert website-monitoring application."""

import logging
import os

from flask import Flask, jsonify, request

import database
import scheduler as sched_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/sites", methods=["GET"])
def list_sites():
    """Return all monitored sites."""
    sites = database.get_all_sites()
    return jsonify([dict(s) for s in sites])


@app.route("/sites", methods=["POST"])
def add_site():
    """Add a new URL to the monitoring list.

    JSON body: {"url": "https://example.com"}
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400

    site_id = database.add_site(url)
    return jsonify({"id": site_id, "url": url}), 201


@app.route("/sites/<path:url>", methods=["DELETE"])
def delete_site(url):
    """Remove a URL from the monitoring list."""
    database.remove_site(url)
    return jsonify({"message": f"Removed {url}"}), 200


@app.route("/acknowledge/<token>", methods=["GET"])
def acknowledge(token):
    """Acknowledge a pending alert via its unique token."""
    found = database.acknowledge(token)
    if found:
        return jsonify({"message": "Alert acknowledged. Thank you!"}), 200
    return jsonify({"error": "Invalid or already-used token."}), 404


@app.route("/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Application startup
# ---------------------------------------------------------------------------

def create_app(check_interval: int = 2, reminder_interval: int = 5) -> Flask:
    """Initialise the database, start the background scheduler, and return the Flask app.

    Side effects:
        - Creates the SQLite schema if it does not exist.
        - Starts an APScheduler BackgroundScheduler with site-check and
          reminder jobs running at the given intervals (in minutes).
    """
    database.init_db()
    scheduler = sched_module.create_scheduler(check_interval, reminder_interval)
    scheduler.start()
    logger.info(
        "Scheduler started (check every %d min, remind every %d min).",
        check_interval,
        reminder_interval,
    )
    return app


if __name__ == "__main__":
    check_interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "2"))
    reminder_interval = int(os.getenv("REMINDER_INTERVAL_MINUTES", "5"))
    flask_app = create_app(check_interval, reminder_interval)
    flask_app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
