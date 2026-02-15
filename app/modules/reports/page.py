from __future__ import annotations

from datetime import date
from typing import Optional

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

from app.repositories.reports_repo import ReportsRepo
from app.services.reports_excel_exporter import ReportsExcelExporter, ReportsMetadata


class ReportsPage(QWidget):
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

        hint = QLabel("Exports an Excel report with multiple sheets based on received_day.")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        layout.addStretch(1)

        self._load_clients()
        self._set_default_dates()

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

    def _load_clients(self) -> None:
        clients = ReportsRepo.list_company_clients_options()

        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All", "")  # UI in English
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

    def _set_default_dates(self) -> None:
        today = date.today()
        first = date(today.year, today.month, 1)

        self.date_from.setDate(first)
        self.date_to.setDate(today)

    def _on_export(self) -> None:
        client_id = self.client_filter.currentData()
        if not isinstance(client_id, str):
            client_id = ""
        client_id = client_id.strip() or None

        d_from = self.date_from.date().toPython()
        d_to = self.date_to.date().toPython()

        if d_from > d_to:
            QMessageBox.warning(self, "Error", "From date must be <= To date.")
            return

        # Pull data
        rows = ReportsRepo.list_incidents_for_reports(
            date_from=d_from,
            date_to=d_to,
            company_client_id=client_id,
        )

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