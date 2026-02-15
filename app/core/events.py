from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppEvents(QObject):
    company_clients_changed = Signal()
    workers_changed = Signal()
    incidents_changed = Signal()
    templates_changed = Signal()


_singleton: AppEvents | None = None


def events() -> AppEvents:
    global _singleton
    if _singleton is None:
        _singleton = AppEvents()
    return _singleton