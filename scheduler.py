"""
scheduler.py - Periodic task management for Credert.

Two recurring jobs are registered:

1. **check_websites_job** – runs every ``CHECK_INTERVAL_MINUTES`` minutes and
   calls :func:`monitor.check_all_websites` to detect content changes.

2. **send_reminders_job** – runs every ``REMINDER_INTERVAL_MINUTES`` minutes
   and sends follow-up WhatsApp messages for alerts that remain unacknowledged
   and have not been notified within the reminder window.

Environment variables (all optional, with defaults):
  CHECK_INTERVAL_MINUTES   – how often to check websites (default: 10)
  REMINDER_INTERVAL_MINUTES – how often the reminder job runs (default: 5)
  REMINDER_RESEND_MINUTES  – minimum gap between reminders for one alert
                             (default: 30)
"""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database
import monitor
import notifier

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "10"))
REMINDER_INTERVAL_MINUTES = int(os.environ.get("REMINDER_INTERVAL_MINUTES", "5"))
REMINDER_RESEND_MINUTES = int(os.environ.get("REMINDER_RESEND_MINUTES", "30"))


def check_websites_job():
    """Detect website changes and send initial notifications."""
    logger.info("Running website check job …")
    try:
        changed = monitor.check_all_websites()
        for site in changed:
            # Fetch the latest alert for this site (the one just created).
            pending = [
                a
                for a in database.get_pending_alerts()
                if a["website_id"] == site["id"]
            ]
            if pending:
                alert = pending[-1]
                sent = notifier.send_whatsapp_notification(
                    url=site["url"],
                    ack_token=alert["ack_token"],
                )
                if sent:
                    database.update_alert_notified(alert["id"])
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error in check_websites_job")


def send_reminders_job():
    """Re-send notifications for alerts that have not been acknowledged."""
    logger.info("Running reminder job …")
    try:
        pending = database.get_pending_alerts()
        threshold = datetime.utcnow() - timedelta(minutes=REMINDER_RESEND_MINUTES)
        for alert in pending:
            last_notified = alert.get("last_notified")
            if last_notified:
                # Parse the stored UTC string.
                try:
                    notified_dt = datetime.fromisoformat(last_notified)
                except ValueError:
                    notified_dt = None
                if notified_dt and notified_dt > threshold:
                    # Too soon – skip this alert.
                    continue

            sent = notifier.send_reminder(
                url=alert["url"],
                ack_token=alert["ack_token"],
            )
            if sent:
                database.update_alert_notified(alert["id"])
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error in send_reminders_job")


def create_scheduler() -> BackgroundScheduler:
    """
    Create, configure, and return a :class:`BackgroundScheduler` instance.

    The scheduler is *not* started here; call ``scheduler.start()`` after
    the application has finished initialising.
    """
    scheduler = BackgroundScheduler(daemon=True)

    scheduler.add_job(
        check_websites_job,
        trigger=IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES),
        id="check_websites",
        name="Check websites for changes",
        replace_existing=True,
    )

    scheduler.add_job(
        send_reminders_job,
        trigger=IntervalTrigger(minutes=REMINDER_INTERVAL_MINUTES),
        id="send_reminders",
        name="Send reminders for unacknowledged alerts",
        replace_existing=True,
    )

    return scheduler
