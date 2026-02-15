from __future__ import annotations

from typing import List, TypedDict

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt


class WorkerRow(TypedDict):
    id: str
    full_name: str
    national_id: str
    company_client_id: str
    company_client_name: str
    created_at: str


class WorkersTableModel(QAbstractTableModel):
    HEADERS = ["Worker", "National ID", "Company Client", "Created At"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[WorkerRow] = []

    def load(self, rows: List[WorkerRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid():
            return None
        if role != int(Qt.ItemDataRole.DisplayRole):
            return None

        row = self._rows[int(index.row())]
        col = int(index.column())

        if col == 0:
            return row["full_name"]
        if col == 1:
            return row["national_id"]
        if col == 2:
            return row["company_client_name"]
        if col == 3:
            return row["created_at"]
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if role == int(Qt.ItemDataRole.DisplayRole) and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def worker_id_at(self, row: int) -> str:
        return self._rows[row]["id"]