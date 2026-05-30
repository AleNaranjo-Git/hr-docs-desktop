from __future__ import annotations

from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
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
from app.core.events import events


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
        self._logout_handled = False

        root = QWidget(self)
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        # Keep actual instances (not only indexes) so we can refresh them from events
        self.company_clients_page: CompanyClientsPage | None = None
        self.workers_page: WorkersPage | None = None
        self.templates_page: TemplatesPage | None = None
        self.incidents_page: IncidentsPage | None = None
        self.generate_documents_page: GenerateDocumentsPage | None = None
        self.reports_page: ReportsPage | None = None

        self.pages: dict[str, int] = {}
        self._pages_cache: dict[str, QWidget] = {}

        # Navigation
        self.sidebar.navigate.connect(self.go_to)
        self.sidebar.request_logout.connect(self.on_logout)

        # Global refresh wiring (scalable)
        ev = events()
        ev.company_clients_changed.connect(self._on_company_clients_changed)
        ev.workers_changed.connect(self._on_workers_changed)
        ev.incidents_changed.connect(self._on_incidents_changed)
        ev.templates_changed.connect(self._on_templates_changed)

        self.go_to("add_client")

    def _get_or_create_page(self, key: str) -> QWidget:
        """Lazy load pages: create only when first accessed."""
        if key in self._pages_cache:
            return self._pages_cache[key]

        # Create the page on-demand
        if key == "add_client":
            page = CompanyClientsPage()
            self.company_clients_page = page
        elif key == "add_template":
            page = TemplatesPage()
            self.templates_page = page
        elif key == "add_worker":
            page = WorkersPage()
            self.workers_page = page
        elif key == "incidents":
            page = IncidentsPage()
            self.incidents_page = page
        elif key == "generate_documents":
            page = GenerateDocumentsPage()
            self.generate_documents_page = page
        elif key == "reports":
            page = ReportsPage()
            self.reports_page = page
        else:
            return None

        # Add to stack and cache
        idx = self.stack.addWidget(page)
        self.pages[key] = idx
        self._pages_cache[key] = page
        return page

    def _build_pages(self) -> None:
        # Legacy method for compatibility; pages are now lazy-loaded.
        pass

    def go_to(self, key: str) -> None:
        if key not in self.pages and key not in self._pages_cache:
            # Create page if not yet loaded
            self._get_or_create_page(key)
        
        if key not in self.pages:
            return
        self.stack.setCurrentIndex(self.pages[key])
        self.sidebar.set_active(key)

    # -----------------------
    # Event-driven refresh
    # -----------------------
    def _on_company_clients_changed(self) -> None:
        # CompanyClients list itself
        if self.company_clients_page:
            self.company_clients_page.refresh()

        # Company clients are used as dropdowns in these pages
        if self.workers_page:
            # implement reload_clients() on WorkersPage (or call _load_clients if you expose it)
            if hasattr(self.workers_page, "reload_clients"):
                self.workers_page.reload_clients()
            self.workers_page.refresh()

        if self.templates_page:
            if hasattr(self.templates_page, "reload_clients"):
                self.templates_page.reload_clients()
            self.templates_page.refresh()

        if self.generate_documents_page:
            if hasattr(self.generate_documents_page, "reload_clients"):
                self.generate_documents_page.reload_clients()

        if self.reports_page:
            if hasattr(self.reports_page, "reload_clients"):
                self.reports_page.reload_clients()

    def _on_workers_changed(self) -> None:
        if self.workers_page:
            self.workers_page.refresh()

        # Incidents page needs workers list for the combo
        if self.incidents_page:
            if hasattr(self.incidents_page, "reload_workers"):
                self.incidents_page.reload_workers()
            self.incidents_page.refresh()

    def _on_incidents_changed(self) -> None:
        if self.incidents_page:
            self.incidents_page.refresh()

    def _on_templates_changed(self) -> None:
        if self.templates_page:
            self.templates_page.refresh()

    def on_logout(self) -> None:
        self._logout_handled = True
        sign_out()
        self.logged_out.emit()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        # End server-side session on graceful window close.
        if not self._logout_handled:
            try:
                sign_out()
            except Exception:
                pass
        super().closeEvent(event)