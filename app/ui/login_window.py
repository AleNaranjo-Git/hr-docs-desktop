from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from app.db.auth_service import sign_in, send_password_reset, AuthError
from app.ui.main_window import MainWindow


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HR Docs - Login")
        self.setMinimumSize(420, 220)

        self._is_busy: bool = False
        self.main: Optional[MainWindow] = None

        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Sign in")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        # Email
        root.addWidget(QLabel("Email"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("name@domain.com")
        self.email_input.setClearButtonEnabled(True)
        self.email_input.setInputMethodHints(
            Qt.InputMethodHint.ImhEmailCharactersOnly | Qt.InputMethodHint.ImhNoAutoUppercase
        )
        root.addWidget(self.email_input)

        # Password
        root.addWidget(QLabel("Password"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setClearButtonEnabled(True)
        root.addWidget(self.password_input)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.forgot_btn = QPushButton("Forgot password?")
        self.forgot_btn.clicked.connect(self.on_forgot_password)
        btn_row.addWidget(self.forgot_btn)

        # Optional: show/hide password toggle
        self.toggle_pw_btn = QPushButton("Show")
        self.toggle_pw_btn.setToolTip("Show/Hide password")
        self.toggle_pw_btn.clicked.connect(self._toggle_password_visibility)
        btn_row.addWidget(self.toggle_pw_btn)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.clicked.connect(self.on_login)
        self.login_btn.setDefault(True)
        btn_row.addWidget(self.login_btn)

        root.addLayout(btn_row)

        # Enter behavior: pressing Enter in password triggers login
        self.password_input.returnPressed.connect(self.on_login)

    # -------------------------
    # UI helpers
    # -------------------------
    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        self.login_btn.setEnabled(not busy)
        self.forgot_btn.setEnabled(not busy)
        self.toggle_pw_btn.setEnabled(not busy)

        # Light feedback
        self.setCursor(Qt.CursorShape.WaitCursor if busy else Qt.CursorShape.ArrowCursor)

    def _normalize_email(self, value: str) -> str:
        return value.strip()

    def _is_valid_email(self, value: str) -> bool:
        return bool(_EMAIL_RE.match(value))

    def _toggle_password_visibility(self) -> None:
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pw_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pw_btn.setText("Show")

    # -------------------------
    # Actions
    # -------------------------
    def on_login(self) -> None:
        if self._is_busy:
            return

        email = self._normalize_email(self.email_input.text())
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Missing info", "Please enter both email and password.")
            return

        if not self._is_valid_email(email):
            QMessageBox.warning(self, "Invalid email", "Please enter a valid email address.")
            return

        self._set_busy(True)

        try:
            sign_in(email, password)
        except AuthError as e:
            # Don’t leak internal details to end users (but still useful).
            QMessageBox.critical(self, "Login failed", str(e))
            self.password_input.clear()
            self.password_input.setFocus()
            return
        except Exception:
            # Catch-all: avoid crashing the UI with unexpected exceptions.
            QMessageBox.critical(self, "Login failed", "Unexpected error. Please try again.")
            self.password_input.clear()
            self.password_input.setFocus()
            return
        finally:
            self._set_busy(False)

        # Open main window
        self.main = MainWindow()
        self.main.logged_out.connect(self.show_again)
        self.main.show()
        self.close()

    def on_forgot_password(self) -> None:
        if self._is_busy:
            return

        email = self._normalize_email(self.email_input.text())
        if not email:
            QMessageBox.information(self, "Forgot password", "Type your email first, then click again.")
            self.email_input.setFocus()
            return

        if not self._is_valid_email(email):
            QMessageBox.warning(self, "Invalid email", "Please enter a valid email address.")
            self.email_input.setFocus()
            return

        self._set_busy(True)

        try:
            send_password_reset(email)
        except AuthError as e:
            QMessageBox.critical(self, "Reset failed", str(e))
            return
        except Exception:
            QMessageBox.critical(self, "Reset failed", "Unexpected error. Please try again.")
            return
        finally:
            self._set_busy(False)

        QMessageBox.information(
            self,
            "Email sent",
            "A password reset email was sent. Open the link, reset your password, then return to the app and sign in.",
        )

    def show_again(self) -> None:
        self.email_input.clear()
        self.password_input.clear()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.toggle_pw_btn.setText("Show")
        self._set_busy(False)
        self.show()
        self.email_input.setFocus()