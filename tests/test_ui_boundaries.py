import ast
import sqlite3
from pathlib import Path

from cash_assistant.controller.view_state import ProductViewState
from cash_assistant.main import build_development_controller
from cash_assistant.ui.sales_screen import (
    _product_icon_path,
    _product_page_count,
    _products_for_page,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_PATH = PROJECT_ROOT / "src" / "cash_assistant" / "ui"


def test_ui_does_not_import_core_data_or_hardware() -> None:
    forbidden_prefixes = (
        "cash_assistant.core",
        "cash_assistant.data",
        "cash_assistant.hardware",
    )

    for path in UI_PATH.glob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules = _imported_modules(module)

        assert all(
            not imported_module.startswith(forbidden_prefix)
            for imported_module in imported_modules
            for forbidden_prefix in forbidden_prefixes
        ), path


def test_development_controller_synchronizes_active_products_from_csv(
    tmp_path: Path,
) -> None:
    controller = build_development_controller(tmp_path / "dev.sqlite3")

    products = controller.prepare_view_state().products

    assert [product.name for product in products] == [
        "Ziemniaki",
        "Ogórki",
        "Jabłka",
        "Kukurydza",
    ]
    assert [product.icon_filename for product in products] == [
        "ziemniaki.png",
        "ogórki.png",
        "jabłka.png",
        "kukurydza.png",
    ]


def test_development_controller_does_not_duplicate_synchronized_products(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "dev.sqlite3"
    build_development_controller(database_path)
    build_development_controller(database_path)

    with sqlite3.connect(database_path) as connection:
        products_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    assert products_count == 5


def test_settings_screen_and_navigation_are_removed() -> None:
    main_window_source = (UI_PATH / "main_window.py").read_text(encoding="utf-8")
    sales_source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert not (UI_PATH / "settings_screen.py").exists()
    assert "SettingsScreen" not in main_window_source
    assert "show_settings_screen" not in main_window_source
    assert "on_open_settings" not in sales_source
    assert "_open_settings_button" not in sales_source


def test_sales_screen_paid_input_accepts_comma_text() -> None:
    source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert "QLineEdit" in source
    assert "textEdited.connect(self._payment_value_changed)" in source
    assert "Command.DECIMAL_SEPARATOR_TYPED" in source


def test_product_icon_path_uses_configured_icon_or_fallback() -> None:
    assert _product_icon_path("jabłka.png").name == "jabłka.png"
    assert _product_icon_path("missing.png").name == "fallback.png"


def test_product_pages_contain_at_most_nine_products() -> None:
    products = tuple(_product_view_state(product_id) for product_id in range(1, 12))

    assert _product_page_count(len(products)) == 2
    assert [product.product_id for product in _products_for_page(products, 0)] == list(
        range(1, 10)
    )
    assert [product.product_id for product in _products_for_page(products, 1)] == [
        10,
        11,
    ]


def test_product_page_count_does_not_add_page_for_exact_multiple_of_nine() -> None:
    assert _product_page_count(0) == 1
    assert _product_page_count(9) == 1
    assert _product_page_count(18) == 2
    assert _product_page_count(19) == 3


def test_sales_screen_uses_page_arrows_without_scrollbar() -> None:
    source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert "PRODUCTS_PER_PAGE = 9" in source
    assert "_previous_products_page_button" in source
    assert "_next_products_page_button" in source
    assert "setVisible(has_multiple_pages)" in source
    assert "self._keyboard_controller.set_products(page_products)" in source
    assert "QScrollArea" not in source


def test_history_screen_uses_controller_dtos_for_sales_history() -> None:
    source = (UI_PATH / "history_screen.py").read_text(encoding="utf-8")

    assert "list_sales_for_history()" in source
    assert "read_sale_details(sale_id)" in source
    assert "SaleSummaryViewState" in source
    assert "SaleDetailsViewState" in source
    assert "Brak sprzedaży" not in source


def test_main_window_installs_global_event_filter_for_sales_screen() -> None:
    source = (UI_PATH / "main_window.py").read_text(encoding="utf-8")

    assert "installEventFilter(self)" in source
    assert "def eventFilter(" in source
    assert "HistoryScreen" not in source
    assert "show_history_screen" not in source
    assert "SettingsScreen" not in source
    assert "QStackedWidget" not in source
    assert "setCentralWidget(self._sales_screen)" in source
    assert "self.centralWidget() is self._sales_screen" in source
    assert "handle_global_key_event(event)" in source


def test_sales_screen_global_key_handling_uses_keyboard_controller() -> None:
    source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert "KeyboardController(controller)" in source
    assert "def handle_global_key_event(" in source
    assert "self._keyboard_controller.handle(command, payload)" in source
    assert "Numpad digits should work independently of widget focus" in source


def test_sales_screen_does_not_expose_history_navigation() -> None:
    source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert "SALES_OPEN_HISTORY_BUTTON_TEXT" not in source
    assert "_open_history_button" not in source
    assert "_open_history" not in source
    assert "on_open_history" not in source


def _imported_modules(module: ast.Module) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    return imports


def _product_view_state(product_id: int) -> ProductViewState:
    return ProductViewState(
        product_id=product_id,
        name=f"Produkt {product_id}",
        price_text="1,00 zł/kg",
        unit_text="kg",
        button_text=f"Produkt {product_id}\n1,00 zł/kg",
        icon_filename="fallback.png",
    )
