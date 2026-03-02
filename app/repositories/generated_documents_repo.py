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
        doc_prefix: str,
        doc_year: int,
        doc_seq: int,
        doc_code: str,
    ) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        payload = {
            "firm_id": firm_id,
            "company_client_id": company_client_id,
            "incident_id": incident_id,
            "template_key": template_key,
            "template_version": template_version,
            "output_path": output_path,
            "doc_prefix": doc_prefix,
            "doc_year": doc_year,
            "doc_seq": doc_seq,
            "doc_code": doc_code,
        }

        resp = sb.table("generated_documents").insert(payload).execute()

        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(f"Failed to record generated document: {resp.error}")
          
    @staticmethod
    def next_doc_seq(*, company_client_id: str, doc_prefix: str, doc_year: int) -> int:
        """
        Returns next consecutive number for:
        (firm_id, company_client_id, doc_prefix, doc_year)
        """
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("generated_documents")
            .select("doc_seq")
            .eq("firm_id", firm_id)
            .eq("company_client_id", company_client_id)
            .eq("doc_prefix", doc_prefix)
            .eq("doc_year", doc_year)
            .order("doc_seq", desc=True)
            .limit(1)
            .execute()
        )

        data = resp.data or []
        if data and isinstance(data[0], dict):
            last_seq = int(data[0].get("doc_seq") or 0)
            return last_seq + 1

        return 1