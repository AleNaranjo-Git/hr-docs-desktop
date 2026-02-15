from __future__ import annotations

from typing import TypedDict, Sequence, Optional, Union, Any

from PySide6.QtCore import (
    QAbstractTableModel,
    Qt,
    QModelIndex,
    QPersistentModelIndex,
)

IndexLike = Union[QModelIndex, QPersistentModelIndex]


class CompanyClientRow(TypedDict):
    id: str
    name: str
    legal_id: str
    description: Optional[str]
    created_at: str


class CompanyClientsTableModel(QAbstractTableModel):
    HEADERS: list[str] = ["Name", "Legal ID", "Description", "Created At"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[CompanyClientRow] = []

    def load(self, rows: Sequence[CompanyClientRow]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent: IndexLike = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: IndexLike = QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(
        self,
        index: IndexLike,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        if not index.isValid() or role != int(Qt.ItemDataRole.DisplayRole):
            return None

        r = index.row()
        c = index.column()
        if r < 0 or r >= len(self._rows):
            return None

        row = self._rows[r]

        if c == 0:
            return row["name"]
        if c == 1:
            return row["legal_id"]
        if c == 2:
            return row.get("description") or ""
        if c == 3:
            return row["created_at"]

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        if role == int(Qt.ItemDataRole.DisplayRole) and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None

    def client_id_at(self, row: int) -> str:
        if row < 0 or row >= len(self._rows):
            return ""
        return self._rows[row]["id"]

    def client_name_at(self, row: int) -> str:
        if row < 0 or row >= len(self._rows):
            return ""
        return self._rows[row]["name"]