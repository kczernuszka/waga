"""Application entry point for the development GUI."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from cash_assistant.controller.app_controller import AppController
from cash_assistant.data.database import connect, initialize_schema
from cash_assistant.data.product_csv_sync import synchronize_products_from_csv
from cash_assistant.data.product_repository import ProductRepository
from cash_assistant.data.sale_repository import SaleRepository
from cash_assistant.hardware.mock_scale import MockScale
from cash_assistant.ui.main_window import MainWindow

DEV_DATABASE_PATH = Path("cash_assistant_dev.sqlite3")
PRODUCTS_CSV_PATH = Path(__file__).resolve().parents[2] / "config" / "products.csv"
DEV_SCALE_WEIGHT_GRAMS = 1_000


def main() -> None:
    """Start the development PySide6 application."""
    app = QApplication(sys.argv)
    controller = build_development_controller(DEV_DATABASE_PATH)
    window = MainWindow(controller)
    window.show()
    raise SystemExit(app.exec())


def build_development_controller(
    database_path: Path = DEV_DATABASE_PATH,
    products_csv_path: Path = PRODUCTS_CSV_PATH,
) -> AppController:
    connection = connect(database_path)
    initialize_schema(connection)
    synchronize_products_from_csv(connection, products_csv_path)

    scale = MockScale()
    scale.set_weight_grams(DEV_SCALE_WEIGHT_GRAMS)

    return AppController(
        scale=scale,
        product_repository=ProductRepository(connection),
        sale_repository=SaleRepository(connection),
    )


if __name__ == "__main__":
    main()
