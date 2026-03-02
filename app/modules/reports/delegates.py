from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QWidget


class EstadoDelegate(QStyledItemDelegate):
    def __init__(self, estados: List[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._estados = estados

    def createEditor(self, parent: QWidget, option, index: QModelIndex):
        combo = QComboBox(parent)
        combo.addItems(self._estados)
        combo.setEditable(False)
        return combo

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        if not isinstance(editor, QComboBox):
            return

        value = index.data(Qt.ItemDataRole.DisplayRole)
        current = (str(value) if value is not None else "").strip().upper()

        # Default when empty
        if not current:
            current = "PENDIENTE"

        idx = editor.findText(current, Qt.MatchFlag.MatchFixedString)
        editor.setCurrentIndex(idx if idx >= 0 else 0)

    def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:
        if not isinstance(editor, QComboBox):
            return
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)