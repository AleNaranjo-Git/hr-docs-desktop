from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableView,
    QMessageBox,
    QComboBox,
    QLabel,
    QCompleter,
)

from app.repositories.workers_repo import WorkersRepo
from app.modules.workers.model import WorkersTableModel, WorkerRow


class WorkersPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        # ---- Top filter ----
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Company client:"))

        self.client_filter = QComboBox()
        self._setup_searchable_combo(self.client_filter)
        self.client_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.client_filter)

        layout.addLayout(filter_row)

        # ---- Form ----
        form = QHBoxLayout()

        self.client_select = QComboBox()
        self.client_select.setMinimumWidth(240)
        self._setup_searchable_combo(self.client_select)

        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("Worker full name")

        self.national_id_input = QLineEdit()
        self.national_id_input.setPlaceholderText("National ID")

        self.save_btn = QPushButton("Add Worker")
        self.save_btn.clicked.connect(self._on_add)

        form.addWidget(self.client_select)
        form.addWidget(self.full_name_input)
        form.addWidget(self.national_id_input)
        form.addWidget(self.save_btn)

        layout.addLayout(form)

        # ---- Table ----
        self.table = QTableView()
        self.model = WorkersTableModel()
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._on_deactivate)

        layout.addWidget(self.table)

        self._load_clients()

        # Default is "All" and we want form combo enabled in that case
        self._apply_filter_to_form()
        self.refresh()

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

    def _load_clients(self) -> None:
        clients = WorkersRepo.list_company_clients_options()

        # Filter combo (includes "All")
        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")  # default visible text = All
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)  # force default to All
        self.client_filter.blockSignals(False)

        # Create worker combo (must pick one)
        self.client_select.blockSignals(True)
        self.client_select.clear()
        for c in clients:
            self.client_select.addItem(c["name"], c["id"])
        self.client_select.setCurrentIndex(0 if self.client_select.count() > 0 else -1)
        self.client_select.blockSignals(False)

    def _on_filter_changed(self) -> None:
        self._apply_filter_to_form()
        self.refresh()

    def _selected_filter_client_id(self) -> str:
        selected = self.client_filter.currentData()
        if isinstance(selected, str):
            return selected.strip()
        return ""

    def _apply_filter_to_form(self) -> None:
        """
        If filter = All -> allow choosing company client for new worker.
        If filter = specific client -> lock form to that same client.
        """
        selected_client_id = self._selected_filter_client_id()

        if not selected_client_id:
            # All
            self.client_select.setEnabled(True)
            return

        # Specific client selected in filter: force the form combo to it and lock it
        idx = self.client_select.findData(selected_client_id)
        if idx != -1:
            self.client_select.blockSignals(True)
            self.client_select.setCurrentIndex(idx)
            self.client_select.blockSignals(False)

        self.client_select.setEnabled(False)

    def refresh(self) -> None:
        selected_client_id = self._selected_filter_client_id()

        rows: List[WorkerRow] = WorkersRepo.list_active(
            company_client_id=selected_client_id or None
        )
        self.model.load(rows)

    def _on_add(self) -> None:
        company_client_id = self.client_select.currentData()
        if not isinstance(company_client_id, str) or not company_client_id.strip():
            QMessageBox.warning(self, "Error", "Please select a company client.")
            return

        full_name = self.full_name_input.text().strip()
        national_id = self.national_id_input.text().strip()

        if not full_name or not national_id:
            QMessageBox.warning(self, "Error", "Full name and National ID are required.")
            return

        WorkersRepo.create(
            company_client_id=company_client_id,
            full_name=full_name,
            national_id=national_id,
        )

        self.full_name_input.clear()
        self.national_id_input.clear()

        # No need to reload clients after adding a worker
        self.refresh()

    def _on_deactivate(self, index: QModelIndex) -> None:
        row = index.row()
        worker_id = self.model.worker_id_at(row)

        confirm = QMessageBox.question(
            self,
            "Deactivate",
            "Deactivate this worker?",
        )

        if confirm == QMessageBox.StandardButton.Yes:
            WorkersRepo.deactivate(worker_id)
            self.refresh()