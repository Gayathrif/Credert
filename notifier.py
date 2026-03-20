"""notifier.py - Alert and reminder notifications for Credert."""

import logging
import os

logger = logging.getLogger(__name__)


def send_alert(url: str, ack_token: str):
    """Send an initial change-detected alert for *url*.

    Prints to the console and, when Twilio credentials are configured,
    also sends a WhatsApp message via Twilio.
    """
    ack_url = _build_ack_url(ack_token)
    message = (
        f"[Credert] ALERT: Changes detected on {url}\n"
        f"Acknowledge here: {ack_url}"
    )
    logger.warning(message)
    print(message)
    _send_whatsapp(message)


def send_reminder(url: str, ack_token: str):
    """Send a reminder alert for an unacknowledged change on *url*."""
    ack_url = _build_ack_url(ack_token)
    message = (
        f"[Credert] REMINDER: Changes on {url} are still unacknowledged.\n"
        f"Acknowledge here: {ack_url}"
    )
    logger.warning(message)
    print(message)
    _send_whatsapp(message)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_ack_url(token: str) -> str:
    """Return the acknowledgment URL for *token*."""
    base = os.getenv("CREDERT_BASE_URL", "http://localhost:5000")
    return f"{base}/acknowledge/{token}"


def _send_whatsapp(message: str):
    """Send *message* via Twilio WhatsApp if credentials are available."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    to_number = os.getenv("TWILIO_WHATSAPP_TO")

    if not all([account_sid, auth_token, to_number]):
        return  # Twilio not configured — skip silently

    try:
        from twilio.rest import Client  # type: ignore[import-untyped]

        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        logger.info("WhatsApp notification sent.")
    except ImportError:
        logger.warning("twilio package not installed; WhatsApp notifications disabled.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send WhatsApp notification: %s", exc)
