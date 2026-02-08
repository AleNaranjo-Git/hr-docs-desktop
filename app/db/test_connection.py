from __future__ import annotations

import os
from dotenv import load_dotenv
from supabase import create_client


def main() -> None:
    # Loads .env from the project root automatically
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_ANON_KEY. "
            "Set them in a .env file or as environment variables."
        )

    supabase = create_client(url, key)

    # Public-readable test table (incident_types)
    res = supabase.table("incident_types").select("id, code, name").order("id").execute()

    print("✅ Connected to Supabase")
    print("incident_types rows:")
    for row in (res.data or []):
        print(f" - {row['id']}: {row['code']} -> {row['name']}")


if __name__ == "__main__":
    main()