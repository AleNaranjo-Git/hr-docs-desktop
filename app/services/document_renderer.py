from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Dict

from docx import Document


SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def format_spanish_long(d: date) -> str:
    # Example: 20 de febrero de 2026
    return f"{d.day} de {SPANISH_MONTHS[d.month]} de {d.year}"


_filename_bad = re.compile(r'[<>:"/\\|?*\x00-\x1F]+')


def safe_filename(name: str) -> str:
    s = name.strip()
    s = _filename_bad.sub("_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:180] if len(s) > 180 else s


def _replace_in_paragraph(paragraph, mapping: Dict[str, str]) -> None:
    """
    Reliable placeholder replacement even when {{placeholders}} are split across runs.
    Tradeoff: replaced segments may lose some run-level styling.
    """
    text = paragraph.text
    new_text = text
    for k, v in mapping.items():
        new_text = new_text.replace(k, v)

    if new_text == text:
        return

    # Clear runs
    for run in paragraph.runs:
        run.text = ""

    # Put everything in first run
    if paragraph.runs:
        paragraph.runs[0].text = new_text
    else:
        paragraph.add_run(new_text)


def replace_placeholders(doc: Document, mapping: Dict[str, str]) -> None:
    # Paragraphs
    for p in doc.paragraphs:
        _replace_in_paragraph(p, mapping)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p, mapping)


@dataclass(frozen=True)
class DocContext:
    today: date
    code: str
    worker_name_upper: str
    incident_date: date
    observations: str


def render_docx(template_bytes: bytes, ctx: DocContext) -> bytes:
    doc = Document(BytesIO(template_bytes))

    mapping = {
        "{{today}}": format_spanish_long(ctx.today),
        "{{code}}": ctx.code,
        "{{name}}": ctx.worker_name_upper,
        "{{incident_date}}": format_spanish_long(ctx.incident_date),
        "{{observations}}": ctx.observations,
    }

    replace_placeholders(doc, mapping)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_output_filename(
    *,
    company_client_name: str,
    code: str,
    worker_full_name: str,
    worker_national_id: str,
    incident_type_code: str,
) -> str:
    base = f"{company_client_name}__{incident_type_code}__{code}__{worker_full_name}__{worker_national_id}.docx"
    return safe_filename(base)


def save_bytes(folder: str, filename: str, content: bytes) -> str:
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(content)
    return str(out_path)