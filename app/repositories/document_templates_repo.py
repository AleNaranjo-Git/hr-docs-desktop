from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, TypedDict

from app.core.session import AppSession
from app.db.supabase_client import get_supabase
from app.core.events import events


class CompanyClientOption(TypedDict):
    id: str
    name: str


class IncidentTypeOption(TypedDict):
    id: int
    code: str
    name: str


class TemplateRow(TypedDict):
    id: str
    company_client_id: str
    company_client_name: str
    template_key: str
    version: int
    storage_path: str
    is_active: bool
    created_at: str


class DocumentTemplatesRepo:
    @staticmethod
    def _bucket_name() -> str:
        bucket = os.getenv("SUPABASE_TEMPLATES_BUCKET")
        if not bucket:
            raise RuntimeError("Missing SUPABASE_TEMPLATES_BUCKET env var.")
        return bucket

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
            if isinstance(r, dict):
                out.append(
                    {
                        "id": int(r.get("id", 0) or 0),
                        "code": str(r.get("code", "")),
                        "name": str(r.get("name", "")),
                    }
                )
        return out

    @staticmethod
    def list_templates(company_client_id: Optional[str] = None) -> List[TemplateRow]:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        query = (
            sb.table("document_templates")
            .select(
                "id, company_client_id, template_key, storage_path, version, is_active, created_at, company_clients(name)"
            )
            .eq("firm_id", firm_id)
            .order("created_at", desc=True)
        )

        if company_client_id:
            query = query.eq("company_client_id", company_client_id)

        resp = query.execute()
        data = resp.data or []

        out: List[TemplateRow] = []
        for r in data:
            if not isinstance(r, dict):
                continue

            embedded = r.get("company_clients")
            client_name = ""
            if isinstance(embedded, dict):
                client_name = str(embedded.get("name", ""))

            out.append(
                {
                    "id": str(r.get("id", "")),
                    "company_client_id": str(r.get("company_client_id", "")),
                    "company_client_name": client_name,
                    "template_key": str(r.get("template_key", "")),
                    "version": int(r.get("version", 0) or 0),
                    "storage_path": str(r.get("storage_path", "")),
                    "is_active": bool(r.get("is_active", False)),
                    "created_at": str(r.get("created_at", "")),
                }
            )

        return out

    @staticmethod
    def _get_next_version(company_client_id: str, template_key: str) -> int:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("document_templates")
            .select("version")
            .eq("firm_id", firm_id)
            .eq("company_client_id", company_client_id)
            .eq("template_key", template_key)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )

        data = resp.data or []
        if data and isinstance(data[0], dict):
            current = int(data[0].get("version", 0) or 0)
            return current + 1

        return 1

    @staticmethod
    def _storage_path(firm_id: str, company_client_id: str, template_key: str, version: int) -> str:
        return f"templates/{firm_id}/{company_client_id}/{template_key}/v{version}.docx"

    @staticmethod
    def _upload_docx_to_storage(storage_path: str, local_file_path: str) -> None:
        sb = get_supabase()
        bucket = DocumentTemplatesRepo._bucket_name()

        with open(local_file_path, "rb") as f:
            file_bytes = f.read()

        storage = sb.storage.from_(bucket)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        # Important: "upsert" must be string in file_options for supabase-py
        try:
            storage.upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return
        except TypeError:
            pass

        storage.upload(
            storage_path,
            file_bytes,
            {"content-type": content_type, "upsert": "true"},
        )

    @staticmethod
    def create_template(company_client_id: str, template_key: str, local_file_path: str) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        version = DocumentTemplatesRepo._get_next_version(company_client_id, template_key)
        storage_path = DocumentTemplatesRepo._storage_path(firm_id, company_client_id, template_key, version)

        # 1) Upload to storage
        DocumentTemplatesRepo._upload_docx_to_storage(storage_path, local_file_path)

        # 2) Deactivate previous active
        sb.table("document_templates").update(
            {"is_active": False}
        ).eq("firm_id", firm_id).eq("company_client_id", company_client_id).eq(
            "template_key", template_key
        ).eq("is_active", True).execute()

        # 3) Insert the new active template row
        payload: Dict[str, Any] = {
            "firm_id": firm_id,
            "company_client_id": company_client_id,
            "template_key": template_key,
            "storage_path": storage_path,
            "version": version,
            "is_active": True,
        }

        sb.table("document_templates").insert(payload).execute()
        
        events().templates_changed.emit()

    @staticmethod
    def deactivate(template_id: str) -> None:
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        sb.table("document_templates").update(
            {"is_active": False}
        ).eq("id", template_id).eq("firm_id", firm_id).execute()
        
        events().templates_changed.emit()