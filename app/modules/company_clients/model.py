from __future__ import annotations
from typing import List, Dict
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex


class CompanyClientsTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Legal ID", "Description", "Created At"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[Dict] = []

    def load(self, rows: List[Dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        row = self._rows[index.row()]
        col = index.column()

        if col == 0:
            return row["name"]
        if col == 1:
            return row["legal_id"]
        if col == 2:
            return row.get("description", "")
        if col == 3:
            return row["created_at"]

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def client_id_at(self, row: int) -> str:
        return self._rows[row]["id"]