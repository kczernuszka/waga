import sqlite3
from pathlib import Path

from cash_assistant.data.database import connect, initialize_database, initialize_schema


def test_initialize_database_creates_mvp_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "cash_assistant.sqlite3"

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert {"products", "sales", "sale_items"}.issubset(table_names)


def test_connect_enables_foreign_keys_and_row_access() -> None:
    connection = connect(":memory:")
    initialize_schema(connection)

    foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'products'
        """
    ).fetchone()

    assert foreign_keys_enabled == 1
    assert row["name"] == "products"
