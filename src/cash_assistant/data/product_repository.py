"""Product repository."""

import sqlite3
from dataclasses import replace

from cash_assistant.core.product import Product, UnitType
from cash_assistant.data.database import transaction


class ProductRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def list_active_products(self) -> list[Product]:
        rows = self._connection.execute(
            """
            SELECT id, code, name, unit_type, price_grosze, active, sort_order,
                   icon_filename
            FROM products
            WHERE active = 1
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
        return [_row_to_product(row) for row in rows]

    def list_all_products(self) -> list[Product]:
        rows = self._connection.execute(
            """
            SELECT id, code, name, unit_type, price_grosze, active, sort_order,
                   icon_filename
            FROM products
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
        return [_row_to_product(row) for row in rows]

    def get_product(self, product_id: int) -> Product | None:
        row = self._connection.execute(
            """
            SELECT id, code, name, unit_type, price_grosze, active, sort_order,
                   icon_filename
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_product(row)

    def get_product_by_code(self, code: str) -> Product | None:
        row = self._connection.execute(
            """
            SELECT id, code, name, unit_type, price_grosze, active, sort_order,
                   icon_filename
            FROM products
            WHERE code = ?
            """,
            (code,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_product(row)

    def create_product(self, product: Product) -> Product:
        with transaction(self._connection):
            cursor = self._connection.execute(
                """
                INSERT INTO products (
                    code,
                    name,
                    unit_type,
                    price_grosze,
                    active,
                    sort_order,
                    icon_filename
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.code,
                    product.name,
                    product.unit_type.value,
                    product.price_grosze,
                    int(product.active),
                    product.sort_order,
                    product.icon_filename,
                ),
            )
        product_id = cursor.lastrowid
        if product_id is None:
            raise RuntimeError("SQLite did not return an id for the created product")
        return replace(product, id=product_id)

    def update_product(self, product: Product) -> Product:
        if product.id is None:
            raise ValueError("product id is required for update")
        current_product = self.get_product(product.id)
        if current_product is None:
            raise ValueError(f"product with id {product.id} does not exist")
        if product.code != current_product.code:
            raise ValueError("product code cannot be changed")

        with transaction(self._connection):
            cursor = self._connection.execute(
                """
                UPDATE products
                SET name = ?,
                    unit_type = ?,
                    price_grosze = ?,
                    active = ?,
                    sort_order = ?,
                    icon_filename = ?
                WHERE id = ?
                """,
                (
                    product.name,
                    product.unit_type.value,
                    product.price_grosze,
                    int(product.active),
                    product.sort_order,
                    product.icon_filename,
                    product.id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"product with id {product.id} does not exist")

        return product

    def deactivate_product(self, product_id: int) -> None:
        with transaction(self._connection):
            cursor = self._connection.execute(
                "UPDATE products SET active = 0 WHERE id = ?",
                (product_id,),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"product with id {product_id} does not exist")


def _row_to_product(row: sqlite3.Row) -> Product:
    return Product(
        id=int(row["id"]),
        code=str(row["code"]),
        name=str(row["name"]),
        unit_type=UnitType(str(row["unit_type"])),
        price_grosze=int(row["price_grosze"]),
        active=bool(row["active"]),
        sort_order=int(row["sort_order"]),
        icon_filename=str(row["icon_filename"]),
    )
