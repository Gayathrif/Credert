"""
database.py - SQLite database handling for Credert.

Manages two tables:
  - websites: tracked URLs with their last-seen content hash and status.
  - alerts:   change events with acknowledgement state and reminder tracking.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("CREDERT_DB_PATH", "credert.db")


@contextmanager
def get_connection():
    """Yield a database connection with row_factory set to Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all required tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS websites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    NOT NULL UNIQUE,
                last_hash   TEXT,
                status      TEXT    NOT NULL DEFAULT 'active',
                created_at  DATETIME DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id    INTEGER NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
                detected_at   DATETIME DEFAULT (datetime('now')),
                acknowledged  INTEGER NOT NULL DEFAULT 0,
                ack_token     TEXT    NOT NULL UNIQUE,
                last_notified DATETIME
            );
            """
        )


# ---------------------------------------------------------------------------
# Website helpers
# ---------------------------------------------------------------------------

def add_website(url: str) -> dict:
    """Insert a new website URL. Returns the created row as a dict."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO websites (url) VALUES (?) RETURNING *", (url,)
        )
        row = cursor.fetchone()
        return dict(row)


def get_all_websites() -> list[dict]:
    """Return all websites."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM websites ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_website(website_id: int) -> dict | None:
    """Return a single website by id, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM websites WHERE id = ?", (website_id,)
        ).fetchone()
        return dict(row) if row else None


def update_website_hash(website_id: int, new_hash: str):
    """Update the stored content hash for a website."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE websites SET last_hash = ? WHERE id = ?",
            (new_hash, website_id),
        )


def delete_website(website_id: int) -> bool:
    """Delete a website (and cascade-delete its alerts). Returns True if found."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM websites WHERE id = ?", (website_id,)
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Alert helpers
# ---------------------------------------------------------------------------

def create_alert(website_id: int, ack_token: str) -> dict:
    """Create a new unacknowledged alert. Returns the created row as a dict."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO alerts (website_id, ack_token)
            VALUES (?, ?)
            RETURNING *
            """,
            (website_id, ack_token),
        )
        row = cursor.fetchone()
        return dict(row)


def get_pending_alerts() -> list[dict]:
    """Return all alerts that have not yet been acknowledged."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.*, w.url
            FROM alerts a
            JOIN websites w ON w.id = a.website_id
            WHERE a.acknowledged = 0
            ORDER BY a.detected_at
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_alerts() -> list[dict]:
    """Return all alerts with their associated URL."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.*, w.url
            FROM alerts a
            JOIN websites w ON w.id = a.website_id
            ORDER BY a.detected_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def acknowledge_alert(ack_token: str) -> bool:
    """Mark an alert as acknowledged. Returns True if a row was updated."""
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE alerts SET acknowledged = 1 WHERE ack_token = ? AND acknowledged = 0",
            (ack_token,),
        )
        return cursor.rowcount > 0


def update_alert_notified(alert_id: int):
    """Record that a reminder was just sent for an alert."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE alerts SET last_notified = datetime('now') WHERE id = ?",
            (alert_id,),
        )
