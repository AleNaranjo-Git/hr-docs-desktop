from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt

from app.repositories.reports_repo import ReportRow, ReportsRepo


def _fmt_dmy(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


class ReportsTableModel(QAbstractTableModel):
    HEADERS = [
        "CONSECUTIVO",
        "FECHA CONSECUTIVO",
        "PATRONO",
        "CORREO",
        "COLABORADOR",
        "FECHA INCIDENTE",
        "FALTA",
        "ESTADO",
        "OBSERVACIONES",
        "REVISIÓN",
    ]

    COL_ESTADO = 7
    COL_OBS = 8

    ESTADO_COL = COL_ESTADO
    OBS_COL = COL_OBS

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[ReportRow] = []

    def load(self, rows: List[ReportRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rows(self) -> List[ReportRow]:
        return list(self._rows)

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if role == int(Qt.ItemDataRole.DisplayRole) and orientation == Qt.Orientation.Horizontal:
            if 0 <= int(section) < len(self.HEADERS):
                return self.HEADERS[int(section)]
        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        base = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        col = int(index.column())
        if col in (self.COL_ESTADO, self.COL_OBS):
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid():
            return None

        r = int(index.row())
        c = int(index.column())
        if r < 0 or r >= len(self._rows):
            return None

        row = self._rows[r]

        if role in (int(Qt.ItemDataRole.DisplayRole), int(Qt.ItemDataRole.EditRole)):
            if c == 0:
                return row.consecutivo
            if c == 1:
                return _fmt_dmy(row.fecha_consecutivo)
            if c == 2:
                return row.patrono
            if c == 3:
                return row.correo
            if c == 4:
                return row.colaborador
            if c == 5:
                return _fmt_dmy(row.fecha_incidente)
            if c == 6:
                return row.falta
            if c == 7:
                return row.estado
            if c == 8:
                return row.observaciones
            if c == 9:
                return row.revision

        return None

    def setData(self, index: QModelIndex, value, role: int = int(Qt.ItemDataRole.EditRole)) -> bool:
        if not index.isValid() or role != int(Qt.ItemDataRole.EditRole):
            return False

        r = int(index.row())
        c = int(index.column())
        if r < 0 or r >= len(self._rows):
            return False

        current = self._rows[r]
        new_text = "" if value is None else str(value).strip()

        if c == self.COL_ESTADO:
            if not new_text:
                new_text = "PENDIENTE"

            allowed = {"PENDIENTE", "ENVIADO", "DESPEDIDO", "ERROR_ENVIO"}
            new_estado = new_text.upper()
            if new_estado not in allowed:
                return False

            ReportsRepo.upsert_meta(
                incident_id=current.incident_id,
                status=new_estado,
                report_observations=None,
            )

            self._rows[r] = ReportRow(**{**asdict(current), "estado": new_estado})
            self.dataChanged.emit(index, index)
            return True

        if c == self.COL_OBS:
            ReportsRepo.upsert_meta(
                incident_id=current.incident_id,
                status=None,
                report_observations=new_text,
            )

            self._rows[r] = ReportRow(**{**asdict(current), "observaciones": new_text})
            self.dataChanged.emit(index, index)
            return True

        return False