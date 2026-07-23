from datetime import UTC, datetime

from cash_assistant.controller.view_state import (
    CartItemViewState,
    ProductViewState,
    SaleItemViewState,
    SaleSummaryViewState,
    build_cart_item_view_state,
    build_product_view_state,
    build_sale_item_view_state,
    build_sale_summary_view_state,
)
from cash_assistant.core.cart import CartItem
from cash_assistant.core.product import Product, UnitType
from cash_assistant.core.sale import Sale, SaleItem


def test_build_product_view_state_for_weighted_product() -> None:
    assert build_product_view_state(
        Product(
            id=1,
            code="jablka",
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=699,
            icon_filename="jabłka.png",
        )
    ) == ProductViewState(
        product_id=1,
        name="Jabłka",
        price_text="6,99 zł/kg",
        unit_text="kg",
        button_text="Jabłka\n6,99 zł/kg",
        icon_filename="jabłka.png",
    )


def test_build_product_view_state_for_piece_product() -> None:
    assert build_product_view_state(
        Product(
            id=2,
            code="bulka",
            name="Bułka",
            unit_type=UnitType.PIECE,
            price_grosze=120,
            icon_filename="fallback.png",
        )
    ) == ProductViewState(
        product_id=2,
        name="Bułka",
        price_text="1,20 zł/szt.",
        unit_text="szt.",
        button_text="Bułka\n1,20 zł/szt.",
        icon_filename="fallback.png",
    )


def test_build_cart_item_view_state() -> None:
    assert build_cart_item_view_state(
        CartItem(
            product_id=1,
            product_code_snapshot="jablka",
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


def test_build_sale_item_view_state_uses_code_snapshot_after_product_deletion() -> None:
    assert build_sale_item_view_state(
        SaleItem(
            product_id=None,
            product_code_snapshot="jablka",
            product_name_snapshot="Jabłka",
            unit_snapshot=UnitType.KG,
            unit_price_grosze_snapshot=699,
            quantity_value=1_500,
            line_total_grosze=1_049,
        )
    ) == SaleItemViewState(
        product_id=None,
        product_code="jablka",
        product_name="Jabłka",
        unit_price_text="6,99 zł/kg",
        quantity_text="1,50 kg",
        line_total_text="10,49 zł",
    )


def test_sale_summary_formats_created_at_in_poland_time_zone() -> None:
    assert build_sale_summary_view_state(
        Sale(
            id=1,
            created_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            raw_total_grosze=1_000,
            rounded_total_grosze=1_000,
            paid_grosze=2_000,
            change_grosze=1_000,
            items=(),
        )
    ) == SaleSummaryViewState(
        sale_id=1,
        created_at_text="2026-06-23 12:00",
        raw_total_grosze=1_000,
        raw_total_text="10,00 zł",
        rounded_total_grosze=1_000,
        rounded_total_text="10,00 zł",
        paid_grosze=2_000,
        paid_text="20,00 zł",
        change_grosze=1_000,
        change_text="10,00 zł",
        items_count=0,
    )
