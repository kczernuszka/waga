import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cash_assistant.controller.app_controller import AppController, AppState
from cash_assistant.controller.keyboard_controller import Command, KeyboardController
from cash_assistant.core.cart import CartItem
from cash_assistant.core.product import Product, UnitType
from cash_assistant.data.database import connect, initialize_schema
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
        sale_repository=SaleRepository(connection),
        clock=lambda: CREATED_AT,
    )


@pytest.fixture
def keyboard_controller(app_controller: AppController) -> KeyboardController:
    return KeyboardController(
        app_controller=app_controller,
        products=(weighted_product(), piece_product()),
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


def test_digit_in_product_selection_selects_weighted_product(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)

    result = keyboard_controller.handle(Command.DIGIT_TYPED, "1")

    assert result == CartItem(
        product_id=1,
        product_name_snapshot="Jabłka",
        unit_type_snapshot=UnitType.KG,
        unit_price_grosze_snapshot=699,
        quantity_value=1_500,
        line_total_grosze=1_049,
    )
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

    assert result == CartItem(
        product_id=2,
        product_name_snapshot="Bułka",
        unit_type_snapshot=UnitType.PIECE,
        unit_price_grosze_snapshot=120,
        quantity_value=1,
        line_total_grosze=120,
    )
    assert app_controller.prepare_view_state().app_state is AppState.CART_REVIEW


def test_select_product_command_accepts_product_payload(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(2_000)

    keyboard_controller.handle(Command.SELECT_PRODUCT, weighted_product())

    assert app_controller.cart.technical_total_grosze == 1_398


def test_start_payment_and_digits_calculate_change(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")

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
    connection: sqlite3.Connection,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.START_PAYMENT)
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")
    keyboard_controller.handle(Command.DIGIT_TYPED, "0")

    saved_sale = keyboard_controller.handle(Command.SAVE_SALE)

    assert SaleRepository(connection).read_sale(1) == saved_sale
    assert app_controller.cart.is_empty
    assert app_controller.prepare_view_state().app_state is AppState.PRODUCT_SELECTION


def test_remove_last_and_clear_cart_commands(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
    keyboard_controller.handle(Command.DIGIT_TYPED, "2")
    keyboard_controller.handle(Command.DIGIT_TYPED, "3")
    keyboard_controller.handle(Command.CONFIRM)

    removed = keyboard_controller.handle(Command.REMOVE_LAST_ITEM)

    assert isinstance(removed, CartItem)
    assert app_controller.cart.technical_total_grosze == 1_049

    keyboard_controller.handle(Command.CLEAR_CART)

    assert app_controller.cart.is_empty


def test_cancel_exits_current_input_without_clearing_cart(
    app_controller: AppController,
    keyboard_controller: KeyboardController,
    scale: MockScale,
) -> None:
    scale.set_weight_grams(1_500)
    keyboard_controller.handle(Command.DIGIT_TYPED, "1")
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
