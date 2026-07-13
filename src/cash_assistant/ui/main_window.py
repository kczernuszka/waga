"""Main application window."""

from PySide6.QtWidgets import QMainWindow

from cash_assistant.controller.app_controller import AppController
from cash_assistant.controller.labels import APP_TITLE
from cash_assistant.ui.sales_screen import SalesScreen


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._sales_screen = SalesScreen(controller)

        self.setWindowTitle(APP_TITLE)
        self.setCentralWidget(self._sales_screen)

    @property
    def sales_screen(self) -> SalesScreen:
        return self._sales_screen
