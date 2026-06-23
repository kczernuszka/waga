import pytest

from cash_assistant.core.cart import Cart, CartItem
from cash_assistant.core.product import Product, UnitType


def weighted_product() -> Product:
    return Product(
        id=1,
        name="Jabłka",
        unit_type=UnitType.KG,
        price_grosze=699,
        active=True,
        sort_order=10,
    )


def piece_product() -> Product:
    return Product(
        id=2,
        name="Bułka",
        unit_type=UnitType.PIECE,
        price_grosze=120,
        active=True,
        sort_order=20,
    )


def test_add_weighted_product_creates_cart_item_with_product_snapshot() -> None:
    cart = Cart()

    item = cart.add_weighted_product(weighted_product(), weight_grams=1_500)

    assert item == CartItem(
        product_id=1,
        product_name_snapshot="Jabłka",
        unit_type_snapshot=UnitType.KG,
        unit_price_grosze_snapshot=699,
        quantity_value=1_500,
        line_total_grosze=1_049,
    )
    assert cart.items == (item,)


def test_add_piece_product_creates_cart_item_with_product_snapshot() -> None:
    cart = Cart()

    item = cart.add_piece_product(piece_product(), quantity=3)

    assert item == CartItem(
        product_id=2,
        product_name_snapshot="Bułka",
        unit_type_snapshot=UnitType.PIECE,
        unit_price_grosze_snapshot=120,
        quantity_value=3,
        line_total_grosze=360,
    )
    assert cart.items == (item,)


def test_cart_technical_total_is_sum_of_line_totals_before_rounding() -> None:
    cart = Cart()
    cart.add_weighted_product(weighted_product(), weight_grams=1_500)
    cart.add_piece_product(piece_product(), quantity=3)

    assert cart.technical_total_grosze == 1_409


def test_cart_rounded_total_is_rounded_to_nearest_50_grosze() -> None:
    cart = Cart()
    cart.add_weighted_product(weighted_product(), weight_grams=1_500)
    cart.add_piece_product(piece_product(), quantity=3)

    assert cart.rounded_total_grosze == 1_400


def test_remove_last_item_removes_and_returns_most_recent_item() -> None:
    cart = Cart()
    first_item = cart.add_weighted_product(weighted_product(), weight_grams=1_500)
    second_item = cart.add_piece_product(piece_product(), quantity=3)

    removed_item = cart.remove_last_item()

    assert removed_item == second_item
    assert cart.items == (first_item,)
    assert cart.technical_total_grosze == 1_049


def test_remove_last_item_from_empty_cart_returns_none() -> None:
    cart = Cart()

    assert cart.remove_last_item() is None


def test_clear_removes_all_items() -> None:
    cart = Cart()
    cart.add_weighted_product(weighted_product(), weight_grams=1_500)
    cart.add_piece_product(piece_product(), quantity=3)

    cart.clear()

    assert cart.items == ()
    assert cart.is_empty
    assert cart.technical_total_grosze == 0
    assert cart.rounded_total_grosze == 0


def test_empty_cart_has_no_items_and_zero_totals() -> None:
    cart = Cart()

    assert cart.items == ()
    assert cart.is_empty
    assert cart.technical_total_grosze == 0
    assert cart.rounded_total_grosze == 0


@pytest.mark.parametrize("weight_grams", [-1, -500])
def test_add_weighted_product_rejects_negative_weight(weight_grams: int) -> None:
    cart = Cart()

    with pytest.raises(ValueError):
        cart.add_weighted_product(weighted_product(), weight_grams=weight_grams)


@pytest.mark.parametrize("quantity", [-1, -3])
def test_add_piece_product_rejects_negative_quantity(quantity: int) -> None:
    cart = Cart()

    with pytest.raises(ValueError):
        cart.add_piece_product(piece_product(), quantity=quantity)


def test_add_piece_product_rejects_kg_product() -> None:
    cart = Cart()

    with pytest.raises(ValueError):
        cart.add_piece_product(weighted_product(), quantity=3)


def test_add_weighted_product_rejects_piece_product() -> None:
    cart = Cart()

    with pytest.raises(ValueError):
        cart.add_weighted_product(piece_product(), weight_grams=1_500)
