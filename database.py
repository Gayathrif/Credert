"""database.py - SQLite database logic for Credert."""

import sqlite3
import uuid
from contextlib import contextmanager

DB_PATH = "credert.db"


@contextmanager
def get_connection():
    """Context manager that yields a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monitored_sites (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                url       TEXT    NOT NULL UNIQUE,
                last_hash TEXT,
                status    TEXT    NOT NULL DEFAULT 'pending',
                ack_token TEXT    UNIQUE
            )
            """
        )


def add_site(url: str) -> int:
    """Add a new URL to monitor. Returns the row id."""
    token = str(uuid.uuid4())
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO monitored_sites (url, ack_token) VALUES (?, ?)",
            (url, token),
        )
        if cursor.lastrowid:
            return cursor.lastrowid
        # URL already exists — return existing id
        row = conn.execute(
            "SELECT id FROM monitored_sites WHERE url = ?", (url,)
        ).fetchone()
        return row["id"]


def get_all_sites():
    """Return all monitored sites as a list of Row objects."""
    with get_connection() as conn:
        return conn.execute("SELECT * FROM monitored_sites").fetchall()


def get_site_by_url(url: str):
    """Return a single site row by URL, or None."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM monitored_sites WHERE url = ?", (url,)
        ).fetchone()


def get_site_by_token(token: str):
    """Return a single site row by acknowledgment token, or None."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM monitored_sites WHERE ack_token = ?", (token,)
        ).fetchone()


def update_hash(url: str, new_hash: str):
    """Update the stored hash for a URL and reset status to 'pending'."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE monitored_sites SET last_hash = ?, status = 'pending' WHERE url = ?",
            (new_hash, url),
        )


def acknowledge(token: str) -> bool:
    """Mark a site alert as done via its ack token. Returns True if found."""
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE monitored_sites SET status = 'done' WHERE ack_token = ?",
            (token,),
        )
        return cursor.rowcount > 0


def remove_site(url: str):
    """Remove a URL from monitoring."""
    with get_connection() as conn:
        conn.execute("DELETE FROM monitored_sites WHERE url = ?", (url,))
