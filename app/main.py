from __future__ import annotations

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv

# ---------- LOAD ENV PROPERLY ----------
if getattr(sys, "frozen", False):

    base_path = Path(sys._MEIPASS)
else:

    base_path = Path(__file__).resolve().parent.parent

env_path = base_path / ".env"
load_dotenv(env_path)

# ---------------------------------------

from app.ui.login_window import LoginWindow


def main() -> None:
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()