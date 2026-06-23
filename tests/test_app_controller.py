import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cash_assistant.controller.app_controller import AppController, AppState, ViewState
from cash_assistant.core.cart import CartItem
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import SaleItem
from cash_assistant.data.database import connect, initialize_schema
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.mock_scale import MockScale

CREATED_AT = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    database_path = tmp_path / "test.sqlite3"
    connection = connect(database_path)
    initialize_schema(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def scale() -> MockScale:
    return MockScale()


@pytest.fixture
def controller(
    connection: sqlite3.Connection,
    scale: MockScale,
) -> AppController:
    return AppController(
        scale=scale,
        product_repository=ProductRepository(connection),
        sale_repository=SaleRepository(connection),
        clock=lambda: CREATED_AT,
    )


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


def test_controller_creates_and_keeps_current_cart(controller: AppController) -> None:
    assert controller.cart.is_empty
    assert controller.prepare_view_state().is_cart_empty


def test_add_weighted_product_uses_current_scale_weight(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)

    item = controller.add_weighted_product(weighted_product())

    assert item == CartItem(
        product_id=1,
        product_name_snapshot="Jabłka",
        unit_type_snapshot=UnitType.KG,
        unit_price_grosze_snapshot=699,
        quantity_value=1_500,
        line_total_grosze=1_049,
    )
    assert controller.cart.items == (item,)


def test_add_piece_product_uses_given_quantity(controller: AppController) -> None:
    item = controller.add_piece_product(piece_product(), quantity=3)

    assert item == CartItem(
        product_id=2,
        product_name_snapshot="Bułka",
        unit_type_snapshot=UnitType.PIECE,
        unit_price_grosze_snapshot=120,
        quantity_value=3,
        line_total_grosze=360,
    )
    assert controller.cart.items == (item,)


def test_remove_last_item_removes_most_recent_item(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    first_item = controller.add_weighted_product(weighted_product())
    second_item = controller.add_piece_product(piece_product(), quantity=3)

    removed_item = controller.remove_last_item()

    assert removed_item == second_item
    assert controller.cart.items == (first_item,)


def test_clear_cart_removes_all_items(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.add_piece_product(piece_product(), quantity=3)

    controller.clear_cart()

    assert controller.cart.is_empty
    assert controller.prepare_view_state().is_cart_empty


def test_prepare_view_state_for_gui(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    item = controller.add_weighted_product(weighted_product())
    controller.set_paid_grosze(2_000)

    assert controller.prepare_view_state() == ViewState(
        app_state=AppState.PAYMENT,
        cart_items=(item,),
        technical_total_grosze=1_049,
        rounded_total_grosze=1_050,
        paid_grosze=2_000,
        change_grosze=950,
        missing_grosze=None,
        is_cart_empty=False,
    )


def test_set_paid_grosze_calculates_change_when_payment_is_enough(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())

    payment = controller.set_paid_grosze(2_000)

    assert payment.paid_grosze == 2_000
    assert payment.change_grosze == 950
    assert payment.missing_grosze is None


def test_set_paid_grosze_calculates_missing_amount_when_payment_is_too_low(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())

    payment = controller.set_paid_grosze(1_000)

    assert payment.paid_grosze == 1_000
    assert payment.change_grosze is None
    assert payment.missing_grosze == 50


def test_set_paid_grosze_rejects_negative_payment(controller: AppController) -> None:
    with pytest.raises(ValueError):
        controller.set_paid_grosze(-1)


def test_save_sale_uses_sale_repository_and_starts_new_cart(
    connection: sqlite3.Connection,
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.add_piece_product(piece_product(), quantity=3)
    controller.set_paid_grosze(2_000)

    saved_sale = controller.save_sale()

    assert saved_sale.id == 1
    assert saved_sale.created_at == CREATED_AT
    assert saved_sale.raw_total_grosze == 1_409
    assert saved_sale.rounded_total_grosze == 1_400
    assert saved_sale.paid_grosze == 2_000
    assert saved_sale.change_grosze == 600
    assert saved_sale.items == (
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
    )
    assert SaleRepository(connection).read_sale(1) == saved_sale
    assert controller.cart.is_empty
    assert controller.prepare_view_state().app_state is AppState.PRODUCT_SELECTION


def test_save_sale_requires_accepted_payment(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())

    with pytest.raises(ValueError):
        controller.save_sale()


def test_save_sale_rejects_missing_payment(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.set_paid_grosze(1_000)

    with pytest.raises(ValueError):
        controller.save_sale()


def test_product_methods_use_product_repository(controller: AppController) -> None:
    second = controller.create_product(
        Product(
            id=None,
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=699,
            sort_order=20,
        )
    )
    first = controller.create_product(
        Product(
            id=None,
            name="Bułka",
            unit_type=UnitType.PIECE,
            price_grosze=120,
            sort_order=10,
        )
    )

    assert controller.list_all_products() == [first, second]
    assert controller.list_active_products() == [first, second]

    assert second.id is not None
    updated_second = controller.update_product(
        Product(
            id=second.id,
            name="Jabłka premium",
            unit_type=UnitType.KG,
            price_grosze=799,
            active=True,
            sort_order=5,
        )
    )

    assert controller.get_product(second.id) == updated_second

    controller.deactivate_product(second.id)

    assert controller.list_active_products() == [first]
    assert controller.get_product(second.id) == Product(
        id=second.id,
        name="Jabłka premium",
        unit_type=UnitType.KG,
        price_grosze=799,
        active=False,
        sort_order=5,
    )


def test_history_methods_use_sale_repository(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.set_paid_grosze(2_000)
    first_sale = controller.save_sale()

    scale.set_weight_grams(2_000)
    controller.add_weighted_product(weighted_product())
    controller.set_paid_grosze(2_000)
    second_sale = controller.save_sale()

    assert controller.list_recent_sales(limit=1) == [second_sale]
    assert controller.list_recent_sales(limit=2) == [second_sale, first_sale]

    assert first_sale.id is not None
    assert controller.read_sale(first_sale.id) == first_sale
    assert controller.read_sale(404) is None
