import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from cash_assistant.core.cart import Cart
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import Sale
from cash_assistant.data.database import initialize_schema
from cash_assistant.data.product_csv_sync import synchronize_products_from_csv
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository

CSV_HEADER = "code,name,unit,price_grosze,active,sort_order,icon_filename\n"
POLAND_TIME_ZONE = ZoneInfo("Europe/Warsaw")


@pytest.fixture
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_synchronize_products_imports_all_csv_fields(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    csv_path = _write_csv(
        tmp_path,
        "jablka,Jabłka,kg,699,true,10,jabłka.png\n"
        "kukurydza,Kukurydza,szt,250,false,20,kukurydza.png\n",
    )

    imported_count = synchronize_products_from_csv(connection, csv_path)

    assert imported_count == 2
    assert ProductRepository(connection).list_all_products() == [
        Product(
            id=1,
            code="jablka",
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=699,
            active=True,
            sort_order=10,
            icon_filename="jabłka.png",
        ),
        Product(
            id=2,
            code="kukurydza",
            name="Kukurydza",
            unit_type=UnitType.PIECE,
            price_grosze=250,
            active=False,
            sort_order=20,
            icon_filename="kukurydza.png",
        ),
    ]


def test_synchronize_products_updates_by_code_and_preserves_id(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repository = ProductRepository(connection)
    existing = repository.create_product(
        Product(
            id=None,
            code="jablka",
            name="Stara nazwa",
            unit_type=UnitType.KG,
            price_grosze=500,
        )
    )
    csv_path = _write_csv(
        tmp_path,
        "jablka,Jabłka premium,kg,799,false,7,jabłka.png\n",
    )

    synchronize_products_from_csv(connection, csv_path)

    assert repository.get_product_by_code("jablka") == Product(
        id=existing.id,
        code="jablka",
        name="Jabłka premium",
        unit_type=UnitType.KG,
        price_grosze=799,
        active=False,
        sort_order=7,
        icon_filename="jabłka.png",
    )


def test_synchronize_products_removes_products_missing_from_csv(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repository = ProductRepository(connection)
    missing_from_csv = repository.create_product(
        Product(
            id=None,
            code="gruszki",
            name="Gruszki",
            unit_type=UnitType.KG,
            price_grosze=800,
        )
    )
    csv_path = _write_csv(
        tmp_path,
        "jablka,Jabłka,kg,699,true,10,jabłka.png\n",
    )

    synchronize_products_from_csv(connection, csv_path)

    assert missing_from_csv.id is not None
    assert repository.get_product_by_code("gruszki") is None
    assert repository.get_product(missing_from_csv.id) is None


def test_synchronize_products_hides_product_when_active_is_false(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    csv_path = _write_csv(
        tmp_path,
        "jablka,Jabłka,kg,699,false,10,jabłka.png\n",
    )

    synchronize_products_from_csv(connection, csv_path)

    repository = ProductRepository(connection)
    assert repository.list_active_products() == []
    assert repository.get_product_by_code("jablka") is not None


def test_synchronize_products_deletes_product_but_preserves_sale_item_snapshots(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    product_repository = ProductRepository(connection)
    product = product_repository.create_product(
        Product(
            id=None,
            code="jablka",
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=699,
        )
    )
    cart = Cart()
    cart.add_weighted_product(product, weight_grams=1_500)
    saved_sale = SaleRepository(connection).save_sale(
        Sale.from_cart(
            cart,
            paid_grosze=2_000,
            created_at=datetime(2026, 7, 23, 12, 0, tzinfo=POLAND_TIME_ZONE),
        )
    )
    csv_path = _write_csv(
        tmp_path,
        "gruszki,Gruszki,kg,899,true,10,gruszki.png\n",
    )

    synchronize_products_from_csv(connection, csv_path)

    assert product_repository.get_product_by_code("jablka") is None
    row = connection.execute(
        """
        SELECT product_id,
               product_code_snapshot,
               product_name_snapshot,
               unit_snapshot,
               unit_price_grosze_snapshot
        FROM sale_items
        WHERE sale_id = ?
        """,
        (saved_sale.id,),
    ).fetchone()
    assert row is not None
    assert row["product_id"] is None
    assert row["product_code_snapshot"] == "jablka"
    assert row["product_name_snapshot"] == "Jabłka"
    assert row["unit_snapshot"] == "kg"
    assert row["unit_price_grosze_snapshot"] == 699

    assert saved_sale.id is not None
    historical_sale = SaleRepository(connection).read_sale(saved_sale.id)
    assert historical_sale is not None
    assert len(historical_sale.items) == 1
    historical_item = historical_sale.items[0]
    assert historical_item.product_id is None
    assert historical_item.product_code_snapshot == "jablka"
    assert historical_item.product_name_snapshot == "Jabłka"
    assert historical_item.unit_snapshot is UnitType.KG
    assert historical_item.unit_price_grosze_snapshot == 699


@pytest.mark.parametrize(
    "csv_text, expected_message",
    [
        (
            "code,name,unit,price_grosze,active,sort_order\n"
            "jablka,Jabłka,kg,699,true,10\n",
            "missing required columns: icon_filename",
        ),
        (
            CSV_HEADER + "jablka,,kg,699,true,10,jabłka.png\n",
            "name is required",
        ),
        (
            CSV_HEADER + "jablka,Jabłka,litry,699,true,10,jabłka.png\n",
            "unit must be 'kg' or 'szt'",
        ),
        (
            CSV_HEADER + "jablka,Jabłka,kg,0,true,10,jabłka.png\n",
            "price_grosze must be greater than zero",
        ),
        (
            CSV_HEADER
            + "jablka,Jabłka,kg,699,true,10,jabłka.png\n"
            + "jablka,Inne jabłka,kg,799,true,20,jabłka.png\n",
            "duplicate product code",
        ),
        (
            CSV_HEADER + "jablka,Jabłka,kg,699,true,-1,jabłka.png\n",
            "sort_order cannot be negative",
        ),
        (
            CSV_HEADER + "jablka,Jabłka,kg,699,yes,10,jabłka.png\n",
            "active must be 'true' or 'false'",
        ),
    ],
)
def test_synchronize_products_validates_complete_file_before_writing(
    connection: sqlite3.Connection,
    tmp_path: Path,
    csv_text: str,
    expected_message: str,
) -> None:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    with pytest.raises(ValueError, match=expected_message):
        synchronize_products_from_csv(connection, csv_path)

    assert ProductRepository(connection).list_all_products() == []


def test_synchronize_products_rolls_back_all_upserts_when_write_fails(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    connection.execute(
        """
        CREATE TRIGGER reject_second_product
        BEFORE INSERT ON products
        WHEN NEW.code = 'broken'
        BEGIN
            SELECT RAISE(ABORT, 'simulated write failure');
        END
        """
    )
    connection.commit()
    csv_path = _write_csv(
        tmp_path,
        "valid,Poprawny,kg,699,true,10,jabłka.png\n"
        "broken,Błędny,szt,100,true,20,kukurydza.png\n",
    )

    with pytest.raises(sqlite3.IntegrityError, match="simulated write failure"):
        synchronize_products_from_csv(connection, csv_path)

    assert ProductRepository(connection).list_all_products() == []


def test_synchronize_products_rolls_back_updates_when_delete_fails(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    repository = ProductRepository(connection)
    retained = repository.create_product(
        Product(
            id=None,
            code="retained",
            name="Old name",
            unit_type=UnitType.KG,
            price_grosze=500,
        )
    )
    removed = repository.create_product(
        Product(
            id=None,
            code="removed",
            name="Removed",
            unit_type=UnitType.KG,
            price_grosze=600,
        )
    )
    connection.execute(
        """
        CREATE TRIGGER reject_product_delete
        BEFORE DELETE ON products
        WHEN OLD.code = 'removed'
        BEGIN
            SELECT RAISE(ABORT, 'simulated delete failure');
        END
        """
    )
    connection.commit()
    csv_path = _write_csv(
        tmp_path,
        "retained,New name,kg,700,true,10,jabłka.png\n",
    )

    with pytest.raises(sqlite3.IntegrityError, match="simulated delete failure"):
        synchronize_products_from_csv(connection, csv_path)

    assert repository.get_product_by_code("retained") == retained
    assert repository.get_product_by_code("removed") == removed


def _write_csv(tmp_path: Path, rows: str) -> Path:
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(CSV_HEADER + rows, encoding="utf-8")
    return csv_path
