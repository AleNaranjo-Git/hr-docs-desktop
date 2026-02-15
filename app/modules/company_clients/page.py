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

        self._is_busy: bool = False

        layout = QVBoxLayout(self)

        # ---- Form ----
        form = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Client name")
        self.name_input.setClearButtonEnabled(True)

        self.legal_id_input = QLineEdit()
        self.legal_id_input.setPlaceholderText("Legal ID")
        self.legal_id_input.setClearButtonEnabled(True)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description (optional)")
        self.desc_input.setClearButtonEnabled(True)

        self.save_btn = QPushButton("Add Client")
        self.save_btn.clicked.connect(self._on_add)
        self.save_btn.setDefault(True)

        form.addWidget(self.name_input)
        form.addWidget(self.legal_id_input)
        form.addWidget(self.desc_input)
        form.addWidget(self.save_btn)

        layout.addLayout(form)

        # Enter key UX
        self.name_input.returnPressed.connect(lambda: self.legal_id_input.setFocus())
        self.legal_id_input.returnPressed.connect(lambda: self.desc_input.setFocus())
        self.desc_input.returnPressed.connect(self._on_add)

        # ---- Table ----
        self.table = QTableView()
        self.model = CompanyClientsTableModel()
        self.table.setModel(self.model)

        self.table.doubleClicked.connect(self._on_deactivate)
        layout.addWidget(self.table)

        self.refresh()
        self.name_input.setFocus()

    # -------------------------
    # helpers
    # -------------------------
    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        self.save_btn.setEnabled(not busy)
        self.name_input.setEnabled(not busy)
        self.legal_id_input.setEnabled(not busy)
        self.desc_input.setEnabled(not busy)
        self.table.setEnabled(not busy)

    @staticmethod
    def _normalize_legal_id(value: str) -> str:
        # mild normalization: trim + remove spaces
        return value.strip().replace(" ", "")

    def refresh(self) -> None:
        try:
            rows = CompanyClientsRepo.list_active()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load clients.\n\n{e}")
            return
        self.model.load(rows)

    def _on_add(self) -> None:
        if self._is_busy:
            return

        name = self.name_input.text().strip()
        legal_id = self._normalize_legal_id(self.legal_id_input.text())
        desc: Optional[str] = self.desc_input.text().strip() or None

        if not name:
            QMessageBox.warning(self, "Missing info", "Client name is required.")
            self.name_input.setFocus()
            return

        if not legal_id:
            QMessageBox.warning(self, "Missing info", "Legal ID is required.")
            self.legal_id_input.setFocus()
            return

        if len(name) < 2:
            QMessageBox.warning(self, "Invalid name", "Client name is too short.")
            self.name_input.setFocus()
            return

        if len(legal_id) < 4:
            QMessageBox.warning(self, "Invalid Legal ID", "Legal ID looks too short.")
            self.legal_id_input.setFocus()
            return

        self._set_busy(True)
        try:
            CompanyClientsRepo.create(name, legal_id, desc)
        except Exception as e:
            # Common case: unique constraint, RLS, etc.
            QMessageBox.critical(self, "Create failed", str(e))
            return
        finally:
            self._set_busy(False)

        # Clear on success only
        self.name_input.clear()
        self.legal_id_input.clear()
        self.desc_input.clear()
        self.name_input.setFocus()

        self.refresh()

    def _on_deactivate(self, index: QModelIndex) -> None:
        if self._is_busy:
            return

        row = index.row()
        if row < 0:
            return

        client_id = self.model.client_id_at(row)
        client_name = self.model.client_name_at(row)

        confirm = QMessageBox.question(
            self,
            "Deactivate",
            f"Deactivate client '{client_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True)
        try:
            CompanyClientsRepo.deactivate(client_id)
        except Exception as e:
            QMessageBox.critical(self, "Deactivate failed", str(e))
            return
        finally:
            self._set_busy(False)

        self.refresh()