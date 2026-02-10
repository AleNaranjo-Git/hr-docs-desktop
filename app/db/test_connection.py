from __future__ import annotations

import os
from typing import Any, Mapping, Sequence, cast

from dotenv import load_dotenv
from supabase import create_client


def main() -> None:
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_ANON_KEY. "
            "Set them in a .env file or as environment variables."
        )

    supabase = create_client(url, key)

    res = supabase.table("incident_types").select("id, code, name").order("id").execute()

    print("✅ Connected to Supabase")
    print("incident_types rows:")

    rows = cast(Sequence[Mapping[str, Any]], res.data or [])

    for row in rows:
        _id = row.get("id")
        code = row.get("code")
        name = row.get("name")
        print(f" - {_id}: {code} -> {name}")


if __name__ == "__main__":
    main()