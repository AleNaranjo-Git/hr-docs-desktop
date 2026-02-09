from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

from app.db.auth_service import sign_in, send_password_reset, AuthError
from app.ui.main_window import MainWindow


class LoginWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HR Docs - Login")
        self.setMinimumSize(420, 220)

        root = QVBoxLayout()
        root.setSpacing(10)

        title = QLabel("Sign in")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        # Email
        root.addWidget(QLabel("Email"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("name@domain.com")
        root.addWidget(self.email_input)

        # Password
        root.addWidget(QLabel("Password"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        root.addWidget(self.password_input)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.forgot_btn = QPushButton("Forgot password?")
        self.forgot_btn.clicked.connect(self.on_forgot_password)
        btn_row.addWidget(self.forgot_btn)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.clicked.connect(self.on_login)
        self.login_btn.setDefault(True)
        btn_row.addWidget(self.login_btn)

        root.addLayout(btn_row)
        self.setLayout(root)

    def on_login(self) -> None:
        email = self.email_input.text()
        password = self.password_input.text()

        self.login_btn.setEnabled(False)
        try:
            sign_in(email, password)
        except AuthError as e:
            QMessageBox.critical(self, "Login failed", str(e))
            return
        finally:
            self.login_btn.setEnabled(True)

        # Open the main window
        self.main = MainWindow()
        self.main.logged_out.connect(self.show_again)
        self.main.show()
        self.close()

    def on_forgot_password(self) -> None:
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.information(self, "Forgot password", "Type your email first, then click again.")
            return


        try:
            send_password_reset(email)
        except AuthError as e:
            QMessageBox.critical(self, "Reset failed", str(e))
            return

        QMessageBox.information(
            self,
            "Email sent",
            "A password reset email was sent. Open the link, reset your password, then return to the app and sign in."
        )
    
    def show_again(self) -> None:
        self.email_input.clear()
        self.password_input.clear()
        self.show()