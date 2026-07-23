from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import cash_assistant.core.sale as sale_module
from cash_assistant.core.cart import Cart, CartItem
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import Sale

POLAND_TIME_ZONE = ZoneInfo("Europe/Warsaw")
CREATED_AT = datetime(2026, 6, 23, 12, 0, tzinfo=POLAND_TIME_ZONE)


def weighted_product() -> Product:
    return Product(
        id=1,
        code="jablka",
        name="Jabłka",
        unit_type=UnitType.KG,
        price_grosze=699,
        active=True,
        sort_order=10,
    )


def piece_product() -> Product:
    return Product(
        id=2,
        code="bulka",
        name="Bułka",
        unit_type=UnitType.PIECE,
        price_grosze=120,
        active=True,
        sort_order=20,
    )


def cart_with_weighted_product() -> Cart:
    cart = Cart()
    cart.add_weighted_product(weighted_product(), weight_grams=1_500)
    return cart


def cart_with_mixed_products() -> Cart:
    cart = cart_with_weighted_product()
    cart.add_piece_product(piece_product(), quantity=3)
    return cart


def test_create_sale_from_weighted_cart() -> None:
    sale = Sale.from_cart(
        cart_with_weighted_product(),
        paid_grosze=2_000,
        created_at=CREATED_AT,
    )

    assert sale.id is None
    assert sale.created_at == CREATED_AT
    assert sale.raw_total_grosze == 1_049
    assert sale.rounded_total_grosze == 1_050
    assert sale.paid_grosze == 2_000
    assert sale.change_grosze == 950
    assert sale.items == (
        sale_module.SaleItem(
            product_id=1,
            product_code_snapshot="jablka",
            product_name_snapshot="Jabłka",
            unit_snapshot=UnitType.KG,
            unit_price_grosze_snapshot=699,
            quantity_value=1_500,
            line_total_grosze=1_049,
        ),
    )


def test_create_sale_from_mixed_cart_with_kg_and_piece_products() -> None:
    sale = Sale.from_cart(
        cart_with_mixed_products(),
        paid_grosze=2_000,
        created_at=CREATED_AT,
    )

    assert sale.items == (
        sale_module.SaleItem(
            product_id=1,
            product_code_snapshot="jablka",
            product_name_snapshot="Jabłka",
            unit_snapshot=UnitType.KG,
            unit_price_grosze_snapshot=699,
            quantity_value=1_500,
            line_total_grosze=1_049,
        ),
        sale_module.SaleItem(
            product_id=2,
            product_code_snapshot="bulka",
            product_name_snapshot="Bułka",
            unit_snapshot=UnitType.PIECE,
            unit_price_grosze_snapshot=120,
            quantity_value=3,
            line_total_grosze=360,
        ),
    )


def test_raw_total_grosze_matches_cart_technical_total() -> None:
    cart = cart_with_mixed_products()

    sale = Sale.from_cart(cart, paid_grosze=2_000, created_at=CREATED_AT)

    assert sale.raw_total_grosze == cart.technical_total_grosze
    assert sale.raw_total_grosze == 1_409


def test_rounded_total_grosze_matches_cart_rounded_total() -> None:
    cart = cart_with_mixed_products()

    sale = Sale.from_cart(cart, paid_grosze=2_000, created_at=CREATED_AT)

    assert sale.rounded_total_grosze == cart.rounded_total_grosze
    assert sale.rounded_total_grosze == 1_400


def test_change_grosze_is_paid_grosze_minus_rounded_total_grosze() -> None:
    sale = Sale.from_cart(
        cart_with_mixed_products(),
        paid_grosze=2_000,
        created_at=CREATED_AT,
    )

    assert sale.change_grosze == 600


def test_sale_keeps_snapshot_of_cart_items() -> None:
    product = weighted_product()
    cart = Cart()
    cart_item = cart.add_weighted_product(product, weight_grams=1_500)

    sale = Sale.from_cart(cart, paid_grosze=2_000, created_at=CREATED_AT)
    cart.clear()
    object.__setattr__(product, "name", "Zmienione jabłka")
    object.__setattr__(product, "price_grosze", 999)

    assert sale.items == (
        sale_module.SaleItem(
            product_id=1,
            product_code_snapshot="jablka",
            product_name_snapshot="Jabłka",
            unit_snapshot=UnitType.KG,
            unit_price_grosze_snapshot=699,
            quantity_value=1_500,
            line_total_grosze=1_049,
        ),
    )
    assert id(sale.items[0]) != id(cart_item)
    assert isinstance(sale.items[0], sale_module.SaleItem)
    assert not isinstance(sale.items[0], CartItem)


def test_create_sale_rejects_empty_cart() -> None:
    with pytest.raises(ValueError):
        Sale.from_cart(Cart(), paid_grosze=2_000, created_at=CREATED_AT)


def test_create_sale_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError):
        Sale.from_cart(
            cart_with_weighted_product(),
            paid_grosze=2_000,
            created_at=datetime(2026, 6, 23, 12, 0),
        )


def test_create_sale_rejects_payment_lower_than_rounded_total() -> None:
    with pytest.raises(ValueError):
        Sale.from_cart(
            cart_with_mixed_products(),
            paid_grosze=1_399,
            created_at=CREATED_AT,
        )


def test_create_sale_rejects_negative_payment() -> None:
    with pytest.raises(ValueError):
        Sale.from_cart(
            cart_with_weighted_product(),
            paid_grosze=-1,
            created_at=CREATED_AT,
        )
