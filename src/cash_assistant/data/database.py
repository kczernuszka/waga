"""SQLite connection and schema helpers."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    price_grosze INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    raw_total_grosze INTEGER NOT NULL,
    rounded_total_grosze INTEGER NOT NULL,
    paid_grosze INTEGER NOT NULL,
    change_grosze INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER,
    product_name_snapshot TEXT NOT NULL,
    unit_type_snapshot TEXT NOT NULL,
    unit_price_grosze_snapshot INTEGER NOT NULL,
    quantity_value INTEGER NOT NULL,
    line_total_grosze INTEGER NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id)
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection configured for this application."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the MVP schema on an existing connection."""
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def initialize_database(database_path: str | Path) -> None:
    """Create or update the application database at the given path."""
    with connect(database_path) as connection:
        initialize_schema(connection)


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run statements in a transaction, rolling back on failure."""
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
