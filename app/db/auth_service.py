from __future__ import annotations

from typing import Optional

from app.core.session import AppSession, SessionState
from app.db.supabase_client import get_supabase


class AuthError(Exception):
    pass


def sign_in(email: str, password: str) -> SessionState:
    email = email.strip()
    if not email or not password:
        raise AuthError("Email and password are required.")

    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        raise AuthError(f"Login failed: {e}") from e

    session = getattr(res, "session", None)
    if session is None:
        raise AuthError("Login failed: no session returned.")

    state = SessionState.from_supabase(session)
    AppSession.current = state
    return state


def sign_out() -> None:
    sb = get_supabase()
    try:
        sb.auth.sign_out()
    finally:
        AppSession.clear()


def send_password_reset(email: str, redirect_to: Optional[str] = None) -> None:
    email = email.strip()
    if not email:
        raise AuthError("Email is required.")

    sb = get_supabase()
    try:
        if redirect_to:
            sb.auth.reset_password_for_email(email, {"redirect_to": redirect_to})
        else:
            sb.auth.reset_password_for_email(email)
    except Exception as e:
        raise AuthError(f"Failed to send reset email: {e}") from e