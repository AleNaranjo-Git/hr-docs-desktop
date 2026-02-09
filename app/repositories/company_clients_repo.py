from __future__ import annotations
from typing import List, Dict

from app.db.supabase_client import get_supabase
from app.core.session import AppSession


class CompanyClientsRepo:
    @staticmethod
    def list_active() -> List[Dict]:
        sb = get_supabase()
        firm_id = AppSession.current.firm_id

        resp = (
            sb.table("company_clients")
            .select("id, name, legal_id, description, created_at")
            .eq("firm_id", firm_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )

        return resp.data or []

    @staticmethod
    def create(name: str, legal_id: str, description: str | None) -> None:
        sb = get_supabase()
        firm_id = AppSession.current.firm_id

        sb.table("company_clients").insert({
            "firm_id": firm_id,
            "name": name,
            "legal_id": legal_id,
            "description": description,
        }).execute()

    @staticmethod
    def deactivate(client_id: str) -> None:
        sb = get_supabase()

        sb.table("company_clients").update({
            "is_active": False
        }).eq("id", client_id).execute()