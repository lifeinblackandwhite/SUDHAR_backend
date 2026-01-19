"""Database facade for Abuse Prevention package.

Re-exports helpers from `abusedb.py` so that other sub-modules can simply do
`from .database import initialize_database` without needing to know the
underlying filename. This maintains backwards-compatibility with existing
imports while keeping the original implementation unchanged.

NOTE: do *not* import this module from outside the `abuseprevention` package –
import functions directly from the public package API instead.
"""

import os
from typing import Generator

import psycopg2
from psycopg2.extensions import connection as _PGConnection
from app.core.config import DATABASE_URL  # uses project-wide env var

try:
    from .abusedb import create_abuse_prevention_tables, initialize_database  # noqa: E402
except ImportError:
    # Allow absolute import when package is executed as top-level module in tests
    from abuseprevention.abusedb import create_abuse_prevention_tables, initialize_database

__all__ = [
    "create_abuse_prevention_tables",
    "initialize_database",
    "get_pg_connection",
    "pg_connection_ctx",
    "create_abuse_prevention_tables_pg",

]


def get_pg_connection() -> _PGConnection:
    """Return a blocking psycopg2 connection to the configured Postgres DB."""
    return psycopg2.connect(DATABASE_URL)


def pg_connection_ctx() -> Generator[_PGConnection, None, None]:
    """Context-manager style generator for *with* statements.

    Example::

        with pg_connection_ctx() as conn:
            cursor = conn.cursor()
            ...
    """
    conn = get_pg_connection()
    try:
        yield conn
    finally:
        conn.close()


def create_abuse_prevention_tables_pg(conn: _PGConnection) -> None:
    """Create schema in PostgreSQL using explicit SQL dialect."""
    cur = conn.cursor()

    # Reports
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            phash TEXT NOT NULL,
            validation_score INTEGER NOT NULL,
            classification TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            verification_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ,
            assigned_official_id TEXT,
            resolution_notes TEXT
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_phash ON reports(phash);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_location ON reports(latitude, longitude);")

    # Verifications
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            verification_id SERIAL PRIMARY KEY,
            report_id TEXT NOT NULL REFERENCES reports(report_id),
            verifier_id TEXT NOT NULL,
            verification_phash TEXT NOT NULL,
            similarity_score REAL NOT NULL,
            comment TEXT,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_verifications_report ON verifications(report_id);")

    # Image metadata
    cur.execute("""
        CREATE TABLE IF NOT EXISTS image_metadata (
            metadata_id SERIAL PRIMARY KEY,
            report_id TEXT NOT NULL REFERENCES reports(report_id),
            image_type TEXT NOT NULL,
            exif_datetime TEXT,
            exif_make TEXT,
            exif_model TEXT,
            exif_software TEXT,
            gps_latitude DOUBLE PRECISION,
            gps_longitude DOUBLE PRECISION,
            gps_accuracy REAL,
            file_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)

    # Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            phone_number TEXT UNIQUE NOT NULL,
            name TEXT,
            email TEXT,
            role TEXT DEFAULT 'CITIZEN',
            reputation_score INTEGER DEFAULT 100,
            reports_submitted INTEGER DEFAULT 0,
            verifications_completed INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL,
            last_login TIMESTAMPTZ,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Officials
    cur.execute("""
        CREATE TABLE IF NOT EXISTS officials (
            official_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            assigned_zone TEXT,
            reports_resolved INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Notifications
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            related_report_id TEXT REFERENCES reports(report_id),
            is_read BOOLEAN DEFAULT FALSE,
            priority TEXT DEFAULT 'NORMAL',
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);")

    # Abuse logs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS abuse_logs (
            log_id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            abuse_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            details TEXT,
            report_id TEXT REFERENCES reports(report_id),
            action_taken TEXT,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)

    conn.commit()


__all__ = [
    "create_abuse_prevention_tables",
    "initialize_database",
]
