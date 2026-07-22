"""Main application window."""

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from cash_assistant.controller.app_controller import AppController
from cash_assistant.controller.labels import APP_TITLE
from cash_assistant.ui.sales_screen import SalesScreen
from cash_assistant.ui.settings_screen import SettingsScreen


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._sales_screen = SalesScreen(
            controller,
            on_open_settings=self.show_settings_screen,
        )
        self._settings_screen = SettingsScreen(
            controller,
            on_back_to_sales=self.show_sales_screen,
            on_products_changed=self._refresh_sales_screen,
        )
        self._screen_stack = QStackedWidget()
        self._screen_stack.addWidget(self._sales_screen)
        self._screen_stack.addWidget(self._settings_screen)

        self.setWindowTitle(APP_TITLE)
        self.setCentralWidget(self._screen_stack)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    @property
    def sales_screen(self) -> SalesScreen:
        return self._sales_screen

    def show_sales_screen(self) -> None:
        self._sales_screen.refresh()
        self._screen_stack.setCurrentWidget(self._sales_screen)

    def show_settings_screen(self) -> None:
        self._settings_screen.refresh()
        self._screen_stack.setCurrentWidget(self._settings_screen)

    def _refresh_sales_screen(self) -> None:
        self._sales_screen.refresh()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self._screen_stack.currentWidget() is self._sales_screen
            and event.type() is QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
        ):
            return self._sales_screen.handle_global_key_event(event)
        return super().eventFilter(watched, event)
