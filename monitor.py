"""monitor.py - Website change detection using MD5 hashing."""

import hashlib
import logging

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15  # seconds


def fetch_content(url: str) -> str:
    """Fetch the text content of a URL.

    Raises:
        requests.RequestException: on network or HTTP errors.
    """
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def compute_hash(content: str) -> str:
    """Return the MD5 hex-digest of *content*."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def check_for_change(url: str, stored_hash: str | None) -> tuple[bool, str]:
    """Check whether *url* has changed since *stored_hash* was recorded.

    Returns:
        (changed, current_hash) where *changed* is True when the page
        content differs from *stored_hash* (or when there was no previous
        hash).
    """
    try:
        content = fetch_content(url)
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        # Return no change so we don't flood alerts on transient errors
        return False, stored_hash or ""

    current_hash = compute_hash(content)
    if stored_hash is None:
        logger.info("First check for %s — storing initial hash.", url)
        return False, current_hash

    changed = current_hash != stored_hash
    if changed:
        logger.info("Change detected for %s", url)
    return changed, current_hash
