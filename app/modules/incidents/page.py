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

from app.repositories.incidents_repo import IncidentsRepo, IncidentRow
from app.modules.incidents.model import IncidentsTableModel


class IncidentsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

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

        # Initial load
        self._load_workers()
        self._load_types()
        self._sync_form_state()
        self.refresh()

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

    def _load_workers(self) -> None:
        try:
            workers = IncidentsRepo.list_workers_options()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load workers.\n\n{e}")
            workers = []

        self.worker_combo.blockSignals(True)
        self.worker_combo.clear()
        self.worker_combo.addItem("All", "")  # filter option
        for w in workers:
            self.worker_combo.addItem(w["label"], w["id"])
        self.worker_combo.setCurrentIndex(0)
        self.worker_combo.blockSignals(False)

        if not workers:
            QMessageBox.information(
                self,
                "No workers",
                "No active workers found. Create a worker first.",
            )

    def _load_types(self) -> None:
        try:
            types = IncidentsRepo.list_incident_types_options()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load incident types.\n\n{e}")
            types = []

        self.type_combo.clear()
        for t in types:
            self.type_combo.addItem(t["label"], t["id"])

        if not types:
            QMessageBox.information(
                self,
                "No incident types",
                "No incident types found. Seed the incident_types table first.",
            )

    def _on_worker_changed(self) -> None:
        self._sync_form_state()
        self.refresh()

    def _sync_form_state(self) -> None:
        """
        Save requires:
        - worker not All
        - incident type selected
        """
        worker_id = self.worker_combo.currentData()
        worker_ok = isinstance(worker_id, str) and bool(worker_id.strip())

        type_id = self.type_combo.currentData()
        type_ok = isinstance(type_id, int)

        self.save_btn.setEnabled(worker_ok and type_ok)

    def refresh(self) -> None:
        worker_id = self.worker_combo.currentData()
        if not isinstance(worker_id, str) or not worker_id.strip():
            worker_id = ""

        try:
            rows: List[IncidentRow] = IncidentsRepo.list_recent(worker_id=worker_id or None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load incidents.\n\n{e}")
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
            # not “wrong”, but usually suspicious. you can remove this if you want.
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

        self.refresh()