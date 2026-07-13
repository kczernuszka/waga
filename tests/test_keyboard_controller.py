import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cash_assistant.controller.app_controller import AppController, AppState
from cash_assistant.controller.keyboard_controller import Command, KeyboardController
from cash_assistant.controller.view_state import ProductEditInput, SaleDetailsViewState, ViewState
from cash_assistant.data.database import connect, initialize_schema
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.mock_scale import MockScale

CREATED_AT = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "test.sqlite3")
    initialize_schema(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def scale() -> MockScale:
    return MockScale()


@pytest.fixture
def app_controller(
    connection: sqlite3.Connection,
    scale: MockScale,
) -> AppController:
    return AppController(
        scale=scale,
        product_repository=ProductRepository(connection),
        sale_repository=SaleRepository(connection),
        clock=lambda: CREATED_AT,
    )


@pytest.fixture
def keyboard_controller(app_controller: AppController) -> KeyboardController:
    create_weighted_product(app_controller, name="Apples", price_grosze=699)
    create_piece_product(app_controller, name="Roll", price_grosze=120)
    return KeyboardController(app_controller=app_controller)


def create_weighted_product(
    app_controller: AppController,
    *,
    name: str = "Apples",
    price_grosze: int = 699,
    sort_order: int = 0,
) -> int:
    view_state = app_controller.save_product_from_input(
        ProductEditInput(
            product_id=None,
            name=name,
            unit_code="kg",
            price_grosze=price_grosze,
            sort_order=sort_order,
        )
    )
    product_id = view_state.product_id
    assert product_id is not None
    return product_id


def create_piece_product(
    app_controller: AppController,
    *,
    name: str = "Roll",
    price_grosze: int = 120,
    sort_order: int = 0,
) -> int:
    view_state = app_controller.save_product_from_input(
        ProductEditInput(
            product_id=None,
            name=name,
            unit_code="piece",
            price_grosze=price_grosze,
            sort_order=sort_order,
        )
    )
    product_id = view_state.product_id
    assert product_id is not None
    return product_id


def test_digit_in_product_selection_selects_weighted_product(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)

    selected_result = keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    result = keyboard_controller.handle(Command.CONFIRM)

    assert isinstance(selected_result, ViewState)
    assert selected_result.app_state is AppState.READING_WEIGHT
    assert isinstance(result, ViewState)
    assert result.cart_items[0].product_name == "Apples"
    assert result.cart_items[0].quantity_text == "1,50 kg"
    assert result.cart_items[0].line_total_text == "10,49 zł"
    assert app_controller.prepare_view_state().app_state is AppState.CART_REVIEW


def test_select_piece_product_enters_quantity_then_confirm_adds_item(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
) -> None:
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")

    assert app_controller.prepare_view_state().app_state is AppState.ENTERING_QUANTITY

    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")
    keyboard_controller.handle(Command.BACKSPACE)
    result = keyboard_controller.handle(Command.CONFIRM)

    assert isinstance(result, ViewState)
    assert result.cart_items[0].product_name == "Roll"
    assert result.cart_items[0].quantity_text == "1 szt."
    assert result.cart_items[0].line_total_text == "1,20 zł"
    assert app_controller.prepare_view_state().app_state is AppState.CART_REVIEW


def test_select_product_command_accepts_product_id_payload(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(2_000)

    keyboard_controller.handle(Command.SELECT_PRODUCT, 1)
    keyboard_controller.handle(Command.CONFIRM)

    assert app_controller.prepare_view_state().technical_total_grosze == 1_398


def test_select_product_command_rejects_non_id_payload(
    keyboard_controller: KeyboardController,
) -> None:
    with pytest.raises(ValueError):
        keyboard_controller.handle(Command.SELECT_PRODUCT, "1")


def test_keyboard_shortcut_maps_to_correct_product_id_from_view_state(
    app_controller: AppController,
    scale: MockScale,
) -> None:
    create_weighted_product(
        app_controller,
        name="Apple",
        price_grosze=699,
        sort_order=20,
    )
    first_slot_product_id = create_weighted_product(
        app_controller,
        name="Pears",
        price_grosze=899,
        sort_order=10,
    )
    keyboard_controller = KeyboardController(app_controller=app_controller)
    scale.set_weight_grams(1_000)

    selected_result = keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    result = keyboard_controller.handle(Command.CONFIRM)

    assert isinstance(selected_result, ViewState)
    assert selected_result.selected_product is not None
    assert selected_result.selected_product.product_id == first_slot_product_id
    assert isinstance(result, ViewState)
    assert result.cart_items[0].product_id == first_slot_product_id
    assert result.cart_items[0].product_name == "Pears"


def test_shortcut_number_is_not_treated_as_product_id(
    app_controller: AppController,
    scale: MockScale,
) -> None:
    product_with_id_1 = create_weighted_product(
        app_controller,
        name="Apple",
        price_grosze=699,
        sort_order=20,
    )
    first_slot_product_id = create_weighted_product(
        app_controller,
        name="Pears",
        price_grosze=899,
        sort_order=10,
    )
    keyboard_controller = KeyboardController(app_controller=app_controller)
    scale.set_weight_grams(1_000)

    selected_result = keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    result = keyboard_controller.handle(Command.CONFIRM)

    assert isinstance(selected_result, ViewState)
    assert isinstance(result, ViewState)
    assert product_with_id_1 == 1
    assert first_slot_product_id == 2
    assert result.cart_items[0].product_id == first_slot_product_id


def test_start_payment_and_digits_calculate_change(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.CONFIRM)

    keyboard_controller.handle(Command.START_PAYMENT)
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")
    keyboard_controller.handle(Command.DIGIT_TYPED, "0")

    view_state = app_controller.prepare_view_state()
    assert view_state.app_state is AppState.PAYMENT
    assert view_state.paid_grosze == 2_000
    assert view_state.change_grosze == 950
    assert view_state.missing_grosze is None


def test_payment_buffer_accepts_decimal_separator(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.CONFIRM)

    keyboard_controller.handle(Command.START_PAYMENT)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.DECIMAL_SEPARATOR_TYPED)
    keyboard_controller.handle(Command.DIGIT_TYPED, "0")
    keyboard_controller.handle(Command.DIGIT_TYPED, "0")

    view_state = app_controller.prepare_view_state()
    assert view_state.paid_grosze == 100
    assert view_state.change_grosze is None
    assert view_state.missing_grosze == 950


def test_save_sale_command_uses_app_controller_and_repository(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.CONFIRM)
    keyboard_controller.handle(Command.START_PAYMENT)
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")
    keyboard_controller.handle(Command.DIGIT_TYPED, "0")

    saved_sale = keyboard_controller.handle(Command.SAVE_SALE)

    assert isinstance(saved_sale, SaleDetailsViewState)
    assert app_controller.read_sale_details(saved_sale.sale_id) == saved_sale
    assert app_controller.prepare_view_state().is_cart_empty
    assert app_controller.prepare_view_state().app_state is AppState.PRODUCT_SELECTION


def test_remove_last_and_clear_cart_commands(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.CONFIRM)
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")
    keyboard_controller.handle(Command.DIGIT_TYPED, "3")
    keyboard_controller.handle(Command.CONFIRM)

    removed_view_state = keyboard_controller.handle(Command.REMOVE_LAST_ITEM)

    assert isinstance(removed_view_state, ViewState)
    assert removed_view_state.technical_total_grosze == 1_049

    cleared_view_state = keyboard_controller.handle(Command.CLEAR_CART)

    assert cleared_view_state is None
    assert app_controller.prepare_view_state().is_cart_empty


def test_cancel_exits_current_input_without_clearing_cart(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.CONFIRM)
    keyboard_controller.handle(Command.START_PAYMENT)
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")

    keyboard_controller.handle(Command.CANCEL)

    view_state = app_controller.prepare_view_state()
    assert view_state.app_state is AppState.CART_REVIEW
    assert view_state.paid_grosze is None
    assert not view_state.is_cart_empty


def test_open_settings_and_history_commands(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
) -> None:
    keyboard_controller.handle(Command.OPEN_SETTINGS)
    assert app_controller.prepare_view_state().app_state is AppState.SETTINGS

    keyboard_controller.handle(Command.OPEN_HISTORY)
    assert app_controller.prepare_view_state().app_state is AppState.HISTORY


def test_invalid_product_shortcut_raises_value_error(
    keyboard_controller: KeyboardController,
) -> None:
    with pytest.raises(ValueError):
        keyboard_controller.handle(Command.DIGIT_TYPED, "9")
