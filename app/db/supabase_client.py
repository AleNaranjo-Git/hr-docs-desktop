from __future__ import annotations

import os
from supabase import create_client, Client

from app.core.session import AppSession

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_ANON_KEY in environment")

    if _supabase is None:
        _supabase = create_client(url, key)


    if AppSession.current and AppSession.current.access_token:
        try:
            _supabase.postgrest.auth(AppSession.current.access_token)
        except Exception:
            try:
                _supabase.auth.set_session(
                    AppSession.current.access_token,
                    AppSession.current.refresh_token
                )
            except Exception:
                pass

    return _supabase