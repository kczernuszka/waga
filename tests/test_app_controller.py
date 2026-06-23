import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cash_assistant.controller.app_controller import AppController, AppState, ViewState
from cash_assistant.controller.labels import PRODUCT_ACTIVE_TEXT, PRODUCT_INACTIVE_TEXT
from cash_assistant.controller.view_state import (
    CartItemViewState,
    ProductEditInput,
    ProductEditViewState,
    ProductListItemViewState,
    ProductViewState,
    UnitOptionViewState,
)
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


def test_select_product_by_id_adds_weighted_product_for_gui(
    controller: AppController,
    scale: MockScale,
) -> None:
    product = controller.create_product(
        Product(
            id=None,
            name="Gruszki",
            unit_type=UnitType.KG,
            price_grosze=899,
        )
    )
    assert product.id is not None
    scale.set_weight_grams(1_000)

    item = controller.select_product_by_id(product.id)

    assert item == CartItem(
        product_id=product.id,
        product_name_snapshot="Gruszki",
        unit_type_snapshot=UnitType.KG,
        unit_price_grosze_snapshot=899,
        quantity_value=1_000,
        line_total_grosze=899,
    )
    assert controller.prepare_view_state().app_state is AppState.CART_REVIEW


def test_select_product_by_id_enters_quantity_for_piece_product(
    controller: AppController,
) -> None:
    product = controller.create_product(
        Product(
            id=None,
            name="Bulka",
            unit_type=UnitType.PIECE,
            price_grosze=120,
        )
    )
    assert product.id is not None

    result = controller.select_product_by_id(product.id)
    item = controller.add_selected_piece_product(quantity=3)

    assert result is None
    assert item == CartItem(
        product_id=product.id,
        product_name_snapshot="Bulka",
        unit_type_snapshot=UnitType.PIECE,
        unit_price_grosze_snapshot=120,
        quantity_value=3,
        line_total_grosze=360,
    )


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
    controller.add_weighted_product(weighted_product())
    controller.start_payment()
    controller.set_paid_grosze(2_000)

    assert controller.prepare_view_state() == ViewState(
        app_state=AppState.PAYMENT,
        products=(),
        cart_items=(
            CartItemViewState(
                product_id=1,
                product_name="Jabłka",
                unit_price_text="6,99 zł/kg",
                quantity_text="1,50 kg",
                line_total_text="10,49 zł",
            ),
        ),
        technical_total_grosze=1_049,
        technical_total_text="10,49 zł",
        rounded_total_grosze=1_050,
        rounded_total_text="10,50 zł",
        paid_grosze=2_000,
        paid_text="20,00 zł",
        change_grosze=950,
        change_text="9,50 zł",
        missing_grosze=None,
        missing_text=None,
        is_cart_empty=False,
    )


def test_set_paid_grosze_calculates_change_when_payment_is_enough(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.start_payment()

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
    controller.start_payment()

    payment = controller.set_paid_grosze(1_000)

    assert payment.paid_grosze == 1_000
    assert payment.change_grosze is None
    assert payment.missing_grosze == 50


def test_set_paid_grosze_rejects_negative_payment(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.start_payment()

    with pytest.raises(ValueError):
        controller.set_paid_grosze(-1)


def test_start_payment_empty_cart_raises(controller: AppController) -> None:
    with pytest.raises(ValueError):
        controller.start_payment()


def test_set_paid_without_start_payment_raises(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())

    with pytest.raises(ValueError):
        controller.set_paid_grosze(2_000)


def test_start_payment_with_non_empty_cart_enters_payment_mode(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())

    controller.start_payment()

    assert controller.prepare_view_state().app_state is AppState.PAYMENT


def test_set_paid_after_start_payment_updates_state(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.start_payment()

    payment = controller.set_paid_grosze(2_000)

    view_state = controller.prepare_view_state()
    assert view_state.app_state is AppState.PAYMENT
    assert view_state.paid_grosze == payment.paid_grosze
    assert view_state.change_grosze == payment.change_grosze
    assert view_state.missing_grosze == payment.missing_grosze


def test_save_sale_uses_sale_repository_and_starts_new_cart(
    connection: sqlite3.Connection,
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.add_piece_product(piece_product(), quantity=3)
    controller.start_payment()
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
    controller.start_payment()
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
    assert first.id is not None
    assert second.id is not None
    assert controller.prepare_view_state().products == (
        ProductViewState(
            product_id=first.id,
            name="Bułka",
            price_text="1,20 zł/szt.",
            unit_text="szt.",
            button_text="Bułka\n1,20 zł/szt.",
        ),
        ProductViewState(
            product_id=second.id,
            name="Jabłka",
            price_text="6,99 zł/kg",
            unit_text="kg",
            button_text="Jabłka\n6,99 zł/kg",
        ),
    )

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


def test_settings_product_list_returns_view_states_not_products(
    controller: AppController,
) -> None:
    first = controller.create_product(
        Product(
            id=None,
            name="Roll",
            unit_type=UnitType.PIECE,
            price_grosze=120,
            sort_order=10,
        )
    )
    second = controller.create_product(
        Product(
            id=None,
            name="Apples",
            unit_type=UnitType.KG,
            price_grosze=699,
            active=False,
            sort_order=20,
        )
    )
    assert first.id is not None
    assert second.id is not None

    products = controller.list_products_for_settings()

    assert len(products) == 2
    assert all(isinstance(product, ProductListItemViewState) for product in products)
    assert all(not isinstance(product, Product) for product in products)
    assert products[0].product_id == first.id
    assert products[0].name == "Roll"
    assert products[0].unit_code == "piece"
    assert products[0].unit_text == "szt."
    assert products[0].price_grosze == 120
    assert products[0].price_text.endswith("/szt.")
    assert products[0].active
    assert products[0].active_text == PRODUCT_ACTIVE_TEXT
    assert products[0].sort_order == 10
    assert products[1].product_id == second.id
    assert products[1].name == "Apples"
    assert products[1].unit_code == "kg"
    assert products[1].unit_text == "kg"
    assert products[1].price_grosze == 699
    assert products[1].price_text.endswith("/kg")
    assert not products[1].active
    assert products[1].active_text == PRODUCT_INACTIVE_TEXT
    assert products[1].sort_order == 20


def test_settings_new_product_edit_view_state_uses_primitives(
    controller: AppController,
) -> None:
    view_state = controller.prepare_product_edit_view_state()

    assert view_state == ProductEditViewState(
        product_id=None,
        name="",
        unit_code="kg",
        price_grosze=0,
        active=True,
        sort_order=0,
        unit_options=(
            UnitOptionViewState(unit_code="kg", label="kg"),
            UnitOptionViewState(unit_code="piece", label="szt."),
        ),
    )
    assert not isinstance(view_state, Product)


def test_settings_existing_product_edit_view_state_uses_primitives(
    controller: AppController,
) -> None:
    product = controller.create_product(
        Product(
            id=None,
            name="Roll",
            unit_type=UnitType.PIECE,
            price_grosze=120,
            active=False,
            sort_order=10,
        )
    )
    assert product.id is not None

    view_state = controller.prepare_product_edit_view_state(product.id)

    assert view_state == ProductEditViewState(
        product_id=product.id,
        name="Roll",
        unit_code="piece",
        price_grosze=120,
        active=False,
        sort_order=10,
        unit_options=(
            UnitOptionViewState(unit_code="kg", label="kg"),
            UnitOptionViewState(unit_code="piece", label="szt."),
        ),
    )
    assert not isinstance(view_state, Product)


def test_settings_save_product_input_maps_primitives_to_domain_model(
    controller: AppController,
) -> None:
    created = controller.save_product_from_input(
        ProductEditInput(
            product_id=None,
            name="Roll",
            unit_code="piece",
            price_grosze=120,
            active=True,
            sort_order=10,
        )
    )
    assert created.product_id is not None
    assert not isinstance(created, Product)
    assert controller.get_product(created.product_id) == Product(
        id=created.product_id,
        name="Roll",
        unit_type=UnitType.PIECE,
        price_grosze=120,
        active=True,
        sort_order=10,
    )

    updated = controller.save_product_from_input(
        ProductEditInput(
            product_id=created.product_id,
            name="Apples",
            unit_code="kg",
            price_grosze=699,
            active=False,
            sort_order=5,
        )
    )

    assert updated == ProductEditViewState(
        product_id=created.product_id,
        name="Apples",
        unit_code="kg",
        price_grosze=699,
        active=False,
        sort_order=5,
        unit_options=(
            UnitOptionViewState(unit_code="kg", label="kg"),
            UnitOptionViewState(unit_code="piece", label="szt."),
        ),
    )
    assert controller.get_product(created.product_id) == Product(
        id=created.product_id,
        name="Apples",
        unit_type=UnitType.KG,
        price_grosze=699,
        active=False,
        sort_order=5,
    )


def test_history_methods_use_sale_repository(
    controller: AppController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    controller.add_weighted_product(weighted_product())
    controller.start_payment()
    controller.set_paid_grosze(2_000)
    first_sale = controller.save_sale()

    scale.set_weight_grams(2_000)
    controller.add_weighted_product(weighted_product())
    controller.start_payment()
    controller.set_paid_grosze(2_000)
    second_sale = controller.save_sale()

    assert controller.list_recent_sales(limit=1) == [second_sale]
    assert controller.list_recent_sales(limit=2) == [second_sale, first_sale]

    assert first_sale.id is not None
    assert controller.read_sale(first_sale.id) == first_sale
    assert controller.read_sale(404) is None
