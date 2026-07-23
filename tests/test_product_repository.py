import sqlite3

import pytest

from cash_assistant.core.product import Product, UnitType
from cash_assistant.data.database import initialize_schema
from cash_assistant.data.product_repository import ProductRepository


@pytest.fixture
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    return connection


def test_create_product_returns_product_with_database_id(
    connection: sqlite3.Connection,
) -> None:
    repository = ProductRepository(connection)

    product = repository.create_product(
        Product(
            id=None,
            code="jablka",
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=699,
            active=True,
            sort_order=10,
        )
    )

    assert product == Product(
        id=1,
        code="jablka",
        name="Jabłka",
        unit_type=UnitType.KG,
        price_grosze=699,
        active=True,
        sort_order=10,
    )


def test_list_products_orders_by_sort_order_then_id(
    connection: sqlite3.Connection,
) -> None:
    repository = ProductRepository(connection)
    second = repository.create_product(
        Product(
            id=None,
            code="gruszki",
            name="Gruszki",
            unit_type=UnitType.KG,
            price_grosze=899,
            sort_order=20,
        )
    )
    first = repository.create_product(
        Product(
            id=None,
            code="bulka",
            name="Bułka",
            unit_type=UnitType.PIECE,
            price_grosze=120,
            sort_order=10,
        )
    )

    assert repository.list_all_products() == [first, second]
    assert repository.list_active_products() == [first, second]


def test_deactivate_product_hides_it_from_active_list(
    connection: sqlite3.Connection,
) -> None:
    repository = ProductRepository(connection)
    active = repository.create_product(
        Product(None, "bulka", "Bułka", UnitType.PIECE, 120)
    )
    inactive = repository.create_product(
        Product(None, "jablka", "Jabłka", UnitType.KG, 699)
    )

    assert inactive.id is not None
    repository.deactivate_product(inactive.id)

    assert repository.list_active_products() == [active]
    assert repository.get_product(inactive.id) == Product(
        id=inactive.id,
        code="jablka",
        name="Jabłka",
        unit_type=UnitType.KG,
        price_grosze=699,
        active=False,
        sort_order=0,
    )


def test_update_product_replaces_stored_fields(
    connection: sqlite3.Connection,
) -> None:
    repository = ProductRepository(connection)
    product = repository.create_product(
        Product(None, "jablka", "Jabłka", UnitType.KG, 699)
    )

    updated = repository.update_product(
        Product(
            id=product.id,
            code="jablka",
            name="Jabłka premium",
            unit_type=UnitType.KG,
            price_grosze=799,
            active=False,
            sort_order=5,
        )
    )

    assert repository.get_product(product.id or 0) == updated


def test_update_product_requires_id(connection: sqlite3.Connection) -> None:
    repository = ProductRepository(connection)

    with pytest.raises(ValueError):
        repository.update_product(
            Product(None, "jablka", "Jabłka", UnitType.KG, 699)
        )


def test_update_product_rejects_code_change(
    connection: sqlite3.Connection,
) -> None:
    repository = ProductRepository(connection)
    product = repository.create_product(
        Product(None, "jablka", "Jabłka", UnitType.KG, 699)
    )

    with pytest.raises(ValueError, match="product code cannot be changed"):
        repository.update_product(
            Product(
                id=product.id,
                code="new-code",
                name=product.name,
                unit_type=product.unit_type,
                price_grosze=product.price_grosze,
            )
        )
