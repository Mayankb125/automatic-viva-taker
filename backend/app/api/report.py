"""api/report.py — Report Routes.

Phase 3.4 adds a basic JSON report endpoint so the frontend report page can
show overall score, per-topic scores, question counts, and switched topics.
PDF generation remains a Phase 5 task.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.score import Score
from app.models.session import Session
from app.services.pillar3_assessment.score_calculator import calculate_session_scores

# All routes in this file get the /api/report prefix automatically
router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{session_id}")
def get_report(session_id: str, db: DBSession = Depends(get_db)):
    """Return a basic report payload for one session (Phase 3.4)."""
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
    }


@router.get("/{session_id}/pdf")
def get_report_pdf(session_id: str):
    """
    Generate and return the report as a downloadable PDF file.
    TODO (Phase 5): Use ReportLab or WeasyPrint to render the same data
    as get_report() into a formatted PDF. Save to data/reports/ and return
    as a FileResponse so the browser downloads it.
    """
    return {"status": "ok"}
