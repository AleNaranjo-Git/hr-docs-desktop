from __future__ import annotations

from typing import List

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QPersistentModelIndex

from app.repositories.incidents_repo import IncidentRow


class IncidentsTableModel(QAbstractTableModel):
    HEADERS = [
        "Code",
        "Received Day",
        "Incident Date",
        "Worker",
        "Type",
        "Manual",
        "Created At",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[IncidentRow] = []

    def load(self, rows: List[IncidentRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid() or role != int(Qt.ItemDataRole.DisplayRole):
            return None

        row = self._rows[int(index.row())]
        col = int(index.column())

        if col == 0:
            return row["code"]
        if col == 1:
            return row["received_day"]
        if col == 2:
            return row["incident_date"]
        if col == 3:
            return row["worker_name"]
        if col == 4:
            return row["incident_type"]
        if col == 5:
            return "Yes" if row["manual_handling"] else "No"
        if col == 6:
            return row["created_at"]

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if role == int(Qt.ItemDataRole.DisplayRole) and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[int(section)]
        return None

    def incident_id_at(self, row: int) -> str:
        return self._rows[row]["id"]