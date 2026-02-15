from __future__ import annotations

from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget,
    QMessageBox,
)

from app.db.auth_service import sign_out
from app.modules.company_clients.page import CompanyClientsPage
from app.modules.workers.page import WorkersPage
from app.modules.incidents.page import IncidentsPage
from app.modules.templates.page import TemplatesPage
from app.modules.generate_documents.page import GenerateDocumentsPage
from app.modules.reports.page import ReportsPage


class Sidebar(QWidget):
    navigate = Signal(str)
    request_logout = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        title = QLabel("HR Docs")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        self.menu_items = [
            ("add_client", "Add Client"),
            ("add_template", "Add Template"),
            ("add_worker", "Add Worker"),
            ("incidents", "Incidents"),
            ("generate_documents", "Generate Documents"),
            ("reports", "Reports"),
        ]

        self.buttons: dict[str, QPushButton] = {}

        for key, label in self.menu_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(42)
            btn.clicked.connect(partial(self._on_menu_clicked, key))
            self.buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

        self.logout_btn = QPushButton("Log out")
        self.logout_btn.setMinimumHeight(42)
        self.logout_btn.clicked.connect(self._confirm_logout)
        layout.addWidget(self.logout_btn)

        self.set_active("add_client")

    def _on_menu_clicked(self, key: str) -> None:
        self.set_active(key)
        self.navigate.emit(key)

    def set_active(self, active_key: str) -> None:
        for key, btn in self.buttons.items():
            btn.setChecked(key == active_key)

    def _confirm_logout(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Confirm")
        box.setText("Do you want to log out?")
        box.setIcon(QMessageBox.Icon.Question)
        yes_btn = box.addButton("Yes", QMessageBox.ButtonRole.YesRole)
        box.addButton("No", QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(yes_btn)

        box.exec()
        if box.clickedButton() == yes_btn:
            self.request_logout.emit()


class PlaceholderPage(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QLabel(title)
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(header)

        hint = QLabel("Skeleton page (UI only).")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        layout.addStretch(1)


class MainWindow(QMainWindow):
    logged_out = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HR Docs Desktop")

        root = QWidget(self)
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.pages: dict[str, int] = {}
        self._build_pages()

        self.sidebar.navigate.connect(self.go_to)
        self.sidebar.request_logout.connect(self.on_logout)

        self.go_to("add_client")

    def _build_pages(self) -> None:
        self._add_page("add_client", CompanyClientsPage())
        self._add_page("add_template", TemplatesPage())
        self._add_page("add_worker", WorkersPage())
        self._add_page("incidents", IncidentsPage())
        self._add_page("generate_documents", GenerateDocumentsPage())
        self._add_page("reports", ReportsPage())

    def _add_page(self, key: str, page: QWidget) -> None:
        self.pages[key] = self.stack.addWidget(page)

    def go_to(self, key: str) -> None:
        if key not in self.pages:
            return
        self.stack.setCurrentIndex(self.pages[key])
        self.sidebar.set_active(key)

    def on_logout(self) -> None:
        sign_out()
        self.logged_out.emit()
        self.close()