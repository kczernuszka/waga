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


def test_sale_items_product_foreign_key_uses_on_delete_set_null() -> None:
    connection = connect(":memory:")
    initialize_schema(connection)

    columns = {
        row["name"]: row for row in connection.execute("PRAGMA table_info(sale_items)")
    }
    product_foreign_key = next(
        row
        for row in connection.execute("PRAGMA foreign_key_list(sale_items)")
        if row["table"] == "products"
    )

    assert columns["product_id"]["notnull"] == 0
    assert product_foreign_key["from"] == "product_id"
    assert product_foreign_key["on_delete"] == "SET NULL"


def test_initialize_schema_migrates_legacy_sale_item_snapshots() -> None:
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
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            raw_total_grosze INTEGER NOT NULL,
            rounded_total_grosze INTEGER NOT NULL,
            paid_grosze INTEGER NOT NULL,
            change_grosze INTEGER NOT NULL
        );
        CREATE TABLE sale_items (
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
        INSERT INTO products (name, unit_type, price_grosze)
        VALUES ('Jabłka', 'kg', 699);
        INSERT INTO sales (
            created_at,
            raw_total_grosze,
            rounded_total_grosze,
            paid_grosze,
            change_grosze
        )
        VALUES ('2026-07-23T12:00:00+02:00', 699, 700, 1000, 300);
        INSERT INTO sale_items (
            sale_id,
            product_id,
            product_name_snapshot,
            unit_type_snapshot,
            unit_price_grosze_snapshot,
            quantity_value,
            line_total_grosze
        )
        VALUES (1, 1, 'Jabłka', 'kg', 699, 1000, 699);
        """
    )

    initialize_schema(connection)

    row = connection.execute(
        """
        SELECT product_id,
               product_code_snapshot,
               product_name_snapshot,
               unit_snapshot,
               unit_price_grosze_snapshot
        FROM sale_items
        WHERE id = 1
        """
    ).fetchone()
    assert row["product_id"] == 1
    assert row["product_code_snapshot"] == "jablka"
    assert row["product_name_snapshot"] == "Jabłka"
    assert row["unit_snapshot"] == "kg"
    assert row["unit_price_grosze_snapshot"] == 699

    connection.execute("DELETE FROM products WHERE id = 1")
    assert connection.execute(
        "SELECT product_id FROM sale_items WHERE id = 1"
    ).fetchone()["product_id"] is None
