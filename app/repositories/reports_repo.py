from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from app.core.session import AppSession
from app.db.supabase_client import get_supabase


@dataclass(frozen=True)
class ReportIncidentRow:
    incident_id: str
    received_day: date
    incident_type_code: str
    incident_type_name: str
    worker_full_name: str
    worker_national_id: str
    company_client_id: str
    company_client_name: str


def _parse_date_yyyy_mm_dd(value: str) -> date:
    y, m, d = value.split("-")
    return date(int(y), int(m), int(d))


class ReportsRepo:
    @staticmethod
    def list_company_clients_options() -> List[dict]:
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

        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(resp.error)

        data = resp.data or []
        out: List[dict] = []
        for r in data:
            if isinstance(r, dict):
                out.append({"id": str(r.get("id", "")), "name": str(r.get("name", ""))})
        return out

    @staticmethod
    def list_incidents_for_reports(
        *,
        date_from: date,
        date_to: date,
        company_client_id: Optional[str],
    ) -> List[ReportIncidentRow]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("incidents")
            .select(
                "id, received_day, "
                "type:incident_types(code, name), "
                "worker:workers(full_name, national_id, company_client_id, company_client:company_clients(name))"
            )
            .eq("firm_id", firm_id)
            .gte("received_day", str(date_from))
            .lte("received_day", str(date_to))
            .order("received_day", desc=False)
            .execute()
        )

        # Optional hardening
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(resp.error)

        data = resp.data or []
        out: List[ReportIncidentRow] = []

        for r in data:
            if not isinstance(r, dict):
                continue

            received_day_str = r.get("received_day")
            if not isinstance(received_day_str, str) or not received_day_str:
                continue

            itype = r.get("type")
            worker = r.get("worker")
            if not isinstance(itype, dict) or not isinstance(worker, dict):
                continue

            cc = worker.get("company_client")
            if not isinstance(cc, dict):
                continue

            cc_id = str(worker.get("company_client_id", ""))

            if company_client_id and cc_id != company_client_id:
                continue

            out.append(
                ReportIncidentRow(
                    incident_id=str(r.get("id", "")),
                    received_day=_parse_date_yyyy_mm_dd(received_day_str),
                    incident_type_code=str(itype.get("code", "")),
                    incident_type_name=str(itype.get("name", "")),
                    worker_full_name=str(worker.get("full_name", "")),
                    worker_national_id=str(worker.get("national_id", "")),
                    company_client_id=cc_id,
                    company_client_name=str(cc.get("name", "")),
                )
            )

        return out