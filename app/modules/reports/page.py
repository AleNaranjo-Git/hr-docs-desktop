from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QDateEdit,
    QCompleter,
)

from app.core.events import events
from app.repositories.reports_repo import ReportsRepo
from app.services.reports_excel_exporter import ReportsExcelExporter, ReportsMetadata


class ReportsPage(QWidget):
    DEFAULT_HINT = "Exports an Excel report with multiple sheets based on received_day."

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Reports")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        # ---- Filters ----
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Company client:"))
        self.client_filter = QComboBox()
        self._setup_searchable_combo(self.client_filter)
        filters.addWidget(self.client_filter, stretch=1)

        filters.addWidget(QLabel("From (received_day):"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        filters.addWidget(self.date_from)

        filters.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        filters.addWidget(self.date_to)

        self.export_btn = QPushButton("Export Excel")
        self.export_btn.clicked.connect(self._on_export)
        filters.addWidget(self.export_btn)

        layout.addLayout(filters)

        self.hint = QLabel(self.DEFAULT_HINT)
        self.hint.setStyleSheet("color: #666;")
        layout.addWidget(self.hint)

        layout.addStretch(1)

        events().company_clients_changed.connect(self.reload_clients)

        self._set_default_dates()
        self._load_clients()
        self._apply_ui_state()

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

        # Hardening: typed text must match an item
        def apply_text_to_selection() -> None:
            text = combo.currentText().strip()
            if not text:
                combo.setCurrentIndex(0)  # default to "All"
                return
            idx = combo.findText(text, Qt.MatchFlag.MatchFixedString)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

        completer.activated.connect(lambda _: apply_text_to_selection())
        if combo.lineEdit():
            combo.lineEdit().editingFinished.connect(apply_text_to_selection)

    def _set_default_dates(self) -> None:
        today = date.today()
        first = date(today.year, today.month, 1)
        self.date_from.setDate(first)
        self.date_to.setDate(today)

    def _load_clients(self) -> None:
        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

        self._set_hint(self.DEFAULT_HINT)

        try:
            clients = ReportsRepo.list_company_clients_options()
        except Exception as e:
            self._set_hint(f"Could not load clients: {e}")
            self.export_btn.setEnabled(False)
            return

        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

        if len(clients) == 0:
            self._set_hint("No clients found. Add a client first to generate reports.")
        else:
            self._set_hint(self.DEFAULT_HINT)

        self.export_btn.setEnabled(True)

    def _apply_ui_state(self) -> None:
        if self.client_filter.count() == 0:
            self.export_btn.setEnabled(False)
        elif "Could not load clients" in (self.hint.text() or ""):
            self.export_btn.setEnabled(False)
        else:
            self.export_btn.setEnabled(True)

    def _on_export(self) -> None:
        self.export_btn.setEnabled(False)
        try:
            client_id = self.client_filter.currentData()
            if not isinstance(client_id, str):
                client_id = ""
            client_id = client_id.strip() or None

            d_from = self.date_from.date().toPython()
            d_to = self.date_to.date().toPython()

            if d_from > d_to:
                QMessageBox.warning(self, "Error", "From date must be <= To date.")
                return

            try:
                rows = ReportsRepo.list_incidents_for_reports(
                    date_from=d_from,
                    date_to=d_to,
                    company_client_id=client_id,
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load incidents.\n\n{e}")
                return

            if not rows:
                QMessageBox.information(self, "No data", "No incidents found for the selected filters.")
                return

            if client_id:
                client_name_ui = self.client_filter.currentText().strip() or "Cliente"
                client_name_es = client_name_ui
            else:
                client_name_es = "Todos"

            suggested = f"reporte_incidencias_{d_from.isoformat()}_a_{d_to.isoformat()}.xlsx"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Report",
                suggested,
                "Excel Workbook (*.xlsx)",
            )
            if not path:
                return

            if not path.lower().endswith(".xlsx"):
                path = path + ".xlsx"

            try:
                wb = ReportsExcelExporter.build_workbook(
                    incidents=rows,
                    meta=ReportsMetadata(date_from=d_from, date_to=d_to, client_name=client_name_es),
                )
                wb.save(path)
            except Exception as e:
                QMessageBox.critical(self, "Export failed", str(e))
                return

            QMessageBox.information(self, "Done", "Report exported successfully.")
        finally:
            self.export_btn.setEnabled(True)

    def reload_clients(self) -> None:
        self._load_clients()
        self._apply_ui_state()