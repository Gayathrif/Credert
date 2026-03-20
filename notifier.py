"""
notifier.py - WhatsApp notification delivery via Twilio for Credert.

Configuration (environment variables):
  TWILIO_ACCOUNT_SID   – Twilio account SID
  TWILIO_AUTH_TOKEN    – Twilio auth token
  TWILIO_WHATSAPP_FROM – sender number, e.g. "whatsapp:+14155238886"
  NOTIFY_WHATSAPP_TO   – recipient number, e.g. "whatsapp:+1234567890"
  APP_BASE_URL         – publicly reachable base URL, e.g. "https://example.com"
                         Used to build the acknowledgement link.
"""

import logging
import os

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
NOTIFY_WHATSAPP_TO = os.environ.get("NOTIFY_WHATSAPP_TO", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")


def _get_twilio_client():
    """
    Return an authenticated Twilio REST client.

    Raises ``RuntimeError`` when the required credentials are not configured.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError(
            "Twilio credentials not configured. "
            "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables."
        )
    # Import lazily so the rest of the application works without the twilio
    # package installed (e.g. during local development / testing).
    from twilio.rest import Client  # type: ignore[import-untyped]

    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def build_ack_url(ack_token: str) -> str:
    """Return the full acknowledgement URL for *ack_token*."""
    return f"{APP_BASE_URL.rstrip('/')}/acknowledge/{ack_token}"


def send_whatsapp_notification(url: str, ack_token: str) -> bool:
    """
    Send a WhatsApp alert for a detected change on *url*.

    Parameters
    ----------
    url:        The website URL where a change was detected.
    ack_token:  Unique token for the acknowledgement link.

    Returns
    -------
    bool
        ``True`` on success, ``False`` when the message could not be sent.
    """
    if not NOTIFY_WHATSAPP_TO:
        logger.error(
            "NOTIFY_WHATSAPP_TO is not set – cannot send WhatsApp notification."
        )
        return False

    ack_url = build_ack_url(ack_token)
    body = (
        f"🔔 *Credert Alert*\n\n"
        f"A change was detected on:\n{url}\n\n"
        f"Click the link below to acknowledge this alert:\n{ack_url}"
    )

    try:
        client = _get_twilio_client()
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=NOTIFY_WHATSAPP_TO,
            body=body,
        )
        logger.info(
            "WhatsApp notification sent (SID: %s) for %s", message.sid, url
        )
        return True
    except RuntimeError as exc:
        logger.error("Twilio configuration error: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send WhatsApp notification for %s: %s", url, exc)
        return False


def send_reminder(url: str, ack_token: str) -> bool:
    """
    Send a reminder WhatsApp message for an unacknowledged alert.

    Functionally identical to :func:`send_whatsapp_notification` but uses a
    slightly different message body to indicate it is a follow-up.
    """
    if not NOTIFY_WHATSAPP_TO:
        logger.error(
            "NOTIFY_WHATSAPP_TO is not set – cannot send WhatsApp reminder."
        )
        return False

    ack_url = build_ack_url(ack_token)
    body = (
        f"⏰ *Credert Reminder*\n\n"
        f"You have not yet acknowledged the change detected on:\n{url}\n\n"
        f"Please acknowledge here:\n{ack_url}"
    )

    try:
        client = _get_twilio_client()
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=NOTIFY_WHATSAPP_TO,
            body=body,
        )
        logger.info(
            "WhatsApp reminder sent (SID: %s) for %s", message.sid, url
        )
        return True
    except RuntimeError as exc:
        logger.error("Twilio configuration error: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send WhatsApp reminder for %s: %s", url, exc)
        return False
