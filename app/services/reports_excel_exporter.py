from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from app.repositories.reports_repo import ReportIncidentRow


SPANISH_MONTHS = [
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def format_date_es(d: date) -> str:
    return f"{d.day} de {SPANISH_MONTHS[d.month]} de {d.year}"


def _auto_fit(ws) -> None:
    for col in range(1, ws.max_column + 1):
        max_len = 0
        col_letter = get_column_letter(col)
        for row in range(1, ws.max_row + 1):
            v = ws.cell(row=row, column=col).value
            if v is None:
                continue
            max_len = max(max_len, len(str(v)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)


_sheet_bad = re.compile(r"[\[\]\:\*\?\/\\]+")


def _safe_sheet_name(name: str) -> str:
    s = name.strip()
    s = _sheet_bad.sub("-", s)
    return s[:31] if len(s) > 31 else s


@dataclass(frozen=True)
class ReportsMetadata:
    date_from: date
    date_to: date
    client_name: str


class ReportsExcelExporter:
    @staticmethod
    def build_workbook(
        *,
        incidents: List[ReportIncidentRow],
        meta: ReportsMetadata,
    ) -> Workbook:
        wb = Workbook()
        default = wb.active
        wb.remove(default)

        ReportsExcelExporter._sheet_resumen_por_tipo(wb, incidents, meta)
        ReportsExcelExporter._sheet_resumen_por_trabajador(wb, incidents, meta)
        ReportsExcelExporter._sheet_resumen_por_cliente(wb, incidents, meta)
        ReportsExcelExporter._sheet_detalle(wb, incidents, meta)

        return wb

    @staticmethod
    def _add_report_header(ws, meta: ReportsMetadata) -> None:
        ws.append(["Reporte de incidencias"])
        ws.append(["Rango (received_day):", format_date_es(meta.date_from), "a", format_date_es(meta.date_to)])
        ws.append(["Cliente:", meta.client_name])
        ws.append([])

    @staticmethod
    def _sheet_resumen_por_tipo(wb: Workbook, incidents: List[ReportIncidentRow], meta: ReportsMetadata) -> None:
        ws = wb.create_sheet(_safe_sheet_name("Resumen - Por tipo"))
        ReportsExcelExporter._add_report_header(ws, meta)

        counts: Dict[Tuple[str, str], int] = defaultdict(int)
        for r in incidents:
            counts[(r.incident_type_code, r.incident_type_name)] += 1

        ws.append(["Código tipo", "Tipo", "Cantidad"])
        for (code, name), n in sorted(counts.items(), key=lambda x: (x[0][0], x[0][1])):
            ws.append([code, name, n])

        _auto_fit(ws)

    @staticmethod
    def _sheet_resumen_por_trabajador(wb: Workbook, incidents: List[ReportIncidentRow], meta: ReportsMetadata) -> None:
        ws = wb.create_sheet(_safe_sheet_name("Resumen - Por trabajador"))
        ReportsExcelExporter._add_report_header(ws, meta)

        type_list = sorted(
            {(r.incident_type_code, r.incident_type_name) for r in incidents},
            key=lambda x: (x[0], x[1]),
        )

        by_worker: Dict[Tuple[str, str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        totals: Dict[Tuple[str, str, str], int] = defaultdict(int)

        for r in incidents:
            wk = (r.company_client_name, r.worker_full_name, r.worker_national_id)
            by_worker[wk][r.incident_type_code] += 1
            totals[wk] += 1

        header = ["Cliente", "Trabajador", "Cédula", "Total"] + [f"{code}" for code, _ in type_list]
        ws.append(header)

        for wk in sorted(by_worker.keys(), key=lambda x: (x[0], x[1], x[2])):
            client_name, worker_name, nat_id = wk
            row = [client_name, worker_name, nat_id, totals[wk]]
            for code, _ in type_list:
                row.append(by_worker[wk].get(code, 0))
            ws.append(row)

        _auto_fit(ws)

    @staticmethod
    def _sheet_resumen_por_cliente(wb: Workbook, incidents: List[ReportIncidentRow], meta: ReportsMetadata) -> None:
        ws = wb.create_sheet(_safe_sheet_name("Resumen - Por cliente"))
        ReportsExcelExporter._add_report_header(ws, meta)

        counts: Dict[str, int] = defaultdict(int)
        for r in incidents:
            counts[r.company_client_name] += 1

        ws.append(["Cliente", "Cantidad"])
        for client, n in sorted(counts.items(), key=lambda x: x[0]):
            ws.append([client, n])

        _auto_fit(ws)

    @staticmethod
    def _sheet_detalle(wb: Workbook, incidents: List[ReportIncidentRow], meta: ReportsMetadata) -> None:
        ws = wb.create_sheet(_safe_sheet_name("Detalle"))
        ReportsExcelExporter._add_report_header(ws, meta)

        ws.append(
            [
                "Cliente",
                "Trabajador",
                "Cédula",
                "Tipo (código)",
                "Tipo (nombre)",
                "received_day",
            ]
        )

        for r in incidents:
            ws.append(
                [
                    r.company_client_name,
                    r.worker_full_name,
                    r.worker_national_id,
                    r.incident_type_code,
                    r.incident_type_name,
                    format_date_es(r.received_day),
                ]
            )

        _auto_fit(ws)