"""api/report.py — Report Routes.

Phase 3.4 adds a basic JSON report endpoint so the frontend report page can
show overall score, per-topic scores, question counts, and switched topics.
Phase 7 adds a downloadable PDF export for the same data.
"""

import json
from datetime import datetime
from io import BytesIO
from textwrap import wrap
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.integrity_flag import IntegrityFlag
from app.models.score import Score
from app.models.session import Session
from app.services.pillar3_assessment.score_calculator import calculate_session_scores

# All routes in this file get the /api/report prefix automatically
router = APIRouter(prefix="/api/report", tags=["report"])


def _build_report_payload(session_id: str, db: DBSession) -> dict:
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    score_rows = db.query(Score).filter(Score.session_id == session_id).all()
    score_records = [
        {"topic": row.topic, "final_score": row.final_score}
        for row in score_rows
        if row.final_score is not None and row.topic is not None
    ]

    if score_records:
        aggregate = calculate_session_scores(score_records)
    else:
        aggregate = {
            "topic_scores": {},
            "topic_question_counts": {},
            "overall_score": 0.0,
            "total_questions": 0,
        }

    adaptive_state = {}
    if db_session.adaptive_state:
        try:
            adaptive_state = json.loads(db_session.adaptive_state)
        except json.JSONDecodeError:
            adaptive_state = {}

    switched_topics = adaptive_state.get("switched_topics", [])
    current_level = adaptive_state.get("current_level", 1)

    integrity_rows = db.query(IntegrityFlag).filter(IntegrityFlag.session_id == session_id).all()
    integrity_by_type = {}
    for row in integrity_rows:
        integrity_by_type[row.flag_type] = integrity_by_type.get(row.flag_type, 0) + 1

    integrity_recent = [
        {
            "flag_type": row.flag_type,
            "question_id": row.question_id,
            "timestamp": row.timestamp,
            "description": row.description,
        }
        for row in sorted(
            integrity_rows,
            key=lambda item: item.timestamp or datetime.min,
            reverse=True,
        )[:10]
    ]

    return {
        "session_id": session_id,
        "student_id": db_session.student_id,
        "subject": db_session.subject,
        "status": db_session.status,
        "start_time": db_session.start_time,
        "end_time": db_session.end_time,
        "overall_score": aggregate["overall_score"],
        "topic_scores": aggregate["topic_scores"],
        "topic_question_counts": aggregate["topic_question_counts"],
        "total_questions": aggregate["total_questions"],
        "switched_topics": switched_topics,
        "current_level": current_level,
        "integrity_summary": {
            "total_flags": len(integrity_rows),
            "by_type": integrity_by_type,
            "recent_flags": integrity_recent,
        },
    }


def _sanitize_pdf_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", "" if value is None else str(value))
    return text.encode("ascii", "ignore").decode("ascii")


def _build_report_lines(report: dict) -> list[str]:
    lines = [
        "Automatic Viva Taker Session Report",
        f"Session ID: {_sanitize_pdf_text(report.get('session_id'))}",
        f"Student ID: {_sanitize_pdf_text(report.get('student_id') or 'N/A')}",
        f"Subject: {_sanitize_pdf_text(report.get('subject') or 'N/A')}",
        f"Status: {_sanitize_pdf_text(report.get('status') or 'N/A')}",
        f"Overall Score: {_sanitize_pdf_text(report.get('overall_score'))}",
        f"Total Questions: {_sanitize_pdf_text(report.get('total_questions'))}",
        f"Current Level: {_sanitize_pdf_text(report.get('current_level'))}",
        f"Switched Topics: {_sanitize_pdf_text(', '.join(report.get('switched_topics') or []) or 'None')}",
        "",
        "Per Topic Scores",
    ]

    topic_scores = report.get("topic_scores") or {}
    topic_counts = report.get("topic_question_counts") or {}
    if topic_scores:
        for topic, score in topic_scores.items():
            lines.extend(
                wrap(
                    f"- {topic}: {score} ({topic_counts.get(topic, 0)} questions)",
                    width=88,
                )
                or [f"- {topic}: {score} ({topic_counts.get(topic, 0)} questions)"]
            )
    else:
        lines.append("No topic scores available.")

    lines.append("")
    lines.append("Integrity Summary")
    integrity_summary = report.get("integrity_summary") or {}
    lines.append(f"Total flags: {_sanitize_pdf_text(integrity_summary.get('total_flags', 0))}")

    by_type = integrity_summary.get("by_type") or {}
    if by_type:
        for flag_type, count in by_type.items():
            lines.append(f"- {flag_type}: {count}")
    else:
        lines.append("No integrity flags recorded.")

    recent_flags = integrity_summary.get("recent_flags") or []
    if recent_flags:
        lines.append("")
        lines.append("Recent Flags")
        for flag in recent_flags:
            description = flag.get("description") or ""
            timestamp = flag.get("timestamp") or ""
            label = f"- {flag.get('flag_type', 'unknown')}"
            if timestamp:
                label = f"{label} @ {_sanitize_pdf_text(timestamp)}"
            if description:
                label = f"{label} - {_sanitize_pdf_text(description)}"
            lines.extend(wrap(label, width=88) or [label])

    return lines


def _build_pdf_bytes(lines: list[str]) -> bytes:
    page_width = 612
    page_height = 792
    margin_left = 54
    margin_top = 54
    line_height = 14
    max_lines_per_page = int((page_height - (margin_top * 2)) / line_height)

    pages: list[list[str]] = []
    current_page: list[str] = []
    for line in lines:
        current_page.append(_sanitize_pdf_text(line))
        if len(current_page) >= max_lines_per_page:
            pages.append(current_page)
            current_page = []
    if current_page or not pages:
        pages.append(current_page)

    objects: list[bytes] = []

    def add_object(content: str | bytes) -> int:
        if isinstance(content, str):
            content_bytes = content.encode("latin-1", "replace")
        else:
            content_bytes = content
        objects.append(content_bytes)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_objects: list[int] = []
    for page_lines in pages:
        text_lines = ["BT", "/F1 11 Tf", f"1 0 0 1 {margin_left} {page_height - margin_top} Tm"]
        for index, line in enumerate(page_lines):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if index == 0:
                text_lines.append(f"({escaped}) Tj")
            else:
                text_lines.append(f"0 -{line_height} Td ({escaped}) Tj")
        text_lines.append("ET")
        stream = "\n".join(text_lines)
        content_object = add_object(
            f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream"
        )
        content_objects.append(content_object)

    page_objects: list[int] = []
    for content_object in content_objects:
        page_object = add_object(
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {page_width} {page_height}] /Resources << /Font << /F1 {font_obj} 0 R >> >> /Contents {content_object} 0 R >>"
        )
        page_objects.append(page_object)

    page_refs = " ".join(f"{page_object} 0 R" for page_object in page_objects)
    pages_obj = add_object(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(page_objects)} >>")
    for page_object in page_objects:
        page_content = objects[page_object - 1].decode("latin-1")
        objects[page_object - 1] = page_content.replace("/Parent 0 0 R", f"/Parent {pages_obj} 0 R").encode("latin-1")

    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n")

    offsets = [0]
    for index, content in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{index} 0 obj\n".encode("ascii"))
        pdf.write(content)
        pdf.write(b"\nendobj\n")

    xref_position = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_position}\n%%EOF"
        ).encode("ascii")
    )

    return pdf.getvalue()


@router.get("/{session_id}")
def get_report(session_id: str, db: DBSession = Depends(get_db)):
    """Return a basic report payload for one session (Phase 3.4)."""
    return _build_report_payload(session_id, db)


@router.get("/{session_id}/pdf")
def get_report_pdf(session_id: str, db: DBSession = Depends(get_db)):
    """
    Generate and return the report as a downloadable PDF file.

    The PDF is rendered with a small built-in generator so the feature works
    without introducing a new heavy dependency.
    """
    report = _build_report_payload(session_id, db)
    pdf_bytes = _build_pdf_bytes(_build_report_lines(report))
    headers = {
        "Content-Disposition": f'attachment; filename="viva-report-{_sanitize_pdf_text(session_id).replace("/", "_")}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
