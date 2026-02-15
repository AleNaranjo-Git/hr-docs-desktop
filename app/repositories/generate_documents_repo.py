from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, List, Optional, TypedDict

from app.core.session import AppSession
from app.db.supabase_client import get_supabase


TEMPLATES_BUCKET = os.getenv("SUPABASE_TEMPLATES_BUCKET", "templates")


class CompanyClientOption(TypedDict):
    id: str
    name: str


class ActiveTemplate(TypedDict):
    storage_path: str
    version: int


@dataclass(frozen=True)
class IncidentForDoc:
    id: str
    code: str
    incident_date: date
    received_day: Optional[date]
    observations: str
    incident_type_code: str
    incident_type_name: str
    worker_full_name: str
    worker_national_id: str
    company_client_id: str
    company_client_name: str


def _parse_iso_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    return None


class GenerateDocumentsRepo:
    @staticmethod
    def list_company_clients_options() -> List[CompanyClientOption]:
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
        out: List[CompanyClientOption] = []

        for r in data:
            if isinstance(r, dict):
                out.append({"id": str(r.get("id", "")), "name": str(r.get("name", ""))})

        return out

    @staticmethod
    def list_incidents_for_generation(
        *,
        date_from: date,
        date_to: date,
        company_client_id: Optional[str],
    ) -> List[IncidentForDoc]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("incidents")
            .select(
                "id, code, incident_date, received_day, observations, "
                "worker:workers(full_name, national_id, company_client_id, company_client:company_clients(name)), "
                "type:incident_types(code, name)"
            )
            .eq("firm_id", firm_id)
            .gte("incident_date", str(date_from))
            .lte("incident_date", str(date_to))
            .order("incident_date", desc=False)
            .execute()
        )

        data = resp.data or []
        out: List[IncidentForDoc] = []

        for r in data:
            if not isinstance(r, dict):
                continue

            worker = r.get("worker")
            itype = r.get("type")
            if not isinstance(worker, dict) or not isinstance(itype, dict):
                continue

            cc = worker.get("company_client")
            if not isinstance(cc, dict):
                continue

            cc_id = str(worker.get("company_client_id", ""))
            if company_client_id and cc_id != company_client_id:
                continue

            inc_date = _parse_iso_date(r.get("incident_date"))
            if not inc_date:
                continue

            rec_day = _parse_iso_date(r.get("received_day"))

            obs = r.get("observations")
            obs_text = "" if obs is None else str(obs)

            out.append(
                IncidentForDoc(
                    id=str(r.get("id", "")),
                    code=str(r.get("code", "")) if r.get("code") else "",
                    incident_date=inc_date,
                    received_day=rec_day,
                    observations=obs_text,
                    incident_type_code=str(itype.get("code", "")),
                    incident_type_name=str(itype.get("name", "")),
                    worker_full_name=str(worker.get("full_name", "")),
                    worker_national_id=str(worker.get("national_id", "")),
                    company_client_id=cc_id,
                    company_client_name=str(cc.get("name", "")),
                )
            )

        return out

    @staticmethod
    def get_active_template(
        *,
        company_client_id: str,
        template_key: str,
    ) -> Optional[ActiveTemplate]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("document_templates")
            .select("storage_path, version")
            .eq("firm_id", firm_id)
            .eq("company_client_id", company_client_id)
            .eq("template_key", template_key)
            .eq("is_active", True)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )

        rows = resp.data or []
        if not rows or not isinstance(rows[0], dict):
            return None

        storage_path = str(rows[0].get("storage_path", "") or "")
        version = int(rows[0].get("version", 0) or 0)

        if not storage_path or version <= 0:
            return None

        return {"storage_path": storage_path, "version": version}

    @staticmethod
    def download_template_bytes(storage_path: str) -> bytes:
        sb = get_supabase()
        return sb.storage.from_(TEMPLATES_BUCKET).download(storage_path)