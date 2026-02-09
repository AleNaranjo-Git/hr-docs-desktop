from __future__ import annotations

import os
from dotenv import load_dotenv
from supabase import create_client
from supabase.client import Client


_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        load_dotenv()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "Missing SUPABASE_URL or SUPABASE_ANON_KEY. "
                "Set them in a .env file (root) or system env vars."
            )
        _supabase = create_client(url, key)
    return _supabase