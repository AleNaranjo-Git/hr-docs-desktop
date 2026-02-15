from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from app.core.session import AppSession
from app.db.supabase_client import get_supabase


class WorkerOption(TypedDict):
    id: str
    label: str


class IncidentTypeOption(TypedDict):
    id: int
    label: str


class IncidentRow(TypedDict):
    id: str
    code: str
    worker_name: str
    incident_type: str
    incident_date: str
    received_day: str
    manual_handling: bool
    observations: str
    created_at: str


class IncidentsRepo:
    @staticmethod
    def list_workers_options() -> List[WorkerOption]:
        """
        Returns active workers for the current firm.
        Label includes company client name to disambiguate duplicates.
        """
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("workers")
            .select("id, full_name, company_clients(name)")
            .eq("firm_id", firm_id)
            .eq("is_active", True)
            .order("full_name")
            .execute()
        )

        data = resp.data or []
        out: List[WorkerOption] = []

        for r in data:
            if not isinstance(r, dict):
                continue

            full_name = str(r.get("full_name", "") or "")
            embedded = r.get("company_clients")
            client_name = ""
            if isinstance(embedded, dict):
                client_name = str(embedded.get("name", "") or "")

            label = full_name
            if client_name:
                label = f"{full_name} — {client_name}"

            out.append({"id": str(r.get("id", "") or ""), "label": label})

        return out

    @staticmethod
    def list_incident_types_options() -> List[IncidentTypeOption]:
        sb = get_supabase()

        resp = (
            sb.table("incident_types")
            .select("id, code, name")
            .order("id")
            .execute()
        )

        data = resp.data or []
        out: List[IncidentTypeOption] = []

        for r in data:
            if not isinstance(r, dict):
                continue

            type_id = r.get("id")
            if not isinstance(type_id, int):
                continue

            code = str(r.get("code", "") or "")
            name = str(r.get("name", "") or "")
            label = f"{code} — {name}" if name else code

            out.append({"id": type_id, "label": label})

        return out

    @staticmethod
    def list_recent(worker_id: Optional[str] = None) -> List[IncidentRow]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        query = (
            sb.table("incidents")
            .select(
                "id, code, incident_date, received_day, observations, manual_handling, created_at, "
                "workers(full_name), incident_types(code, name)"
            )
            .eq("firm_id", firm_id)
            .order("created_at", desc=True)
        )

        if worker_id:
            query = query.eq("worker_id", worker_id)

        resp = query.execute()
        data = resp.data or []

        out: List[IncidentRow] = []
        for r in data:
            if not isinstance(r, dict):
                continue

            worker_name = ""
            w = r.get("workers")
            if isinstance(w, dict):
                worker_name = str(w.get("full_name", "") or "")

            incident_type = ""
            it = r.get("incident_types")
            if isinstance(it, dict):
                it_code = str(it.get("code", "") or "")
                it_name = str(it.get("name", "") or "")
                incident_type = f"{it_code} — {it_name}" if it_name else it_code

            out.append(
                {
                    "id": str(r.get("id", "") or ""),
                    "code": str(r.get("code", "") or ""),
                    "worker_name": worker_name,
                    "incident_type": incident_type,
                    "incident_date": str(r.get("incident_date", "") or ""),
                    "received_day": str(r.get("received_day", "") or ""),
                    "manual_handling": bool(r.get("manual_handling", False)),
                    "observations": str(r.get("observations", "") or ""),
                    "created_at": str(r.get("created_at", "") or ""),
                }
            )

        return out

    @staticmethod
    def create(
        *,
        worker_id: str,
        incident_type_id: int,
        incident_date: str,   # "YYYY-MM-DD"
        received_day: str,    # "YYYY-MM-DD"
        observations: Optional[str],
        manual_handling: bool,
    ) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        payload: Dict[str, Any] = {
            "firm_id": firm_id,
            "worker_id": worker_id,
            "incident_type_id": incident_type_id,
            "incident_date": incident_date,
            "received_day": received_day,
            "observations": observations,
            "manual_handling": manual_handling,
        }

        sb.table("incidents").insert(payload).execute()

    @staticmethod
    def delete(incident_id: str) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        sb.table("incidents").delete().eq("id", incident_id).eq("firm_id", firm_id).execute()