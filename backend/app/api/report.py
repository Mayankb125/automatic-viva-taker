"""
api/report.py — Report Routes
================================
Generates and serves the post-viva performance report.

After a session ends, the student (and examiner) can view a detailed report
showing: questions asked, student answers, score breakdowns per question,
integrity flags raised, and the overall final score.

All routes are prefixed with /api/report.
These are currently STUB implementations. Real report generation will be
added in Phase 5.

Endpoints:
    GET /api/report/{session_id}        — Return full JSON report for a session
    GET /api/report/{session_id}/pdf    — Download the report as a formatted PDF
"""

from fastapi import APIRouter

# All routes in this file get the /api/report prefix automatically
router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{session_id}")
def get_report(session_id: str):
    """
    Return the full performance report for a completed session.
    TODO (Phase 5): Query questions, scores, and integrity_flags tables
    for this session_id. Aggregate into a structured JSON report with:
    - Session metadata (student name, subject, topic, duration)
    - Per-question breakdown (question text, answer, all 5 scores, reason)
    - Integrity event timeline
    - Overall score and grade
    """
    return {"status": "ok"}


@router.get("/{session_id}/pdf")
def get_report_pdf(session_id: str):
    """
    Generate and return the report as a downloadable PDF file.
    TODO (Phase 5): Use ReportLab or WeasyPrint to render the same data
    as get_report() into a formatted PDF. Save to data/reports/ and return
    as a FileResponse so the browser downloads it.
    """
    return {"status": "ok"}
