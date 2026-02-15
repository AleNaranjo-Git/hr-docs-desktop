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

        title = QLabel("Workers")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        self.hint = QLabel("")
        self.hint.setStyleSheet("color: #666;")
        layout.addWidget(self.hint)

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
        self._apply_filter_to_form()
        self.refresh()
        self._apply_ui_state()

    def _set_hint(self, text: str) -> None:
        self.hint.setText(text or "")

    def _apply_ui_state(self) -> None:
        has_clients = self.client_select.count() > 0

        self.client_filter.setEnabled(has_clients or self.client_filter.count() > 0)
        self.client_select.setEnabled(has_clients and self.client_select.isEnabled())
        self.full_name_input.setEnabled(has_clients)
        self.national_id_input.setEnabled(has_clients)
        self.save_btn.setEnabled(has_clients)

        if not has_clients:
            self._set_hint("No clients found. Add a client first before creating workers.")
        else:
            self._set_hint("")

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        # Hardening: typed text must match an item
        def apply_text_to_selection() -> None:
            text = combo.currentText().strip()
            if not text:
                combo.setCurrentIndex(-1)
                return

            idx = combo.findText(text, Qt.MatchFlag.MatchFixedString)
            combo.setCurrentIndex(idx if idx >= 0 else -1)

        completer.activated.connect(lambda _: apply_text_to_selection())
        if combo.lineEdit():
            combo.lineEdit().editingFinished.connect(apply_text_to_selection)

    def _load_clients(self) -> None:
        try:
            clients = WorkersRepo.list_company_clients_options()
        except Exception as e:
            self.client_filter.clear()
            self.client_filter.addItem("All", "")
            self.client_select.clear()
            self._set_hint(f"Could not load clients: {e}")
            return

        # Filter combo (includes "All")
        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)
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
        selected_client_id = self._selected_filter_client_id()

        if not selected_client_id:
            # All
            self.client_select.setEnabled(True)
            return

        idx = self.client_select.findData(selected_client_id)
        if idx != -1:
            self.client_select.blockSignals(True)
            self.client_select.setCurrentIndex(idx)
            self.client_select.blockSignals(False)

        self.client_select.setEnabled(False)

    def refresh(self) -> None:
        selected_client_id = self._selected_filter_client_id()

        try:
            rows: List[WorkerRow] = WorkersRepo.list_active(
                company_client_id=selected_client_id or None
            )
        except Exception as e:
            self.model.load([])
            self._set_hint(f"Could not load workers: {e}")
            return

        self.model.load(rows)

    def _on_add(self) -> None:
        if self.client_select.count() == 0:
            QMessageBox.warning(self, "Error", "No clients exist yet. Create a client first.")
            return

        # If user typed something and it doesn't match, currentIndex becomes -1
        if self.client_select.currentIndex() < 0:
            QMessageBox.warning(self, "Error", "Pick a company client from the list (typed text must match).")
            return

        company_client_id = self.client_select.currentData()
        if not isinstance(company_client_id, str) or not company_client_id.strip():
            QMessageBox.warning(self, "Error", "Please select a company client.")
            return

        full_name = self.full_name_input.text().strip()
        national_id = self.national_id_input.text().strip()

        if not full_name or not national_id:
            QMessageBox.warning(self, "Error", "Full name and National ID are required.")
            return

        self.save_btn.setEnabled(False)
        try:
            WorkersRepo.create(
                company_client_id=company_client_id,
                full_name=full_name,
                national_id=national_id,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        finally:
            self.save_btn.setEnabled(True)

        self.full_name_input.clear()
        self.national_id_input.clear()
        self.refresh()

    def _on_deactivate(self, index: QModelIndex) -> None:
        row = index.row()
        worker_id = self.model.worker_id_at(row)
        if not worker_id:
            return

        confirm = QMessageBox.question(
            self,
            "Deactivate",
            "Deactivate this worker?",
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                WorkersRepo.deactivate(worker_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self.refresh()