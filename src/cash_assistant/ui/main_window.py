"""Main application window."""

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from cash_assistant.controller.app_controller import AppController
from cash_assistant.controller.labels import APP_TITLE
from cash_assistant.ui.sales_screen import SalesScreen


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._sales_screen = SalesScreen(controller)

        self.setWindowTitle(APP_TITLE)
        self.setCentralWidget(self._sales_screen)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    @property
    def sales_screen(self) -> SalesScreen:
        return self._sales_screen

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self.centralWidget() is self._sales_screen
            and event.type() is QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
        ):
            return self._sales_screen.handle_global_key_event(event)
        return super().eventFilter(watched, event)
