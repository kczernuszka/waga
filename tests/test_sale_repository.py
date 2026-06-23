import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from cash_assistant.core.cart import Cart
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import Sale, SaleItem
from cash_assistant.data.database import initialize_schema
from cash_assistant.data.sale_repository import SaleRepository


@pytest.fixture
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def weighted_product() -> Product:
    return Product(
        id=1,
        name="Jabłka",
        unit_type=UnitType.KG,
        price_grosze=699,
    )


def piece_product() -> Product:
    return Product(
        id=2,
        name="Bułka",
        unit_type=UnitType.PIECE,
        price_grosze=120,
    )


def mixed_sale(created_at: datetime) -> Sale:
    cart = Cart()
    cart.add_weighted_product(weighted_product(), weight_grams=1_500)
    cart.add_piece_product(piece_product(), quantity=3)
    return Sale.from_cart(cart, paid_grosze=2_000, created_at=created_at)


def test_save_sale_returns_sale_with_database_id_and_keeps_items(
    connection: sqlite3.Connection,
) -> None:
    repository = SaleRepository(connection)
    sale = mixed_sale(datetime(2026, 6, 23, 12, 0, tzinfo=UTC))

    saved_sale = repository.save_sale(sale)

    assert saved_sale.id == 1
    assert saved_sale == Sale(
        id=1,
        created_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
        raw_total_grosze=1_409,
        rounded_total_grosze=1_400,
        paid_grosze=2_000,
        change_grosze=600,
        items=(
            SaleItem(
                product_id=1,
                product_name_snapshot="Jabłka",
                unit_type_snapshot=UnitType.KG,
                unit_price_grosze_snapshot=699,
                quantity_value=1_500,
                line_total_grosze=1_049,
            ),
            SaleItem(
                product_id=2,
                product_name_snapshot="Bułka",
                unit_type_snapshot=UnitType.PIECE,
                unit_price_grosze_snapshot=120,
                quantity_value=3,
                line_total_grosze=360,
            ),
        ),
    )


def test_read_sale_returns_saved_sale_with_item_snapshots(
    connection: sqlite3.Connection,
) -> None:
    repository = SaleRepository(connection)
    sale = mixed_sale(datetime(2026, 6, 23, 12, 0, tzinfo=UTC))
    saved_sale = repository.save_sale(sale)

    assert saved_sale.id is not None
    assert repository.read_sale(saved_sale.id) == saved_sale


def test_read_sale_returns_none_for_missing_sale(
    connection: sqlite3.Connection,
) -> None:
    repository = SaleRepository(connection)

    assert repository.read_sale(404) is None


def test_list_recent_sales_returns_newest_first_with_limit(
    connection: sqlite3.Connection,
) -> None:
    repository = SaleRepository(connection)
    older = repository.save_sale(mixed_sale(datetime(2026, 6, 23, 12, 0, tzinfo=UTC)))
    newer = repository.save_sale(
        mixed_sale(datetime(2026, 6, 23, 12, 0, tzinfo=UTC) + timedelta(minutes=5))
    )

    assert repository.list_recent_sales(limit=1) == [newer]
    assert repository.list_recent_sales(limit=2) == [newer, older]


def test_save_sale_rejects_sale_without_items(
    connection: sqlite3.Connection,
) -> None:
    repository = SaleRepository(connection)
    sale = Sale(
        id=None,
        created_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
        raw_total_grosze=0,
        rounded_total_grosze=0,
        paid_grosze=0,
        change_grosze=0,
        items=(),
    )

    with pytest.raises(ValueError):
        repository.save_sale(sale)


def test_save_sale_rolls_back_sale_when_saving_items_fails(
    connection: sqlite3.Connection,
) -> None:
    connection.execute("DROP TABLE sale_items")
    connection.execute(
        """
        CREATE TABLE sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name_snapshot TEXT NOT NULL,
            unit_type_snapshot TEXT NOT NULL,
            unit_price_grosze_snapshot INTEGER NOT NULL,
            quantity_value INTEGER NOT NULL CHECK (quantity_value < 0),
            line_total_grosze INTEGER NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id)
        )
        """
    )
    connection.commit()
    repository = SaleRepository(connection)
    sale = mixed_sale(datetime(2026, 6, 23, 12, 0, tzinfo=UTC))

    with pytest.raises(sqlite3.IntegrityError):
        repository.save_sale(sale)

    sales_count = connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    sale_items_count = connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0]
    assert sales_count == 0
    assert sale_items_count == 0
