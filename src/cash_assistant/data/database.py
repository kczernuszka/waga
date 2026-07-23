"""SQLite connection and schema helpers."""

import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    price_grosze INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    icon_filename TEXT NOT NULL DEFAULT 'fallback.png'
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
    product_code_snapshot TEXT NOT NULL,
    product_name_snapshot TEXT NOT NULL,
    unit_snapshot TEXT NOT NULL,
    unit_price_grosze_snapshot INTEGER NOT NULL,
    quantity_value INTEGER NOT NULL,
    line_total_grosze INTEGER NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
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
    _migrate_products_schema(connection)
    _migrate_sale_items_schema(connection)
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


def _migrate_products_schema(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(products)").fetchall()
    }
    if "code" not in columns:
        connection.execute("ALTER TABLE products ADD COLUMN code TEXT")
    if "icon_filename" not in columns:
        connection.execute(
            """
            ALTER TABLE products
            ADD COLUMN icon_filename TEXT NOT NULL DEFAULT 'fallback.png'
            """
        )

    rows = connection.execute(
        "SELECT id, name, code FROM products ORDER BY id"
    ).fetchall()
    used_codes = {
        str(row[2]).strip()
        for row in rows
        if row[2] is not None and str(row[2]).strip()
    }
    for product_id, name, code in rows:
        if code is not None and str(code).strip():
            continue
        generated_code = _unique_legacy_code(str(name), int(product_id), used_codes)
        connection.execute(
            "UPDATE products SET code = ? WHERE id = ?",
            (generated_code, product_id),
        )
        used_codes.add(generated_code)

    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS products_code_unique ON products(code)"
    )
    connection.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS products_code_required_on_insert
        BEFORE INSERT ON products
        WHEN NEW.code IS NULL OR trim(NEW.code) = ''
        BEGIN
            SELECT RAISE(ABORT, 'product code is required');
        END;

        CREATE TRIGGER IF NOT EXISTS products_code_required_on_update
        BEFORE UPDATE OF code ON products
        WHEN NEW.code IS NULL OR trim(NEW.code) = ''
        BEGIN
            SELECT RAISE(ABORT, 'product code is required');
        END;
        """
    )


def _unique_legacy_code(name: str, product_id: int, used_codes: set[str]) -> str:
    normalized_name = name.replace("ł", "l").replace("Ł", "L")
    ascii_name = unicodedata.normalize("NFKD", normalized_name).encode(
        "ascii", "ignore"
    ).decode("ascii")
    base_code = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    if not base_code:
        base_code = f"product-{product_id}"

    candidate = base_code
    if candidate in used_codes:
        candidate = f"{base_code}-{product_id}"
    return candidate


def _migrate_sale_items_schema(connection: sqlite3.Connection) -> None:
    column_rows = connection.execute("PRAGMA table_info(sale_items)").fetchall()
    columns = {str(row[1]): row for row in column_rows}
    foreign_keys = connection.execute("PRAGMA foreign_key_list(sale_items)").fetchall()
    has_product_set_null = any(
        str(row[2]) == "products"
        and str(row[3]) == "product_id"
        and str(row[6]).upper() == "SET NULL"
        for row in foreign_keys
    )
    product_id_is_nullable = (
        "product_id" in columns and not bool(columns["product_id"][3])
    )
    schema_is_current = (
        "product_code_snapshot" in columns
        and "unit_snapshot" in columns
        and "unit_type_snapshot" not in columns
        and product_id_is_nullable
        and has_product_set_null
    )
    if schema_is_current:
        return

    if "unit_snapshot" in columns:
        unit_expression = "si.unit_snapshot"
    elif "unit_type_snapshot" in columns:
        unit_expression = "si.unit_type_snapshot"
    else:
        raise RuntimeError("sale_items has no unit snapshot column")

    if "product_code_snapshot" in columns:
        code_expression = "NULLIF(trim(si.product_code_snapshot), '')"
    else:
        code_expression = "NULL"

    connection.execute("DROP TABLE IF EXISTS sale_items_migrated")
    connection.execute(
        """
        CREATE TABLE sale_items_migrated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER,
            product_code_snapshot TEXT NOT NULL,
            product_name_snapshot TEXT NOT NULL,
            unit_snapshot TEXT NOT NULL,
            unit_price_grosze_snapshot INTEGER NOT NULL,
            quantity_value INTEGER NOT NULL,
            line_total_grosze INTEGER NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO sale_items_migrated (
            id,
            sale_id,
            product_id,
            product_code_snapshot,
            product_name_snapshot,
            unit_snapshot,
            unit_price_grosze_snapshot,
            quantity_value,
            line_total_grosze
        )
        SELECT si.id,
               si.sale_id,
               p.id,
               COALESCE(
                   {code_expression},
                   p.code,
                   'legacy-sale-item-' || si.id
               ),
               si.product_name_snapshot,
               {unit_expression},
               si.unit_price_grosze_snapshot,
               si.quantity_value,
               si.line_total_grosze
        FROM sale_items AS si
        LEFT JOIN products AS p ON p.id = si.product_id
        """
    )
    connection.execute("DROP TABLE sale_items")
    connection.execute("ALTER TABLE sale_items_migrated RENAME TO sale_items")
