"""scheduler.py - Timing logic for Credert using APScheduler."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

import database
import monitor
import notifier

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL = 2    # minutes between site-change checks
DEFAULT_REMINDER_INTERVAL = 5  # minutes between pending-alert reminders


def check_sites():
    """Check all monitored URLs for changes and fire alerts as needed."""
    sites = database.get_all_sites()
    for site in sites:
        url = site["url"]
        stored_hash = site["last_hash"]
        ack_token = site["ack_token"]

        changed, current_hash = monitor.check_for_change(url, stored_hash)

        if stored_hash is None:
            # First time we've seen this URL — store the baseline hash
            database.update_hash(url, current_hash)
            continue

        if changed:
            database.update_hash(url, current_hash)
            notifier.send_alert(url, ack_token)


def send_reminders():
    """Re-send alerts for all sites whose status is still 'pending'."""
    sites = database.get_all_sites()
    for site in sites:
        if site["status"] == "pending" and site["last_hash"] is not None:
            notifier.send_reminder(site["url"], site["ack_token"])


def create_scheduler(
    check_interval: int = DEFAULT_CHECK_INTERVAL,
    reminder_interval: int = DEFAULT_REMINDER_INTERVAL,
) -> BackgroundScheduler:
    """Create and configure a BackgroundScheduler with monitoring jobs."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_sites,
        "interval",
        minutes=check_interval,
        id="check_sites",
        replace_existing=True,
    )
    scheduler.add_job(
        send_reminders,
        "interval",
        minutes=reminder_interval,
        id="send_reminders",
        replace_existing=True,
    )
    return scheduler
