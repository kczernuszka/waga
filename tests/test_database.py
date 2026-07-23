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


def test_initialize_schema_adds_product_csv_columns_and_unique_code() -> None:
    connection = connect(":memory:")
    initialize_schema(connection)

    column_names = {
        row["name"] for row in connection.execute("PRAGMA table_info(products)")
    }
    indexes = {
        row["name"]: bool(row["unique"])
        for row in connection.execute("PRAGMA index_list(products)")
    }

    assert {"code", "icon_filename"}.issubset(column_names)
    assert indexes["products_code_unique"] is True


def test_initialize_schema_migrates_existing_products_without_duplicates() -> None:
    connection = connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit_type TEXT NOT NULL,
            price_grosze INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        INSERT INTO products (name, unit_type, price_grosze)
        VALUES ('Jabłka', 'kg', 699);
        """
    )

    initialize_schema(connection)

    row = connection.execute(
        "SELECT code, icon_filename FROM products WHERE id = 1"
    ).fetchone()
    assert row["code"] == "jablka"
    assert row["icon_filename"] == "fallback.png"
