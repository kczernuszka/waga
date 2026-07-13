"""Application entry point for the development GUI."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from cash_assistant.controller.app_controller import AppController
from cash_assistant.controller.view_state import ProductEditInput
from cash_assistant.data.database import connect, initialize_schema
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.mock_scale import MockScale
from cash_assistant.ui.main_window import MainWindow

DEV_DATABASE_PATH = Path("cash_assistant_dev.sqlite3")
DEV_SCALE_WEIGHT_GRAMS = 1_000


def main() -> None:
    """Start the development PySide6 application."""
    app = QApplication(sys.argv)
    controller = build_development_controller(DEV_DATABASE_PATH)
    window = MainWindow(controller)
    window.show()
    raise SystemExit(app.exec())


def build_development_controller(database_path: Path = DEV_DATABASE_PATH) -> AppController:
    connection = connect(database_path)
    initialize_schema(connection)

    scale = MockScale()
    scale.set_weight_grams(DEV_SCALE_WEIGHT_GRAMS)

    controller = AppController(
        scale=scale,
        product_repository=ProductRepository(connection),
        sale_repository=SaleRepository(connection),
    )
    seed_development_products(controller)
    return controller


def seed_development_products(controller: AppController) -> None:
    existing_product_names = {product.name for product in controller.list_products_for_settings()}

    for product in _development_product_inputs():
        if product.name not in existing_product_names:
            controller.save_product_from_input(product)


def _development_product_inputs() -> tuple[ProductEditInput, ...]:
    return (
        ProductEditInput(
            product_id=None,
            name="Ziemniaki",
            unit_code="kg",
            price_grosze=299,
            sort_order=10,
        ),
        ProductEditInput(
            product_id=None,
            name="Ogórki",
            unit_code="kg",
            price_grosze=799,
            sort_order=20,
        ),
        ProductEditInput(
            product_id=None,
            name="Jabłka",
            unit_code="kg",
            price_grosze=499,
            sort_order=30,
        ),
        ProductEditInput(
            product_id=None,
            name="Bułka",
            unit_code="piece",
            price_grosze=120,
            sort_order=40,
        ),
    )


if __name__ == "__main__":
    main()
