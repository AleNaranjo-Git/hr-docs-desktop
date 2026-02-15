from __future__ import annotations

from datetime import date
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QLineEdit,
    QCompleter,
)

from app.repositories.generate_documents_repo import (
    GenerateDocumentsRepo,
    IncidentForDoc,
)

from app.services.document_renderer import (
    DocContext,
    build_output_filename,
    render_docx,
    save_bytes,
)


class GenerateDocumentsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        # ---- Filters row ----
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Company client:"))

        self.client_filter = QComboBox()
        self._setup_searchable_combo(self.client_filter)
        filters.addWidget(self.client_filter)

        filters.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        filters.addWidget(self.date_from)

        filters.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        filters.addWidget(self.date_to)

        layout.addLayout(filters)

        # ---- Output folder row ----
        out_row = QHBoxLayout()

        self.out_folder_input = QLineEdit()
        self.out_folder_input.setReadOnly(True)
        self.out_folder_input.setPlaceholderText("Choose an output folder for generated documents...")

        self.pick_folder_btn = QPushButton("Choose Folder")
        self.pick_folder_btn.clicked.connect(self._pick_output_folder)

        self.generate_btn = QPushButton("Generate Documents")
        self.generate_btn.clicked.connect(self._on_generate)

        out_row.addWidget(self.out_folder_input, stretch=1)
        out_row.addWidget(self.pick_folder_btn)
        out_row.addWidget(self.generate_btn)

        layout.addLayout(out_row)

        self._output_folder: Optional[str] = None

        self._load_clients()
        self._init_dates()

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

    def _load_clients(self) -> None:
        clients = GenerateDocumentsRepo.list_company_clients_options()

        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

    def _init_dates(self) -> None:
        today = date.today()
        self.date_from.setDate(today.replace(day=1))
        self.date_to.setDate(today)

    def _pick_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if not folder:
            return
        self._output_folder = folder
        self.out_folder_input.setText(folder)

    def _on_generate(self) -> None:
        if not self._output_folder:
            QMessageBox.warning(self, "Missing folder", "Please choose an output folder first.")
            return

        q_from = self.date_from.date()
        q_to = self.date_to.date()

        date_from = date(q_from.year(), q_from.month(), q_from.day())
        date_to = date(q_to.year(), q_to.month(), q_to.day())

        if date_from > date_to:
            QMessageBox.warning(self, "Invalid range", "From date cannot be after To date.")
            return

        client_id = self.client_filter.currentData()
        if not isinstance(client_id, str):
            client_id = ""
        client_id = client_id.strip() or None

        try:
            incidents: List[IncidentForDoc] = GenerateDocumentsRepo.list_incidents_for_generation(
                date_from=date_from,
                date_to=date_to,
                company_client_id=client_id,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load incidents.\n\n{e}")
            return

        if not incidents:
            QMessageBox.information(self, "No incidents", "No incidents found for the selected filters.")
            return

        today = date.today()
        generated = 0
        failures: List[str] = []

        for inc in incidents:
            try:
                if not inc.code.strip():
                    raise RuntimeError(
                        f"Incident {inc.id} has empty code. "
                        "Make sure the incidents code trigger is working."
                    )

                template_key = inc.incident_type_code
                storage_path = GenerateDocumentsRepo.get_active_template_storage_path(
                    company_client_id=inc.company_client_id,
                    template_key=template_key,
                )
                if not storage_path:
                    raise RuntimeError(
                        f"No active template found for client '{inc.company_client_name}' "
                        f"and template '{template_key}'."
                    )

                template_bytes = GenerateDocumentsRepo.download_template_bytes(storage_path)

                ctx = DocContext(
                    today=today,
                    code=inc.code.strip(),
                    worker_name_upper=inc.worker_full_name.strip().upper(),
                    incident_date=inc.incident_date,
                    observations=inc.observations or "",
                )

                out_bytes = render_docx(template_bytes, ctx)

                filename = build_output_filename(
                    company_client_name=inc.company_client_name,
                    code=inc.code.strip(),
                    worker_full_name=inc.worker_full_name,
                    worker_national_id=inc.worker_national_id,
                    incident_type_code=inc.incident_type_code,
                )

                save_bytes(self._output_folder, filename, out_bytes)
                generated += 1

            except Exception as e:
                failures.append(f"{inc.code or inc.id}: {e}")

        if failures:
            msg = (
                f"Generated {generated} document(s).\n\n"
                f"Failures ({len(failures)}):\n- " + "\n- ".join(failures[:12])
            )
            if len(failures) > 12:
                msg += "\n- ... (more)"
            QMessageBox.warning(self, "Done (with issues)", msg)
        else:
            QMessageBox.information(self, "Done", f"Generated {generated} document(s).")