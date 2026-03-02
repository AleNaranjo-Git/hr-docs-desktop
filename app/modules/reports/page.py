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
    QPushButton,
    QMessageBox,
    QFileDialog,
    QDateEdit,
    QCompleter,
    QLineEdit,
    QTableView,
    QAbstractItemView,
)

from app.core.events import events
from app.repositories.reports_repo import ReportsRepo, ReportRow
from app.modules.reports.model import ReportsTableModel
from app.modules.reports.delegates import EstadoDelegate
from app.services.reports_excel_exporter import ReportsExcelExporter, ReportsMetadata


class ReportsPage(QWidget):
    DEFAULT_HINT = "Muestra una tabla editable (ESTADO/OBSERVACIONES) y permite exportar exactamente lo filtrado."

    # UI list (with Todos)
    ESTADOS_UI = ["Todos", "PENDIENTE", "ENVIADO", "DESPEDIDO", "ERROR_ENVIO"]

    # Values actually saved in DB
    ESTADOS_DB = ["PENDIENTE", "ENVIADO", "DESPEDIDO", "ERROR_ENVIO"]

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Reportes (UD)")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        # ---- Filters row 1 ----
        row1 = QHBoxLayout()

        row1.addWidget(QLabel("Patrono:"))
        self.client_filter = QComboBox()
        self._setup_searchable_combo(self.client_filter)
        self.client_filter.currentIndexChanged.connect(self.refresh)
        row1.addWidget(self.client_filter, stretch=2)

        row1.addWidget(QLabel("Estado:"))
        self.estado_filter = QComboBox()
        self.estado_filter.addItems(self.ESTADOS_UI)
        self.estado_filter.currentIndexChanged.connect(self._apply_filters)
        row1.addWidget(self.estado_filter)

        row1.addWidget(QLabel("Buscar colaborador:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre o cédula...")
        self.search_input.textChanged.connect(self._apply_filters)
        row1.addWidget(self.search_input, stretch=2)

        layout.addLayout(row1)

        # ---- Filters row 2 ----
        row2 = QHBoxLayout()

        row2.addWidget(QLabel("Desde (received_day):"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.date_from)

        row2.addWidget(QLabel("Hasta:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.date_to)

        self.refresh_btn = QPushButton("Cargar")
        self.refresh_btn.clicked.connect(self.refresh)
        row2.addWidget(self.refresh_btn)

        self.export_btn = QPushButton("Exportar Excel")
        self.export_btn.clicked.connect(self._on_export)
        row2.addWidget(self.export_btn)

        layout.addLayout(row2)

        self.hint = QLabel(self.DEFAULT_HINT)
        self.hint.setStyleSheet("color: #666;")
        layout.addWidget(self.hint)

        # ---- Table ----
        self.table = QTableView()
        self.model = ReportsTableModel()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)

        # IMPORTANT: allow editing on double click / click / typing
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )

        # Delegate for Estado column (combo)
        # Your ReportsTableModel must expose ESTADO_COL
        self.table.setItemDelegateForColumn(
            self.model.ESTADO_COL,
            EstadoDelegate(self.ESTADOS_DB, self.table),
        )

        layout.addWidget(self.table, stretch=1)

        # internal: full data (before status/search filters)
        self._all_rows: List[ReportRow] = []

        events().company_clients_changed.connect(self.reload_clients)

        self._set_default_dates()
        self._load_clients()

        # initial load
        self.refresh()

        # Refresh when dates change
        self.date_from.dateChanged.connect(self.refresh)
        self.date_to.dateChanged.connect(self.refresh)

    def _setup_searchable_combo(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

        def apply_text_to_selection() -> None:
            text = combo.currentText().strip()
            if not text:
                combo.setCurrentIndex(0)
                return
            idx = combo.findText(text, Qt.MatchFlag.MatchFixedString)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

        completer.activated.connect(lambda _: apply_text_to_selection())
        if combo.lineEdit():
            combo.lineEdit().editingFinished.connect(apply_text_to_selection)

    def _set_default_dates(self) -> None:
        today = date.today()
        first = date(today.year, today.month, 1)

        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        self.date_from.setDate(first)
        self.date_to.setDate(today)
        self.date_from.blockSignals(False)
        self.date_to.blockSignals(False)

    def _load_clients(self) -> None:
        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("Todos", "")
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

        try:
            clients = ReportsRepo.list_company_clients_options()
        except Exception as e:
            self.hint.setText(f"No se pudieron cargar los patronos: {e}")
            self.export_btn.setEnabled(False)
            return

        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("Todos", "")
        for c in clients:
            self.client_filter.addItem(c["name"], c["id"])
        self.client_filter.setCurrentIndex(0)
        self.client_filter.blockSignals(False)

        self.export_btn.setEnabled(True)

    def _selected_client_id(self) -> Optional[str]:
        cid = self.client_filter.currentData()
        if not isinstance(cid, str):
            return None
        cid = cid.strip()
        return cid or None

    def refresh(self) -> None:
        self.refresh_btn.setEnabled(False)
        try:
            d_from = self.date_from.date().toPython()
            d_to = self.date_to.date().toPython()
            if d_from > d_to:
                QMessageBox.warning(self, "Error", "La fecha 'Desde' debe ser <= 'Hasta'.")
                return

            client_id = self._selected_client_id()

            try:
                rows = ReportsRepo.list_report_rows(
                    date_from=d_from,
                    date_to=d_to,
                    company_client_id=client_id,
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error cargando incidencias:\n\n{e}")
                return

            self._all_rows = rows
            self._apply_filters()
        finally:
            self.refresh_btn.setEnabled(True)

    def _apply_filters(self) -> None:
        estado_ui = (self.estado_filter.currentText() or "").strip()
        estado = None if estado_ui == "Todos" else estado_ui

        q = (self.search_input.text() or "").strip().lower()

        filtered: List[ReportRow] = []
        for r in self._all_rows:
            if estado and (r.estado or "").strip().upper() != estado.upper():
                continue

            if q:
                hay = f"{r.colaborador} {r.cedula}".lower()
                if q not in hay:
                    continue

            filtered.append(r)

        self.model.load(filtered)

        if not filtered:
            self.hint.setText("No hay datos para los filtros seleccionados.")
        else:
            self.hint.setText(self.DEFAULT_HINT)

    def _on_export(self) -> None:
        rows = self.model.rows()
        if not rows:
            QMessageBox.information(self, "Sin datos", "No hay filas para exportar.")
            return

        d_from = self.date_from.date().toPython()
        d_to = self.date_to.date().toPython()

        client_id = self._selected_client_id()
        if client_id:
            client_name = self.client_filter.currentText().strip() or "Cliente"
        else:
            client_name = "Todos"

        suggested = f"reporte_ud_{d_from.isoformat()}_a_{d_to.isoformat()}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte",
            suggested,
            "Excel Workbook (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            wb = ReportsExcelExporter.build_workbook(
                rows=rows,
                meta=ReportsMetadata(date_from=d_from, date_to=d_to, client_name=client_name),
            )
            wb.save(path)
        except Exception as e:
            QMessageBox.critical(self, "Exportación fallida", str(e))
            return

        QMessageBox.information(self, "Listo", "Reporte exportado correctamente.")

    def reload_clients(self) -> None:
        self._load_clients()
        self.refresh()