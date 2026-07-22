import ast
from pathlib import Path

from cash_assistant.main import build_development_controller
from cash_assistant.ui.settings_screen import _parse_price_grosze

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


def test_development_controller_seeds_products_when_database_is_empty(tmp_path: Path) -> None:
    controller = build_development_controller(tmp_path / "dev.sqlite3")

    products = controller.list_products_for_settings()

    assert [product.name for product in products] == ["Ziemniaki", "Ogórki", "Jabłka", "Bułka"]


def test_development_controller_does_not_duplicate_seed_products(tmp_path: Path) -> None:
    database_path = tmp_path / "dev.sqlite3"
    first_controller = build_development_controller(database_path)
    second_controller = build_development_controller(database_path)

    assert len(first_controller.list_products_for_settings()) == 4
    assert len(second_controller.list_products_for_settings()) == 4


def test_sales_screen_paid_input_accepts_comma_text() -> None:
    source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert "QLineEdit" in source
    assert "textEdited.connect(self._payment_value_changed)" in source
    assert "Command.DECIMAL_SEPARATOR_TYPED" in source


def test_settings_screen_uses_controller_dtos_for_product_editing() -> None:
    source = (UI_PATH / "settings_screen.py").read_text(encoding="utf-8")

    assert "list_products_for_settings()" in source
    assert "prepare_product_edit_view_state(product_id)" in source
    assert "save_product_from_input(product_input)" in source
    assert "ProductEditInput(" in source
    assert "QStackedWidget" in source
    assert "self._page_stack.addWidget(self._products_page)" in source
    assert "self._page_stack.addWidget(self._form_page)" in source
    assert "self._show_form_page()" in source
    assert "self._show_products_page()" in source


def test_settings_screen_price_parser_accepts_comma_text() -> None:
    assert _parse_price_grosze("0") == 0
    assert _parse_price_grosze("1") == 100
    assert _parse_price_grosze("1,20") == 120
    assert _parse_price_grosze("0,05") == 5
    assert _parse_price_grosze("1,2") == 120


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
    assert "QStackedWidget" in source
    assert "HistoryScreen" not in source
    assert "show_history_screen" not in source
    assert "setCentralWidget(self._screen_stack)" in source
    assert "setCentralWidget(self._sales_screen)" not in source
    assert "setCentralWidget(self._settings_screen)" not in source
    assert "self._screen_stack.currentWidget() is self._sales_screen" in source
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
