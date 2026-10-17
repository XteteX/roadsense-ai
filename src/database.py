"""SQLite storage for defect reports.

The database path does not depend on the current working directory, so the
dashboard, the bot and the API all use the same file.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("ROADSENSE_DB", PROJECT_ROOT / "data" / "roadsense.db"))

COLUMNS = ["type", "lat", "lon", "size_cm", "traffic_level", "is_near_social",
           "score", "category", "explanation"]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                lat REAL,
                lon REAL,
                size_cm REAL,
                traffic_level INTEGER,
                is_near_social BOOLEAN,
                score REAL,
                category TEXT,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_defect(defect_data: dict) -> int:
    """Insert a report and return its ID."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            f"INSERT INTO defects ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            tuple(defect_data[c] for c in COLUMNS),
        )
        return cur.lastrowid


def get_defects() -> list[dict]:
    """All reports, newest last."""
    with closing(_connect()) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM defects ORDER BY id")]


def get_defect(defect_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM defects WHERE id = ?", (defect_id,)).fetchone()
        return dict(row) if row else None


def delete_defect(defect_id: int) -> bool:
    with closing(_connect()) as conn, conn:
        return conn.execute("DELETE FROM defects WHERE id = ?", (defect_id,)).rowcount > 0


def save_defect(defect_data: dict) -> int:
    """Backwards-compatible alias of :func:`add_defect`."""
    return add_defect(defect_data)
