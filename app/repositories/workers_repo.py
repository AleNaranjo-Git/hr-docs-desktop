from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from app.core.session import AppSession
from app.db.supabase_client import get_supabase
from app.core.events import events

class WorkerRow(TypedDict):
    id: str
    full_name: str
    national_id: str
    company_client_id: str
    company_client_name: str
    created_at: str


class ClientOption(TypedDict):
    id: str
    name: str


class WorkersRepo:
    @staticmethod
    def list_company_clients_options() -> List[ClientOption]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("company_clients")
            .select("id, name")
            .eq("firm_id", firm_id)
            .eq("is_active", True)
            .order("name")
            .execute()
        )

        data = resp.data or []
        out: List[ClientOption] = []

        for r in data:
            if isinstance(r, dict):
                out.append({"id": str(r.get("id", "")), "name": str(r.get("name", ""))})

        return out

    @staticmethod
    def list_active(company_client_id: Optional[str] = None) -> List[WorkerRow]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        query = (
            sb.table("workers")
            .select("id, full_name, national_id, company_client_id, created_at, company_clients(name)")
            .eq("firm_id", firm_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
        )

        if company_client_id:
            query = query.eq("company_client_id", company_client_id)

        resp = query.execute()
        data = resp.data or []

        out: List[WorkerRow] = []
        for r in data:
            if not isinstance(r, dict):
                continue

            embedded = r.get("company_clients")
            client_name = ""
            if isinstance(embedded, dict):
                client_name = str(embedded.get("name", "") or "")

            out.append(
                {
                    "id": str(r.get("id", "") or ""),
                    "full_name": str(r.get("full_name", "") or ""),
                    "national_id": str(r.get("national_id", "") or ""),
                    "company_client_id": str(r.get("company_client_id", "") or ""),
                    "company_client_name": client_name,
                    "created_at": str(r.get("created_at", "") or ""),
                }
            )

        return out

    @staticmethod
    def create(company_client_id: str, full_name: str, national_id: str) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        payload: Dict[str, Any] = {
            "firm_id": firm_id,
            "company_client_id": company_client_id,
            "full_name": full_name,
            "national_id": national_id,
        }

        sb.table("workers").insert(payload).execute()
        
        events().workers_changed.emit()

    @staticmethod
    def deactivate(worker_id: str) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        sb.table("workers").update({"is_active": False}).eq("id", worker_id).eq("firm_id", firm_id).execute()
        
        events().workers_changed.emit()