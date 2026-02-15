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
    QFileDialog,
    QCompleter,
)

from app.repositories.document_templates_repo import (
    DocumentTemplatesRepo,
    TemplateRow,
)


class TemplatesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        # ---- Filter row ----
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
        self._setup_searchable_combo(self.client_select)
        self.client_select.setMinimumWidth(280)

        self.template_type = QComboBox()
        self.template_type.setMinimumWidth(260)

        self.file_path_input = QLineEdit()
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setPlaceholderText("Select a .docx template...")

        self.pick_btn = QPushButton("Choose File")
        self.pick_btn.clicked.connect(self._pick_file)

        self.upload_btn = QPushButton("Upload Template")
        self.upload_btn.clicked.connect(self._on_upload)

        form.addWidget(QLabel("Client:"))
        form.addWidget(self.client_select)
        form.addWidget(QLabel("Type:"))
        form.addWidget(self.template_type)
        form.addWidget(self.file_path_input, stretch=1)
        form.addWidget(self.pick_btn)
        form.addWidget(self.upload_btn)

        layout.addLayout(form)

        # ---- Table ----
        self.table = QTableView()
        self.model = self._build_model()
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._on_deactivate)
        layout.addWidget(self.table)

        self._selected_file: Optional[str] = None

        self._load_clients()
        self._load_types()
        self.refresh()

    def _build_model(self):
        from app.modules.templates.model import TemplatesTableModel
        return TemplatesTableModel()

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

    def _load_clients(self) -> None:
        clients = DocumentTemplatesRepo.list_company_clients_options()

        # Filter combo defaults to All
        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

        # Create template requires a specific client (but can be locked by filter)
        self.client_select.clear()
        for c in clients:
            self.client_select.addItem(c["name"], c["id"])

        self._apply_client_lock()

    def _load_types(self) -> None:
        types_ = DocumentTemplatesRepo.list_incident_types_options()
        self.template_type.clear()
        # Use incident_types.code as template_key
        for t in types_:
            label = f"{t['name']} ({t['code']})"
            self.template_type.addItem(label, t["code"])

    def _on_filter_changed(self) -> None:
        self._apply_client_lock()
        self.refresh()

    def _apply_client_lock(self) -> None:
        selected = self.client_filter.currentData()
        selected_id = selected if isinstance(selected, str) else ""

        if selected_id.strip():
            # lock create combo to filtered client
            self._set_combo_by_data(self.client_select, selected_id)
            self.client_select.setEnabled(False)
        else:
            # All -> allow selecting any client when creating template
            self.client_select.setEnabled(True)

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, data_value: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == data_value:
                combo.setCurrentIndex(i)
                return

    def refresh(self) -> None:
        selected_client_id = self.client_filter.currentData()
        if not isinstance(selected_client_id, str):
            selected_client_id = ""

        rows: List[TemplateRow] = DocumentTemplatesRepo.list_templates(
            company_client_id=selected_client_id or None
        )
        self.model.load(rows)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DOCX template",
            "",
            "Word Documents (*.docx)",
        )
        if not path:
            return

        self._selected_file = path
        self.file_path_input.setText(path)

    def _on_upload(self) -> None:
        company_client_id = self.client_select.currentData()
        if not isinstance(company_client_id, str) or not company_client_id.strip():
            QMessageBox.warning(self, "Error", "Please select a company client.")
            return

        template_key = self.template_type.currentData()
        if not isinstance(template_key, str) or not template_key.strip():
            QMessageBox.warning(self, "Error", "Please select a template type.")
            return

        if not self._selected_file or not self._selected_file.lower().endswith(".docx"):
            QMessageBox.warning(self, "Error", "Please choose a .docx file.")
            return

        try:
            DocumentTemplatesRepo.create_template(
                company_client_id=company_client_id,
                template_key=template_key,
                local_file_path=self._selected_file,
            )
        except Exception as e:
            QMessageBox.critical(self, "Upload failed", str(e))
            return

        # Clear selection
        self._selected_file = None
        self.file_path_input.clear()

        self.refresh()

    def _on_deactivate(self, index: QModelIndex) -> None:
        row = index.row()
        template_id = self.model.template_id_at(row)

        confirm = QMessageBox.question(
            self,
            "Deactivate",
            "Deactivate this template?",
        )

        if confirm == QMessageBox.StandardButton.Yes:
            DocumentTemplatesRepo.deactivate(template_id)
            self.refresh()