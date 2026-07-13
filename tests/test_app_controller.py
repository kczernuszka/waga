import inspect
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cash_assistant.controller.app_controller import AppController, AppState
from cash_assistant.controller.labels import PRODUCT_ACTIVE_TEXT, PRODUCT_INACTIVE_TEXT
from cash_assistant.controller.view_state import (
    CartItemViewState,
    ProductEditInput,
    ProductEditViewState,
    ProductListItemViewState,
    ProductViewState,
    SaleDetailsViewState,
    SaleItemViewState,
    SaleSummaryViewState,
    UnitOptionViewState,
)
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


def create_weighted_product(
    controller: AppController,
    *,
    name: str = "Apples",
    price_grosze: int = 699,
    active: bool = True,
    sort_order: int = 0,
) -> int:
    view_state = controller.save_product_from_input(
        ProductEditInput(
            product_id=None,
            name=name,
            unit_code="kg",
            price_grosze=price_grosze,
            active=active,
            sort_order=sort_order,
        )
    )
    product_id = view_state.product_id
    assert product_id is not None
    return product_id


def create_piece_product(
    controller: AppController,
    *,
    name: str = "Roll",
    price_grosze: int = 120,
    active: bool = True,
    sort_order: int = 0,
) -> int:
    view_state = controller.save_product_from_input(
        ProductEditInput(
            product_id=None,
            name=name,
            unit_code="piece",
            price_grosze=price_grosze,
            active=active,
            sort_order=sort_order,
        )
    )
    product_id = view_state.product_id
    assert product_id is not None
    return product_id


def test_public_api_does_not_expose_old_domain_methods() -> None:
    forbidden_public_names = {
        "cart",
        "list_active_products",
        "list_all_products",
        "get_product",
        "create_product",
        "update_product",
        "add_weighted_product",
        "add_piece_product",
        "add_piece_product_by_id",
        "list_recent_sales",
        "read_sale",
    }

    public_names = {name for name in dir(AppController) if not name.startswith("_")}

    assert forbidden_public_names.isdisjoint(public_names)


def test_controller_creates_and_keeps_current_cart(controller: AppController) -> None:
    view_state = controller.prepare_view_state()

    assert view_state.is_cart_empty
    assert view_state.cart_items == ()


def test_select_weighted_product_by_id_uses_current_scale_weight(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller, name="Apples", price_grosze=699)
    scale.set_weight_grams(1_500)

    view_state = controller.select_product_by_id(product_id)

    assert view_state.app_state is AppState.CART_REVIEW
    assert view_state.cart_items == (
        CartItemViewState(
            product_id=product_id,
            product_name="Apples",
            unit_price_text="6,99 zł/kg",
            quantity_text="1,50 kg",
            line_total_text="10,49 zł",
        ),
    )


def test_select_piece_product_enters_quantity_and_adds_selected_product(
    controller: AppController,
) -> None:
    product_id = create_piece_product(controller, name="Roll", price_grosze=120)

    view_state = controller.select_product_by_id(product_id)
    updated_view_state = controller.add_selected_piece_product(quantity=3)

    assert view_state.app_state is AppState.ENTERING_QUANTITY
    assert updated_view_state.app_state is AppState.CART_REVIEW
    assert updated_view_state.cart_items == (
        CartItemViewState(
            product_id=product_id,
            product_name="Roll",
            unit_price_text="1,20 zł/szt.",
            quantity_text="3 szt.",
            line_total_text="3,60 zł",
        ),
    )


def test_remove_last_item_removes_most_recent_item(
    controller: AppController,
    scale: MockScale,
) -> None:
    weighted_product_id = create_weighted_product(controller)
    piece_product_id = create_piece_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(weighted_product_id)
    controller.select_product_by_id(piece_product_id)
    controller.add_selected_piece_product(quantity=3)

    view_state = controller.remove_last_item()

    assert view_state.cart_items == (
        CartItemViewState(
            product_id=weighted_product_id,
            product_name="Apples",
            unit_price_text="6,99 zł/kg",
            quantity_text="1,50 kg",
            line_total_text="10,49 zł",
        ),
    )


def test_clear_cart_removes_all_items(
    controller: AppController,
    scale: MockScale,
) -> None:
    weighted_product_id = create_weighted_product(controller)
    piece_product_id = create_piece_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(weighted_product_id)
    controller.select_product_by_id(piece_product_id)
    controller.add_selected_piece_product(quantity=3)

    view_state = controller.clear_cart()

    assert view_state.is_cart_empty
    assert view_state.cart_items == ()


def test_prepare_view_state_for_gui(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller, name="Apples", price_grosze=699)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)
    controller.start_payment()
    controller.set_paid_grosze(2_000)

    view_state = controller.prepare_view_state()

    assert view_state.app_state is AppState.PAYMENT
    assert view_state.cart_items == (
        CartItemViewState(
            product_id=product_id,
            product_name="Apples",
            unit_price_text="6,99 zł/kg",
            quantity_text="1,50 kg",
            line_total_text="10,49 zł",
        ),
    )
    assert view_state.technical_total_grosze == 1_049
    assert view_state.technical_total_text == "10,49 zł"
    assert view_state.rounded_total_grosze == 1_050
    assert view_state.rounded_total_text == "10,50 zł"
    assert view_state.paid_grosze == 2_000
    assert view_state.paid_text == "20,00 zł"
    assert view_state.change_grosze == 950
    assert view_state.change_text == "9,50 zł"
    assert view_state.missing_grosze is None
    assert view_state.missing_text is None
    assert not view_state.is_cart_empty


def test_set_paid_grosze_calculates_change_when_payment_is_enough(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)
    controller.start_payment()

    payment = controller.set_paid_grosze(2_000)

    assert payment.paid_grosze == 2_000
    assert payment.change_grosze == 950
    assert payment.missing_grosze is None


def test_set_paid_grosze_calculates_missing_amount_when_payment_is_too_low(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)
    controller.start_payment()

    payment = controller.set_paid_grosze(1_000)

    assert payment.paid_grosze == 1_000
    assert payment.change_grosze is None
    assert payment.missing_grosze == 50


def test_set_paid_grosze_rejects_negative_payment(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)
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
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)

    with pytest.raises(ValueError):
        controller.set_paid_grosze(2_000)


def test_start_payment_with_non_empty_cart_enters_payment_mode(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)

    view_state = controller.start_payment()

    assert view_state.app_state is AppState.PAYMENT


def test_set_paid_after_start_payment_updates_state(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)
    controller.start_payment()

    payment = controller.set_paid_grosze(2_000)

    view_state = controller.prepare_view_state()
    assert view_state.app_state is AppState.PAYMENT
    assert view_state.paid_grosze == payment.paid_grosze
    assert view_state.change_grosze == payment.change_grosze
    assert view_state.missing_grosze == payment.missing_grosze


def test_save_sale_uses_sale_repository_and_starts_new_cart(
    controller: AppController,
    scale: MockScale,
) -> None:
    weighted_product_id = create_weighted_product(controller, name="Apples", price_grosze=699)
    piece_product_id = create_piece_product(controller, name="Roll", price_grosze=120)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(weighted_product_id)
    controller.select_product_by_id(piece_product_id)
    controller.add_selected_piece_product(quantity=3)
    controller.start_payment()
    controller.set_paid_grosze(2_000)

    saved_sale = controller.save_sale()

    assert saved_sale == SaleDetailsViewState(
        sale_id=1,
        created_at_text="2026-06-23 12:00",
        raw_total_grosze=1_409,
        raw_total_text="14,09 zł",
        rounded_total_grosze=1_400,
        rounded_total_text="14,00 zł",
        paid_grosze=2_000,
        paid_text="20,00 zł",
        change_grosze=600,
        change_text="6,00 zł",
        items=(
            SaleItemViewState(
                product_id=weighted_product_id,
                product_name="Apples",
                unit_price_text="6,99 zł/kg",
                quantity_text="1,50 kg",
                line_total_text="10,49 zł",
            ),
            SaleItemViewState(
                product_id=piece_product_id,
                product_name="Roll",
                unit_price_text="1,20 zł/szt.",
                quantity_text="3 szt.",
                line_total_text="3,60 zł",
            ),
        ),
    )
    assert controller.read_sale_details(1) == saved_sale
    assert controller.prepare_view_state().is_cart_empty
    assert controller.prepare_view_state().app_state is AppState.PRODUCT_SELECTION


def test_save_sale_requires_accepted_payment(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)

    with pytest.raises(ValueError):
        controller.save_sale()


def test_save_sale_rejects_missing_payment(
    controller: AppController,
    scale: MockScale,
) -> None:
    product_id = create_weighted_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(product_id)
    controller.start_payment()
    controller.set_paid_grosze(1_000)

    with pytest.raises(ValueError):
        controller.save_sale()


def test_sales_view_state_lists_active_products_for_sales(
    controller: AppController,
) -> None:
    inactive_product_id = create_weighted_product(
        controller,
        name="Inactive apples",
        price_grosze=699,
        active=False,
        sort_order=5,
    )
    first_product_id = create_piece_product(
        controller,
        name="Roll",
        price_grosze=120,
        sort_order=10,
    )
    second_product_id = create_weighted_product(
        controller,
        name="Apples",
        price_grosze=699,
        sort_order=20,
    )

    view_state = controller.prepare_view_state()

    assert view_state.products == (
        ProductViewState(
            product_id=first_product_id,
            name="Roll",
            price_text="1,20 zł/szt.",
            unit_text="szt.",
            button_text="Roll\n1,20 zł/szt.",
        ),
        ProductViewState(
            product_id=second_product_id,
            name="Apples",
            price_text="6,99 zł/kg",
            unit_text="kg",
            button_text="Apples\n6,99 zł/kg",
        ),
    )
    assert inactive_product_id not in [product.product_id for product in view_state.products]


def test_settings_product_list_returns_view_states_not_products(
    controller: AppController,
) -> None:
    first_product_id = create_piece_product(
        controller,
        name="Roll",
        price_grosze=120,
        sort_order=10,
    )
    second_product_id = create_weighted_product(
        controller,
        name="Apples",
        price_grosze=699,
        active=False,
        sort_order=20,
    )

    products = controller.list_products_for_settings()

    assert products == [
        ProductListItemViewState(
            product_id=first_product_id,
            name="Roll",
            unit_code="piece",
            unit_text="szt.",
            price_grosze=120,
            price_text="1,20 zł/szt.",
            active=True,
            active_text=PRODUCT_ACTIVE_TEXT,
            sort_order=10,
        ),
        ProductListItemViewState(
            product_id=second_product_id,
            name="Apples",
            unit_code="kg",
            unit_text="kg",
            price_grosze=699,
            price_text="6,99 zł/kg",
            active=False,
            active_text=PRODUCT_INACTIVE_TEXT,
            sort_order=20,
        ),
    ]


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


def test_settings_existing_product_edit_view_state_uses_primitives(
    controller: AppController,
) -> None:
    product_id = create_piece_product(
        controller,
        name="Roll",
        price_grosze=120,
        active=False,
        sort_order=10,
    )

    view_state = controller.prepare_product_edit_view_state(product_id)

    assert view_state == ProductEditViewState(
        product_id=product_id,
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
    assert controller.prepare_product_edit_view_state(created.product_id) == created

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
    assert controller.prepare_product_edit_view_state(created.product_id) == updated


def test_history_sale_list_returns_summary_view_states(
    controller: AppController,
    scale: MockScale,
) -> None:
    weighted_product_id = create_weighted_product(controller)
    piece_product_id = create_piece_product(controller)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(weighted_product_id)
    controller.start_payment()
    controller.set_paid_grosze(2_000)
    first_sale = controller.save_sale()

    controller.select_product_by_id(piece_product_id)
    controller.add_selected_piece_product(quantity=3)
    controller.start_payment()
    controller.set_paid_grosze(500)
    second_sale = controller.save_sale()

    sales = controller.list_sales_for_history(limit=2)

    assert sales == [
        SaleSummaryViewState(
            sale_id=second_sale.sale_id,
            created_at_text="2026-06-23 12:00",
            raw_total_grosze=360,
            raw_total_text="3,60 zł",
            rounded_total_grosze=350,
            rounded_total_text="3,50 zł",
            paid_grosze=500,
            paid_text="5,00 zł",
            change_grosze=150,
            change_text="1,50 zł",
            items_count=1,
        ),
        SaleSummaryViewState(
            sale_id=first_sale.sale_id,
            created_at_text="2026-06-23 12:00",
            raw_total_grosze=1_049,
            raw_total_text="10,49 zł",
            rounded_total_grosze=1_050,
            rounded_total_text="10,50 zł",
            paid_grosze=2_000,
            paid_text="20,00 zł",
            change_grosze=950,
            change_text="9,50 zł",
            items_count=1,
        ),
    ]


def test_history_sale_details_returns_view_state(
    controller: AppController,
    scale: MockScale,
) -> None:
    weighted_product_id = create_weighted_product(controller, name="Apples", price_grosze=699)
    piece_product_id = create_piece_product(controller, name="Roll", price_grosze=120)
    scale.set_weight_grams(1_500)
    controller.select_product_by_id(weighted_product_id)
    controller.select_product_by_id(piece_product_id)
    controller.add_selected_piece_product(quantity=3)
    controller.start_payment()
    controller.set_paid_grosze(2_000)
    saved_sale = controller.save_sale()

    details = controller.read_sale_details(saved_sale.sale_id)

    assert details == SaleDetailsViewState(
        sale_id=saved_sale.sale_id,
        created_at_text="2026-06-23 12:00",
        raw_total_grosze=1_409,
        raw_total_text="14,09 zł",
        rounded_total_grosze=1_400,
        rounded_total_text="14,00 zł",
        paid_grosze=2_000,
        paid_text="20,00 zł",
        change_grosze=600,
        change_text="6,00 zł",
        items=(
            SaleItemViewState(
                product_id=weighted_product_id,
                product_name="Apples",
                unit_price_text="6,99 zł/kg",
                quantity_text="1,50 kg",
                line_total_text="10,49 zł",
            ),
            SaleItemViewState(
                product_id=piece_product_id,
                product_name="Roll",
                unit_price_text="1,20 zł/szt.",
                quantity_text="3 szt.",
                line_total_text="3,60 zł",
            ),
        ),
    )


def test_history_sale_details_returns_none_for_missing_sale(
    controller: AppController,
) -> None:
    assert controller.read_sale_details(404) is None


def test_navigation_methods_update_view_state(controller: AppController) -> None:
    assert controller.open_settings().app_state is AppState.SETTINGS
    assert controller.open_history().app_state is AppState.HISTORY
    assert controller.cancel_current_operation().app_state is AppState.PRODUCT_SELECTION


def test_public_app_controller_annotations_use_no_domain_models() -> None:
    forbidden_names = {"Product", "Sale", "Cart", "CartItem", "UnitType"}

    for name, member in inspect.getmembers(AppController, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue

        annotations = member.__annotations__
        annotation_text = " ".join(str(annotation) for annotation in annotations.values())
        assert forbidden_names.isdisjoint(annotation_text.split())
