from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

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
from app.repositories.generated_documents_repo import GeneratedDocumentsRepo

from app.services.document_renderer import (
    DocContext,
    build_output_filename,
    render_docx,
    save_bytes,
    assert_required_placeholders,
)


# Required placeholders by incident_type_code
REQUIRED_FIELDS: Dict[str, List[str]] = {
    "JOB_ABANDONMENT": ["today", "code", "name", "incident_date", "observations"],
    "ABSENCE": ["today", "code", "name", "incident_date"],
    "LATE_ARRIVAL": ["today", "code", "name", "incident_date"],
}


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
        self.out_folder_input.setPlaceholderText(
            "Choose an output folder for generated documents..."
        )

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
            QMessageBox.warning(
                self, "Missing folder", "Please choose an output folder first."
            )
            return

        q_from = self.date_from.date()
        q_to = self.date_to.date()

        date_from = date(q_from.year(), q_from.month(), q_from.day())
        date_to = date(q_to.year(), q_to.month(), q_to.day())

        if date_from > date_to:
            QMessageBox.warning(
                self, "Invalid range", "From date cannot be after To date."
            )
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
            QMessageBox.information(
                self, "No incidents", "No incidents found for the selected filters."
            )
            return

        # -------------------------
        # PRE-FLIGHT (ALL-OR-NOTHING)
        # -------------------------
        today = date.today()

        errors: List[str] = []

        # Cache templates by (company_client_id, template_key)
        template_cache: Dict[Tuple[str, str], bytes] = {}

        # Cache active template metadata by (company_client_id, template_key)
        active_template_cache: Dict[Tuple[str, str], Tuple[str, int]] = {}

        # Duplicate tracking (already generated) - we will SKIP them in generation
        already_generated: List[str] = []

        for inc in incidents:
            code = (inc.code or "").strip()
            if not code:
                errors.append(f"Incident {inc.id} has empty code (trigger not applied?).")
                continue

            template_key = inc.incident_type_code.strip()
            if not template_key:
                errors.append(f"{code}: incident_type_code is empty.")
                continue

            required = REQUIRED_FIELDS.get(template_key)
            if not required:
                errors.append(
                    f"{code}: no REQUIRED_FIELDS configured for template_key '{template_key}'."
                )
                continue

            cache_key = (inc.company_client_id, template_key)

            # Get active template (storage_path + version)
            if cache_key not in active_template_cache:
                active = GenerateDocumentsRepo.get_active_template(
                    company_client_id=inc.company_client_id,
                    template_key=template_key,
                )
                if not active:
                    errors.append(
                        f"{code}: missing ACTIVE template for client '{inc.company_client_name}' ({template_key})."
                    )
                    continue
                active_template_cache[cache_key] = (active["storage_path"], active["version"])

            storage_path, template_version = active_template_cache[cache_key]

            # Check duplicate (already generated)
            try:
                exists = GeneratedDocumentsRepo.exists_for_incident(
                    incident_id=inc.id,
                    template_key=template_key,
                    template_version=template_version,
                )
                if exists:
                    already_generated.append(code)
                    # We do NOT treat as error; we skip later.
            except Exception as e:
                errors.append(f"{code}: failed duplicate-check against generated_documents: {e}")
                continue

            # Download template bytes once per client+key
            if cache_key not in template_cache:
                try:
                    template_cache[cache_key] = GenerateDocumentsRepo.download_template_bytes(
                        storage_path
                    )
                except Exception as e:
                    errors.append(f"{code}: failed to download template ({template_key}): {e}")
                    continue

            # Validate placeholders exist in template
            try:
                assert_required_placeholders(template_cache[cache_key], required)
            except Exception as e:
                errors.append(f"{code}: template '{template_key}' missing placeholders: {e}")

        if errors:
            msg = "Generation stopped. Fix these issues first:\n\n- " + "\n- ".join(errors[:14])
            if len(errors) > 14:
                msg += "\n- ... (more)"
            QMessageBox.critical(self, "Cannot generate", msg)
            return

        # If everything is already generated, tell user and stop
        # (still ALL-OR-NOTHING: nothing new to generate)
        # NOTE: We check this by computing which ones we would generate.
        to_generate: List[IncidentForDoc] = []
        for inc in incidents:
            template_key = inc.incident_type_code.strip()
            ck = (inc.company_client_id, template_key)
            _, template_version = active_template_cache[ck]

            if not GeneratedDocumentsRepo.exists_for_incident(
                incident_id=inc.id,
                template_key=template_key,
                template_version=template_version,
            ):
                to_generate.append(inc)

        if not to_generate:
            QMessageBox.information(
                self,
                "Nothing to do",
                "All documents for the selected range were already generated for the current active template versions.",
            )
            return

        # Optional: warn user that some were skipped (not an error)
        if already_generated:
            # Keep it short
            QMessageBox.information(
                self,
                "Some already generated",
                f"{len(already_generated)} incident(s) already have generated documents for the active template versions and will be skipped.",
            )

        # -------------------------
        # GENERATE (safe to proceed)
        # -------------------------
        generated = 0
        db_written = 0

        try:
            for inc in to_generate:
                template_key = inc.incident_type_code.strip()
                cache_key = (inc.company_client_id, template_key)

                template_bytes = template_cache[cache_key]
                storage_path, template_version = active_template_cache[cache_key]

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

                out_path = save_bytes(self._output_folder, filename, out_bytes)
                generated += 1

                # record it
                GeneratedDocumentsRepo.create(
                    company_client_id=inc.company_client_id,
                    incident_id=inc.id,
                    template_key=template_key,
                    template_version=template_version,
                    output_path=out_path,
                )
                db_written += 1

        except Exception as e:
            QMessageBox.critical(self, "Generation failed", str(e))
            return

        QMessageBox.information(
            self,
            "Done",
            f"Generated {generated} document(s).\nRecorded {db_written} row(s) in generated_documents.",
        )