from __future__ import annotations

from typing import List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.repositories.document_templates_repo import TemplateRow


class TemplatesTableModel(QAbstractTableModel):
    HEADERS = ["Client", "Template Key", "Version", "Active", "Created At"]

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[TemplateRow] = []

    def load(self, rows: List[TemplateRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid() or role != int(Qt.ItemDataRole.DisplayRole):
            return None

        row = self._rows[index.row()]
        col = index.column()

        if col == 0:
            return row["company_client_name"]
        if col == 1:
            return row["template_key"]
        if col == 2:
            return str(row["version"])
        if col == 3:
            return "Yes" if row["is_active"] else "No"
        if col == 4:
            return row["created_at"]

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if role == int(Qt.ItemDataRole.DisplayRole) and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def template_id_at(self, row: int) -> str:
        return self._rows[row]["id"]