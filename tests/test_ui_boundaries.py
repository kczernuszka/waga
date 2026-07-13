import ast
from pathlib import Path

from cash_assistant.main import build_development_controller
from cash_assistant.ui.sales_screen import _whole_zloty_to_grosze

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


def test_sales_screen_paid_input_uses_whole_zloty_values() -> None:
    assert _whole_zloty_to_grosze(0) == 0
    assert _whole_zloty_to_grosze(1) == 100
    assert _whole_zloty_to_grosze(20) == 2_000


def test_main_window_installs_global_event_filter_for_sales_screen() -> None:
    source = (UI_PATH / "main_window.py").read_text(encoding="utf-8")

    assert "installEventFilter(self)" in source
    assert "def eventFilter(" in source
    assert "self.centralWidget() is self._sales_screen" in source
    assert "handle_global_key_event(event)" in source


def test_sales_screen_global_key_handling_uses_keyboard_controller() -> None:
    source = (UI_PATH / "sales_screen.py").read_text(encoding="utf-8")

    assert "KeyboardController(controller)" in source
    assert "def handle_global_key_event(" in source
    assert "self._keyboard_controller.handle(command, payload)" in source
    assert "Numpad digits should work independently of widget focus" in source


def _imported_modules(module: ast.Module) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    return imports
