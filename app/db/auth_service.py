from __future__ import annotations

from typing import Optional

from app.core.session import AppSession, SessionState
from app.db.supabase_client import get_supabase


class AuthError(Exception):
    pass


def _fetch_firm_id_for_user(user_id: str) -> str:
    sb = get_supabase()
    try:
        resp = (
            sb.table("profiles")
            .select("firm_id")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise AuthError(f"Failed to fetch firm profile: {e}") from e

    data = getattr(resp, "data", None)
    if not data:
        raise AuthError(
            "Login succeeded but no active profile was found for this user. "
            "Make sure a row exists in profiles with is_active=true."
        )

    firm_id = data[0].get("firm_id")
    if not firm_id:
        raise AuthError("Profile found but firm_id is missing.")
    return firm_id


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

    
    user_id = getattr(session.user, "id", "") or ""
    firm_id = _fetch_firm_id_for_user(user_id)

    
    state = SessionState.from_supabase(session, firm_id)

    AppSession.current = state
    
    print("SESSION:", AppSession.current)
    
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