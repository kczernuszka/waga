import pytest

from cash_assistant.core.product import Product, UnitType


def test_product_stores_all_required_fields() -> None:
    product = Product(
        id=1,
        name="Jabłka",
        unit_type=UnitType.KG,
        price_grosze=699,
        active=True,
        sort_order=10,
    )

    assert product.id == 1
    assert product.name == "Jabłka"
    assert product.unit_type is UnitType.KG
    assert product.price_grosze == 699
    assert product.active is True
    assert product.sort_order == 10


def test_product_defaults_to_active_with_zero_sort_order() -> None:
    product = Product(
        id=None,
        name="Bułka",
        unit_type=UnitType.PIECE,
        price_grosze=120,
    )

    assert product.active is True
    assert product.sort_order == 0


def test_unit_type_values_are_kg_and_piece() -> None:
    assert UnitType.KG.value == "kg"
    assert UnitType.PIECE.value == "piece"


def test_product_rejects_negative_price() -> None:
    with pytest.raises(ValueError):
        Product(
            id=1,
            name="Jabłka",
            unit_type=UnitType.KG,
            price_grosze=-1,
        )
