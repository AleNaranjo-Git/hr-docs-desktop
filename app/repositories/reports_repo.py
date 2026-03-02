from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from app.core.session import AppSession
from app.db.supabase_client import get_supabase


INCIDENT_TYPE_TO_FALTA_ES = {
    "ABSENCE": "AUSENCIA INJUSTIFICADA",
    "LATE_ARRIVAL": "LLEGADA TARDÍA",
    "JOB_ABANDONMENT": "ABANDONO DE TRABAJO",
}


@dataclass(frozen=True)
class ReportRow:
    incident_id: str
    consecutivo: str  # incidents.code
    fecha_consecutivo: date  # incidents.received_day
    patrono: str  # company_clients.name
    correo: str  # workers.email
    colaborador: str  # workers.full_name
    cedula: str  # workers.national_id
    fecha_incidente: date  # incidents.incident_date
    falta: str  # Spanish label
    estado: str  # from incident_report_meta.status (default PENDIENTE)
    observaciones: str  # from incident_report_meta.report_observations
    revision: str  # computed


def _parse_date_yyyy_mm_dd(value: str) -> date:
    y, m, d = value.split("-")
    return date(int(y), int(m), int(d))


def _falta_label_from_type_code(type_code: str, type_name: str) -> str:
    """
    Prefer fixed mapping by code.
    Fallback to type_name (already Spanish sometimes).
    """
    code = (type_code or "").strip().upper()
    mapped = INCIDENT_TYPE_TO_FALTA_ES.get(code)
    if mapped:
        return mapped

    # fallback: if the DB name is already Spanish, keep it (upper for consistency)
    if (type_name or "").strip():
        return (type_name or "").strip().upper()

    return code


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
    def _fetch_meta_map(incident_ids: List[str]) -> Dict[str, dict]:
        """
        Returns: {incident_id: {"status": str, "report_observations": str}}
        If a row doesn't exist, caller will default to PENDIENTE / "".
        """
        if not incident_ids:
            return {}

        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("incident_report_meta")
            .select("incident_id, status, report_observations")
            .eq("firm_id", firm_id)
            .in_("incident_id", incident_ids)
            .execute()
        )

        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(resp.error)

        data = resp.data or []
        out: Dict[str, dict] = {}
        for r in data:
            if not isinstance(r, dict):
                continue
            iid = str(r.get("incident_id", "") or "").strip()
            if not iid:
                continue
            out[iid] = {
                "status": str(r.get("status", "") or "").strip(),
                "report_observations": "" if r.get("report_observations") is None else str(r.get("report_observations")),
            }
        return out

    @staticmethod
    def upsert_meta(
        *,
        incident_id: str,
        status: Optional[str] = None,
        report_observations: Optional[str] = None,
    ) -> None:
        """
        Robust upsert:
        - First checks if the meta row exists for (firm_id, incident_id)
        - If exists -> UPDATE
        - Else -> INSERT
        This avoids 23505 duplicate issues if upsert/on_conflict behavior differs by client lib version.
        """
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        if not incident_id or not incident_id.strip():
            raise ValueError("incident_id is required")

        # Build patch (only send changed fields)
        patch: Dict[str, object] = {}
        if status is not None:
            patch["status"] = status
        if report_observations is not None:
            patch["report_observations"] = report_observations

        # Nothing to update
        if not patch:
            return

        # 1) Check existence
        check = (
            sb.table("incident_report_meta")
            .select("incident_id")
            .eq("firm_id", firm_id)
            .eq("incident_id", incident_id)
            .limit(1)
            .execute()
        )

        if hasattr(check, "error") and check.error:
            raise RuntimeError(check.error)

        exists = bool(check.data) and isinstance(check.data, list) and len(check.data) > 0

        if exists:
            # 2a) UPDATE
            resp = (
                sb.table("incident_report_meta")
                .update(patch)
                .eq("firm_id", firm_id)
                .eq("incident_id", incident_id)
                .execute()
            )
            if hasattr(resp, "error") and resp.error:
                raise RuntimeError(resp.error)
            return

        # 2b) INSERT
        payload = {"firm_id": firm_id, "incident_id": incident_id, **patch}
        resp = sb.table("incident_report_meta").insert(payload).execute()
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(resp.error)

    @staticmethod
    def list_report_rows(
        *,
        date_from: date,
        date_to: date,
        company_client_id: Optional[str],
    ) -> List[ReportRow]:
        """
        Pull incidents by firm + received_day range,
        merge with incident_report_meta,
        compute revision rules for ABSENCE within same month.
        """
        sb = get_supabase()
        firm_id = AppSession.require().firm_id

        resp = (
            sb.table("incidents")
            .select(
                "id, code, received_day, incident_date, "
                "type:incident_types(code, name), "
                "worker:workers(full_name, national_id, email, company_client_id, company_client:company_clients(name))"
            )
            .eq("firm_id", firm_id)
            .gte("received_day", str(date_from))
            .lte("received_day", str(date_to))
            .order("received_day", desc=False)
            .execute()
        )

        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(resp.error)

        data = resp.data or []

        # first pass: parse rows (without meta/revision)
        temp: List[dict] = []
        incident_ids: List[str] = []

        for r in data:
            if not isinstance(r, dict):
                continue

            iid = str(r.get("id", "") or "").strip()
            if not iid:
                continue

            received_day_str = r.get("received_day")
            incident_date_str = r.get("incident_date")
            if not isinstance(received_day_str, str) or not received_day_str:
                continue
            if not isinstance(incident_date_str, str) or not incident_date_str:
                continue

            itype = r.get("type")
            worker = r.get("worker")
            if not isinstance(itype, dict) or not isinstance(worker, dict):
                continue

            cc = worker.get("company_client")
            if not isinstance(cc, dict):
                continue

            cc_id = str(worker.get("company_client_id", "") or "").strip()
            if company_client_id and cc_id != company_client_id:
                continue

            patrono = str(cc.get("name", "") or "").strip()
            type_code = str(itype.get("code", "") or "").strip()
            type_name = str(itype.get("name", "") or "").strip()

            temp.append(
                {
                    "incident_id": iid,
                    "consecutivo": str(r.get("code", "") or "").strip(),
                    "fecha_consecutivo": _parse_date_yyyy_mm_dd(received_day_str),
                    "fecha_incidente": _parse_date_yyyy_mm_dd(incident_date_str),
                    "incident_type_code": type_code,
                    "incident_type_name": type_name,
                    "patrono": patrono,
                    "correo": str(worker.get("email", "") or "").strip(),
                    "colaborador": str(worker.get("full_name", "") or "").strip(),
                    "cedula": str(worker.get("national_id", "") or "").strip(),
                    "company_client_id": cc_id,
                }
            )
            incident_ids.append(iid)

        meta_map = ReportsRepo._fetch_meta_map(incident_ids)

        # Build helper index to compute ABSENCE review per worker per month
        # key: (company_client_id, worker_national_id, yyyy, mm) -> sorted incident_date list for ABSENCE
        absence_by_worker_month: Dict[tuple, List[date]] = {}
        for t in temp:
            if (t["incident_type_code"] or "").strip().upper() != "ABSENCE":
                continue
            d: date = t["fecha_incidente"]
            key = (t["company_client_id"], t["cedula"], d.year, d.month)
            absence_by_worker_month.setdefault(key, []).append(d)

        for k in list(absence_by_worker_month.keys()):
            absence_by_worker_month[k] = sorted(absence_by_worker_month[k])

        def compute_revision_for_row(t: dict) -> str:
            if (t["incident_type_code"] or "").strip().upper() != "ABSENCE":
                return ""

            d: date = t["fecha_incidente"]
            key = (t["company_client_id"], t["cedula"], d.year, d.month)
            days = absence_by_worker_month.get(key, [])
            n = len(days)

            if n <= 1:
                return "Tiene 1 ausencia injustificada"

            # consecutive check: any pair with diff == 1 day
            has_consecutive = False
            for i in range(1, len(days)):
                if (days[i] - days[i - 1]).days == 1:
                    has_consecutive = True
                    break

            if has_consecutive:
                return "Se puede despedir: 2 ausencias injustificadas seguidas"

            if n >= 3:
                return "Se puede despedir: 3 ausencias injustificadas alternas (mismo mes)"

            # n == 2 but not consecutive
            return "Tiene 2 ausencias injustificadas no seguidas"

        out: List[ReportRow] = []
        for t in temp:
            iid = t["incident_id"]
            meta = meta_map.get(iid, {})
            estado = (meta.get("status") or "").strip() or "PENDIENTE"
            obs = meta.get("report_observations")
            if obs is None:
                obs = ""

            falta = _falta_label_from_type_code(t["incident_type_code"], t["incident_type_name"])
            revision = compute_revision_for_row(t)

            out.append(
                ReportRow(
                    incident_id=iid,
                    consecutivo=t["consecutivo"],
                    fecha_consecutivo=t["fecha_consecutivo"],
                    patrono=t["patrono"],
                    correo=t["correo"],
                    colaborador=t["colaborador"],
                    cedula=t["cedula"],
                    fecha_incidente=t["fecha_incidente"],
                    falta=falta,
                    estado=estado,
                    observaciones=str(obs),
                    revision=revision,
                )
            )

        return out