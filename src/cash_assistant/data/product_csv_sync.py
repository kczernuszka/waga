"""Validated, transactional product synchronization from CSV."""

import csv
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cash_assistant.core.product import UnitType
from cash_assistant.data.database import transaction

REQUIRED_COLUMNS = (
    "code",
    "name",
    "unit",
    "price_grosze",
    "active",
    "sort_order",
    "icon_filename",
)

_UNIT_TYPE_BY_CSV_VALUE = {
    "kg": UnitType.KG,
    "szt": UnitType.PIECE,
}


@dataclass(frozen=True)
class ProductCsvRecord:
    code: str
    name: str
    unit_type: UnitType
    price_grosze: int
    active: bool
    sort_order: int
    icon_filename: str


def synchronize_products_from_csv(
    connection: sqlite3.Connection,
    csv_path: str | Path,
) -> int:
    """Validate the complete file and upsert all records in one transaction."""
    records = read_product_csv(csv_path)

    with transaction(connection):
        for record in records:
            connection.execute(
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
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    unit_type = excluded.unit_type,
                    price_grosze = excluded.price_grosze,
                    active = excluded.active,
                    sort_order = excluded.sort_order,
                    icon_filename = excluded.icon_filename
                """,
                (
                    record.code,
                    record.name,
                    record.unit_type.value,
                    record.price_grosze,
                    int(record.active),
                    record.sort_order,
                    record.icon_filename,
                ),
            )

    return len(records)


def read_product_csv(csv_path: str | Path) -> tuple[ProductCsvRecord, ...]:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_headers(reader.fieldnames)

        records: list[ProductCsvRecord] = []
        used_codes: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            record = _parse_row(row, row_number)
            if record.code in used_codes:
                raise ValueError(
                    f"row {row_number}: duplicate product code {record.code!r}"
                )
            used_codes.add(record.code)
            records.append(record)

    return tuple(records)


def _validate_headers(fieldnames: Sequence[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("products CSV is missing a header row")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise ValueError(f"products CSV is missing required columns: {missing_text}")


def _parse_row(row: dict[str, str | None], row_number: int) -> ProductCsvRecord:
    values = {
        column: _required_value(row.get(column), column, row_number)
        for column in REQUIRED_COLUMNS
    }
    unit_type = _parse_unit(values["unit"], row_number)
    price_grosze = _parse_positive_int(
        values["price_grosze"], "price_grosze", row_number
    )
    active = _parse_active(values["active"], row_number)
    sort_order = _parse_non_negative_int(
        values["sort_order"], "sort_order", row_number
    )
    icon_filename = _parse_icon_filename(values["icon_filename"], row_number)

    return ProductCsvRecord(
        code=values["code"],
        name=values["name"],
        unit_type=unit_type,
        price_grosze=price_grosze,
        active=active,
        sort_order=sort_order,
        icon_filename=icon_filename,
    )


def _required_value(value: str | None, field: str, row_number: int) -> str:
    normalized = "" if value is None else value.strip()
    if not normalized:
        raise ValueError(f"row {row_number}: {field} is required")
    return normalized


def _parse_unit(value: str, row_number: int) -> UnitType:
    unit_type = _UNIT_TYPE_BY_CSV_VALUE.get(value.lower())
    if unit_type is None:
        raise ValueError(f"row {row_number}: unit must be 'kg' or 'szt'")
    return unit_type


def _parse_positive_int(value: str, field: str, row_number: int) -> int:
    parsed = _parse_int(value, field, row_number)
    if parsed <= 0:
        raise ValueError(f"row {row_number}: {field} must be greater than zero")
    return parsed


def _parse_non_negative_int(value: str, field: str, row_number: int) -> int:
    parsed = _parse_int(value, field, row_number)
    if parsed < 0:
        raise ValueError(f"row {row_number}: {field} cannot be negative")
    return parsed


def _parse_int(value: str, field: str, row_number: int) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"row {row_number}: {field} must be an integer") from error


def _parse_active(value: str, row_number: int) -> bool:
    normalized = value.lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"row {row_number}: active must be 'true' or 'false'")


def _parse_icon_filename(value: str, row_number: int) -> str:
    if Path(value).name != value or value in {".", ".."}:
        raise ValueError(f"row {row_number}: icon_filename must be a file name")
    return value
