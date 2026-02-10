from __future__ import annotations

from typing import TypedDict, cast, Any

from app.db.supabase_client import get_supabase
from app.core.session import AppSession


class CompanyClientRow(TypedDict):
    id: str
    name: str
    legal_id: str
    description: str | None
    created_at: str


class CompanyClientsRepo:
    @staticmethod
    def list_active() -> list[CompanyClientRow]:
        sb = get_supabase()
        firm_id: str = AppSession.require().firm_id

        resp = (
            sb.table("company_clients")
            .select("id, name, legal_id, description, created_at")
            .eq("firm_id", firm_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )

        return cast(list[CompanyClientRow], resp.data or [])

    @staticmethod
    def create(name: str, legal_id: str, description: str | None) -> None:
        sb = get_supabase()
        firm_id: str = AppSession.require().firm_id

        payload: dict[str, Any] = {
            "firm_id": firm_id,
            "name": name,
            "legal_id": legal_id,
            "description": description,
        }

        sb.table("company_clients").insert(payload).execute()

    @staticmethod
    def deactivate(client_id: str) -> None:
        sb = get_supabase()
        firm_id: str = AppSession.require().firm_id

        sb.table("company_clients").update(
            {"is_active": False}
        ).eq("id", client_id).eq("firm_id", firm_id).execute()