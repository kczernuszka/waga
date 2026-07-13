"""Sale repository."""

import sqlite3
from dataclasses import replace
from datetime import datetime

from cash_assistant.core.product import UnitType
from cash_assistant.core.sale import Sale, SaleItem
from cash_assistant.data.database import transaction


class SaleRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def save_sale(self, sale: Sale) -> Sale:
        if not sale.items:
            raise ValueError("cannot save sale without items")

        created_at = _created_at_for_storage(sale.created_at)

        with transaction(self._connection):
            cursor = self._connection.execute(
                """
                INSERT INTO sales (
                    created_at,
                    raw_total_grosze,
                    rounded_total_grosze,
                    paid_grosze,
                    change_grosze
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at.isoformat(timespec="seconds"),
                    sale.raw_total_grosze,
                    sale.rounded_total_grosze,
                    sale.paid_grosze,
                    sale.change_grosze,
                ),
            )
            sale_id = cursor.lastrowid
            if sale_id is None:
                raise RuntimeError("SQLite did not return an id for the saved sale")

            self._connection.executemany(
                """
                INSERT INTO sale_items (
                    sale_id,
                    product_id,
                    product_name_snapshot,
                    unit_type_snapshot,
                    unit_price_grosze_snapshot,
                    quantity_value,
                    line_total_grosze
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sale_id,
                        item.product_id,
                        item.product_name_snapshot,
                        item.unit_type_snapshot.value,
                        item.unit_price_grosze_snapshot,
                        item.quantity_value,
                        item.line_total_grosze,
                    )
                    for item in sale.items
                ],
            )

        return replace(sale, id=sale_id, created_at=created_at)

    def list_recent_sales(self, limit: int = 20) -> list[Sale]:
        if limit < 0:
            raise ValueError("limit cannot be negative")

        rows = self._connection.execute(
            """
            SELECT id, created_at, raw_total_grosze, rounded_total_grosze, paid_grosze,
                   change_grosze
            FROM sales
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._sale_from_row(row) for row in rows]

    def read_sale(self, sale_id: int) -> Sale | None:
        row = self._connection.execute(
            """
            SELECT id, created_at, raw_total_grosze, rounded_total_grosze, paid_grosze,
                   change_grosze
            FROM sales
            WHERE id = ?
            """,
            (sale_id,),
        ).fetchone()
        if row is None:
            return None
        return self._sale_from_row(row)

    def _sale_from_row(self, row: sqlite3.Row) -> Sale:
        sale_id = int(row["id"])
        return Sale(
            id=sale_id,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            raw_total_grosze=int(row["raw_total_grosze"]),
            rounded_total_grosze=int(row["rounded_total_grosze"]),
            paid_grosze=int(row["paid_grosze"]),
            change_grosze=int(row["change_grosze"]),
            items=self._load_items(sale_id),
        )

    def _load_items(self, sale_id: int) -> tuple[SaleItem, ...]:
        rows = self._connection.execute(
            """
            SELECT product_id,
                   product_name_snapshot,
                   unit_type_snapshot,
                   unit_price_grosze_snapshot,
                   quantity_value,
                   line_total_grosze
            FROM sale_items
            WHERE sale_id = ?
            ORDER BY id ASC
            """,
            (sale_id,),
        ).fetchall()
        return tuple(_row_to_sale_item(row) for row in rows)


def _row_to_sale_item(row: sqlite3.Row) -> SaleItem:
    product_id = row["product_id"]
    return SaleItem(
        product_id=None if product_id is None else int(product_id),
        product_name_snapshot=str(row["product_name_snapshot"]),
        unit_type_snapshot=UnitType(str(row["unit_type_snapshot"])),
        unit_price_grosze_snapshot=int(row["unit_price_grosze_snapshot"]),
        quantity_value=int(row["quantity_value"]),
        line_total_grosze=int(row["line_total_grosze"]),
    )


def _created_at_for_storage(value: datetime) -> datetime:
    stored_text = value.isoformat(timespec="seconds")
    return datetime.fromisoformat(stored_text)
