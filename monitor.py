"""
monitor.py - Website change-detection logic for Credert.

Fetches each active website's content, computes an MD5 hash, and compares it
with the previously stored hash.  When a change is detected the caller is
responsible for triggering notifications (see scheduler.py).
"""

import hashlib
import logging
import os
import uuid

import requests

import database

logger = logging.getLogger(__name__)

# Number of seconds to wait for a website response before timing out.
REQUEST_TIMEOUT = int(os.environ.get("MONITOR_TIMEOUT", "15"))


def fetch_content(url: str) -> str | None:
    """
    Download the raw text content of *url*.

    Returns the response text on success, or ``None`` when the request fails
    (network error, HTTP error, or timeout).
    """
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def compute_hash(content: str) -> str:
    """Return the SHA-256 hex-digest of *content*."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def check_website(website: dict) -> bool:
    """
    Check a single website for changes.

    Parameters
    ----------
    website:
        A row dict from ``database.get_all_websites()`` with at least the
        keys ``id``, ``url``, and ``last_hash``.

    Returns
    -------
    bool
        ``True`` if a change was detected (and an alert was created),
        ``False`` otherwise.
    """
    url = website["url"]
    content = fetch_content(url)
    if content is None:
        logger.warning("Skipping hash comparison for %s (fetch failed)", url)
        return False

    new_hash = compute_hash(content)
    old_hash = website.get("last_hash")

    # Always persist the latest hash so subsequent checks use the current
    # version as the baseline.
    database.update_website_hash(website["id"], new_hash)

    if old_hash is None:
        # First time we have seen this website – establish baseline.
        logger.info("Baseline hash stored for %s", url)
        return False

    if new_hash != old_hash:
        logger.info("Change detected for %s", url)
        ack_token = uuid.uuid4().hex
        database.create_alert(website["id"], ack_token)
        return True

    logger.debug("No change for %s", url)
    return False


def check_all_websites() -> list[dict]:
    """
    Iterate over every active website and check for changes.

    Returns
    -------
    list[dict]
        A list of website dicts for which a change was detected.
    """
    websites = database.get_all_websites()
    changed = []
    for site in websites:
        if site.get("status") != "active":
            continue
        if check_website(site):
            changed.append(site)
    return changed
