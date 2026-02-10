from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableView,
    QMessageBox,
)

from app.repositories.company_clients_repo import CompanyClientsRepo
from app.modules.company_clients.model import CompanyClientsTableModel


class CompanyClientsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        # ---- Form ----
        form = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Client name")

        self.legal_id_input = QLineEdit()
        self.legal_id_input.setPlaceholderText("Legal ID")

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description")

        self.save_btn = QPushButton("Add Client")
        self.save_btn.clicked.connect(self._on_add)

        form.addWidget(self.name_input)
        form.addWidget(self.legal_id_input)
        form.addWidget(self.desc_input)
        form.addWidget(self.save_btn)

        layout.addLayout(form)

        # ---- Table ----
        self.table = QTableView()
        self.model = CompanyClientsTableModel()
        self.table.setModel(self.model)

        # NOTE: doubleClicked emits a QModelIndex
        self.table.doubleClicked.connect(self._on_deactivate)

        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        rows = CompanyClientsRepo.list_active()
        self.model.load(rows)

    def _on_add(self) -> None:
        name = self.name_input.text().strip()
        legal_id = self.legal_id_input.text().strip()
        desc: Optional[str] = self.desc_input.text().strip() or None

        if not name or not legal_id:
            QMessageBox.warning(self, "Error", "Name and Legal ID are required")
            return

        CompanyClientsRepo.create(name, legal_id, desc)

        self.name_input.clear()
        self.legal_id_input.clear()
        self.desc_input.clear()

        self.refresh()

    def _on_deactivate(self, index: QModelIndex) -> None:
        row: int = index.row()
        client_id = self.model.client_id_at(row)

        confirm = QMessageBox.question(
            self,
            "Deactivate",
            "Deactivate this client?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            CompanyClientsRepo.deactivate(client_id)
            self.refresh()