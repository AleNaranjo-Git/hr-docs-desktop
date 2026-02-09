from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from app.ui.login_window import LoginWindow

def main() -> None:
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()