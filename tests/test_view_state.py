from cash_assistant.controller.view_state import (
    CartItemViewState,
    ProductViewState,
    build_cart_item_view_state,
    build_product_view_state,
)
from cash_assistant.core.cart import CartItem
from cash_assistant.core.product import Product, UnitType


def test_build_product_view_state_for_weighted_product() -> None:
    assert build_product_view_state(
        Product(
            id=1,
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=699,
        )
    ) == ProductViewState(
        product_id=1,
        name="Jabłka",
        price_text="6,99 zł/kg",
        unit_text="kg",
        button_text="Jabłka\n6,99 zł/kg",
    )


def test_build_product_view_state_for_piece_product() -> None:
    assert build_product_view_state(
        Product(
            id=2,
            name="Bułka",
            unit_type=UnitType.PIECE,
            price_grosze=120,
        )
    ) == ProductViewState(
        product_id=2,
        name="Bułka",
        price_text="1,20 zł/szt.",
        unit_text="szt.",
        button_text="Bułka\n1,20 zł/szt.",
    )


def test_build_cart_item_view_state() -> None:
    assert build_cart_item_view_state(
        CartItem(
            product_id=1,
            product_name_snapshot="Jabłka",
            unit_type_snapshot=UnitType.KG,
            unit_price_grosze_snapshot=699,
            quantity_value=1_500,
            line_total_grosze=1_049,
        )
    ) == CartItemViewState(
        product_id=1,
        product_name="Jabłka",
        unit_price_text="6,99 zł/kg",
        quantity_text="1,50 kg",
        line_total_text="10,49 zł",
    )
