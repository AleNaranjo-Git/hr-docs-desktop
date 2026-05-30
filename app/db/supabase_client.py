from __future__ import annotations

import os
import threading
from typing import Callable, TypeVar
from supabase import create_client, Client

from app.core.session import AppSession, SessionState

_supabase: Client | None = None
T = TypeVar("T")
_refresh_lock = threading.Lock()


def _apply_session_to_client(sb: Client, state: SessionState) -> None:
    # Keep PostgREST scoped to the current access token.
    # Avoid calling auth.set_session() on every request because refresh tokens
    # are rotated and can become "already used" if replayed.
    try:
        sb.postgrest.auth(state.access_token)
    except Exception:
        pass


def _extract_error_text(exc: Exception) -> str:
    chunks: list[str] = []
    try:
        chunks.append(str(exc))
    except Exception:
        pass

    args = getattr(exc, "args", ()) or ()
    for a in args:
        try:
            chunks.append(str(a))
        except Exception:
            continue

    return " | ".join([c for c in chunks if c])


def is_jwt_expired_error(exc: Exception) -> bool:
    msg = _extract_error_text(exc).upper()
    return "JWT EXPIRED" in msg or "PGRST303" in msg


def refresh_session_tokens() -> bool:
    with _refresh_lock:
        state = AppSession.current
        if state is None or not state.refresh_token:
            return False

        sb = get_supabase()

        try:
            refreshed = sb.auth.refresh_session(state.refresh_token)
        except TypeError:
            try:
                refreshed = sb.auth.refresh_session()
            except Exception:
                return False
        except Exception:
            return False

        session_obj = getattr(refreshed, "session", None) or refreshed

        if not getattr(session_obj, "access_token", ""):
            return False

        new_state = SessionState.from_supabase(session_obj)
        new_state.firm_id = state.firm_id
        AppSession.current = new_state

        _apply_session_to_client(sb, new_state)
        return True


def execute_with_auth_retry(action: Callable[[], T]) -> T:
    try:
        return action()
    except Exception as e:
        if not is_jwt_expired_error(e):
            raise
        if not refresh_session_tokens():
            raise RuntimeError("Session expired. Please log in again.") from e
        return action()


def get_supabase() -> Client:
    global _supabase

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_ANON_KEY in environment")

    if _supabase is None:
        _supabase = create_client(url, key)

    if AppSession.current and AppSession.current.access_token:
        _apply_session_to_client(_supabase, AppSession.current)

    return _supabase