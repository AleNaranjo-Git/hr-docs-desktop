from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QModelIndex, Qt, QDate
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QTableView,
    QMessageBox,
    QCompleter,
)

from app.core.events import events
from app.repositories.incidents_repo import IncidentsRepo, IncidentRow
from app.modules.incidents.model import IncidentsTableModel


class IncidentsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Incidents")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        # Non-blocking hint (replaces popups like "No workers")
        self.hint = QLabel("")
        self.hint.setStyleSheet("color: #666;")
        layout.addWidget(self.hint)

        # ---- Worker filter/target ----
        top = QHBoxLayout()
        top.addWidget(QLabel("Worker:"))

        self.worker_combo = QComboBox()
        self.worker_combo.setMinimumWidth(360)
        self._setup_searchable_combo(self.worker_combo)
        self.worker_combo.currentIndexChanged.connect(self._on_worker_changed)

        top.addWidget(self.worker_combo)
        top.addStretch(1)
        layout.addLayout(top)

        # ---- Form ----
        form = QHBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(260)

        self.incident_date = QDateEdit()
        self.incident_date.setCalendarPopup(True)
        self.incident_date.setDisplayFormat("yyyy-MM-dd")
        self.incident_date.setDate(QDate.currentDate())

        self.received_day = QDateEdit()
        self.received_day.setCalendarPopup(True)
        self.received_day.setDisplayFormat("yyyy-MM-dd")
        self.received_day.setDate(QDate.currentDate())

        self.manual_cb = QCheckBox("Manual handling")

        self.save_btn = QPushButton("Add Incident")
        self.save_btn.clicked.connect(self._on_add)

        form.addWidget(QLabel("Type:"))
        form.addWidget(self.type_combo)
        form.addWidget(QLabel("Incident date:"))
        form.addWidget(self.incident_date)
        form.addWidget(QLabel("Received day:"))
        form.addWidget(self.received_day)
        form.addWidget(self.manual_cb)
        form.addWidget(self.save_btn)

        layout.addLayout(form)

        # Observations
        obs_row = QVBoxLayout()
        obs_row.addWidget(QLabel("Observations:"))
        self.observations = QTextEdit()
        self.observations.setPlaceholderText("Optional notes about the incident...")
        self.observations.setFixedHeight(90)
        obs_row.addWidget(self.observations)
        layout.addLayout(obs_row)

        # ---- Table ----
        self.table = QTableView()
        self.model = IncidentsTableModel()
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._on_delete)
        layout.addWidget(self.table)

        # ---- Subscribe to global events ----
        events().workers_changed.connect(self._on_workers_changed)
        events().incidents_changed.connect(self._on_incidents_changed)

        # Initial load
        self._load_types()
        self._load_workers()
        self._sync_form_state()
        self.refresh()

    def _set_hint(self, text: str) -> None:
        self.hint.setText(text or "")

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        # Optional hardening (same pattern as other pages): typed text must match
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

    def _load_workers(self) -> None:
        try:
            workers = IncidentsRepo.list_workers_options()
        except Exception as e:
            self._set_hint(f"Could not load workers: {e}")
            workers = []

        self.worker_combo.blockSignals(True)
        self.worker_combo.clear()
        self.worker_combo.addItem("All", "")  # filter option
        for w in workers:
            self.worker_combo.addItem(w["label"], w["id"])
        self.worker_combo.setCurrentIndex(0)
        self.worker_combo.blockSignals(False)

        if not workers:
            # NO POPUP — just a hint
            self._set_hint("No workers yet. Create a worker first to add incidents.")
        else:
            # Clear hint only if the hint was about missing workers
            if "No workers yet" in self.hint.text():
                self._set_hint("")

        self._sync_form_state()

    def _load_types(self) -> None:
        try:
            types_ = IncidentsRepo.list_incident_types_options()
        except Exception as e:
            self._set_hint(f"Could not load incident types: {e}")
            types_ = []

        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for t in types_:
            self.type_combo.addItem(t["label"], t["id"])
        self.type_combo.blockSignals(False)

        if not types_:
            # Non-blocking hint
            self._set_hint("No incident types found. Seed the incident_types table first.")

        self._sync_form_state()

    def _on_worker_changed(self) -> None:
        self._sync_form_state()
        self.refresh()

    def _sync_form_state(self) -> None:
        """
        Save requires:
        - worker not All
        - incident type selected
        - and workers/types exist
        """
        has_workers = self.worker_combo.count() > 1  # includes "All"
        has_types = self.type_combo.count() > 0

        worker_id = self.worker_combo.currentData()
        worker_ok = isinstance(worker_id, str) and bool(worker_id.strip())

        type_id = self.type_combo.currentData()
        type_ok = isinstance(type_id, int)

        form_enabled = has_workers and has_types
        self.type_combo.setEnabled(form_enabled)
        self.incident_date.setEnabled(form_enabled)
        self.received_day.setEnabled(form_enabled)
        self.manual_cb.setEnabled(form_enabled)
        self.observations.setEnabled(form_enabled)

        self.save_btn.setEnabled(worker_ok and type_ok and form_enabled)

    def refresh(self) -> None:
        worker_id = self.worker_combo.currentData()
        if not isinstance(worker_id, str) or not worker_id.strip():
            worker_id = ""

        try:
            rows: List[IncidentRow] = IncidentsRepo.list_recent(worker_id=worker_id or None)
        except Exception as e:
            self._set_hint(f"Could not load incidents: {e}")
            rows = []

        self.model.load(rows)

    def _on_add(self) -> None:
        worker_id = self.worker_combo.currentData()
        if not isinstance(worker_id, str) or not worker_id.strip():
            QMessageBox.warning(self, "Error", "Please select a Worker (not 'All') to create an incident.")
            return

        incident_type_id = self.type_combo.currentData()
        if not isinstance(incident_type_id, int):
            QMessageBox.warning(self, "Error", "Please select an incident type.")
            return

        incident_date_str = self.incident_date.date().toString("yyyy-MM-dd")
        received_day_str = self.received_day.date().toString("yyyy-MM-dd")

        if received_day_str < incident_date_str:
            confirm = QMessageBox.question(
                self,
                "Check dates",
                "Received day is earlier than Incident date. Continue?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        observations_text = self.observations.toPlainText().strip()
        observations: Optional[str] = observations_text or None

        self.save_btn.setEnabled(False)
        try:
            IncidentsRepo.create(
                worker_id=worker_id,
                incident_type_id=incident_type_id,
                incident_date=incident_date_str,
                received_day=received_day_str,
                observations=observations,
                manual_handling=self.manual_cb.isChecked(),
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not create incident:\n{e}")
            return
        finally:
            self._sync_form_state()

        # reset UI
        self.observations.clear()
        self.manual_cb.setChecked(False)
        self.incident_date.setDate(QDate.currentDate())
        self.received_day.setDate(QDate.currentDate())

        # Notify + refresh
        events().incidents_changed.emit()
        self.refresh()

    def _on_delete(self, index: QModelIndex) -> None:
        row = index.row()
        incident_id = self.model.incident_id_at(row)

        confirm = QMessageBox.question(self, "Delete Incident", "Delete this incident?")
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            IncidentsRepo.delete(incident_id)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not delete incident:\n{e}")
            return

        events().incidents_changed.emit()
        self.refresh()

    # ---- Event handlers ----
    def _on_workers_changed(self) -> None:
        self._load_workers()
        self.refresh()

    def _on_incidents_changed(self) -> None:
        self.refresh()

    # Optional explicit calls
    def reload_workers(self) -> None:
        self._load_workers()

    def reload_types(self) -> None:
        self._load_types()