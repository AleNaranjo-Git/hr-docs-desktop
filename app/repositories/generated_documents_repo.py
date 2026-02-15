from __future__ import annotations

from typing import Any, Dict

from app.core.session import AppSession
from app.db.supabase_client import get_supabase


class GeneratedDocumentsRepo:
    @staticmethod
    def exists_for_incident(
        *,
        incident_id: str,
        template_key: str,
        template_version: int,
    ) -> bool:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("generated_documents")
            .select("id")
            .eq("firm_id", firm_id)
            .eq("incident_id", incident_id)
            .eq("template_key", template_key)
            .eq("template_version", template_version)
            .limit(1)
            .execute()
        )

        rows = resp.data or []
        return bool(rows)

    @staticmethod
    def create(
        *,
        company_client_id: str,
        incident_id: str,
        template_key: str,
        template_version: int,
        output_path: str,
    ) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        payload: Dict[str, Any] = {
            "firm_id": firm_id,
            "company_client_id": company_client_id,
            "incident_id": incident_id,
            "template_key": template_key,
            "template_version": template_version,
            "output_path": output_path,
            # optional:
            # "generated_by": AppSession.require().user_id,
        }

        sb.table("generated_documents").insert(payload).execute()