"""
api/session.py — Viva Session Routes
======================================
Manages the lifecycle of a viva session: starting, ending, and topic switching.

All routes are prefixed with /api/session.

Endpoints:
    POST /api/session/start           — Start a new session for the logged-in student
    POST /api/session/end             — End the active session, calculate overall score
    POST /api/session/switch-topic    — Change the current topic mid-session
    GET  /api/session/{session_id}    — Fetch details and status of a specific session
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.session import Session
from app.models.score import Score
from app.services.pillar2_nlp.adaptive_logic import make_session_state
from app.services.pillar3_assessment.score_calculator import calculate_session_scores

# All routes in this file get the /api/session prefix automatically
router = APIRouter(prefix="/api/session", tags=["session"])


# ── Request schemas ───────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    student_id: str
    subject: str
    topic_list: list[str] = Field(min_length=1)


class EndSessionRequest(BaseModel):
    session_id: str


class SwitchTopicRequest(BaseModel):
    session_id: str
    new_topic: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start")
def start_session(body: StartSessionRequest, db: DBSession = Depends(get_db)):
    """
    Start a new viva session.
    Creates a Session row with status='active' and initialises the adaptive state.
    Returns the session_id so the frontend knows which session to use for all
    subsequent question/answer requests.
    """
    session_id = str(uuid.uuid4())

    # Build the full adaptive state dict — drives all difficulty decisions
    adaptive_state = make_session_state(
        session_id=session_id,
        student_id=body.student_id,
        subject=body.subject,
        topic_list=body.topic_list,
    )

    # Persist the session row to SQLite
    db_session = Session(
        id=session_id,
        student_id=body.student_id,
        subject=body.subject,
        topic=body.topic_list[0],               # start on the first topic
        topic_list=json.dumps(body.topic_list),
        status="active",
        adaptive_state=json.dumps(adaptive_state),
    )
    db.add(db_session)
    db.commit()

    return {
        "session_id": session_id,
        "current_topic": body.topic_list[0],
        "current_level": 1,
    }


@router.post("/end")
def end_session(body: EndSessionRequest, db: DBSession = Depends(get_db)):
    """
    End the active viva session.
    Marks the session complete, calculates overall score, and returns final stats.
    """
    db_session = db.query(Session).filter(Session.id == body.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Collect all scored answers for this session
    score_rows = db.query(Score).filter(Score.session_id == body.session_id).all()
    score_records = [
        {"topic": r.topic, "final_score": r.final_score}
        for r in score_rows
        if r.final_score is not None and r.topic is not None
    ]

    # Aggregate per-topic and overall scores
    if score_records:
        result = calculate_session_scores(score_records)
    else:
        result = {
            "topic_scores": {},
            "topic_question_counts": {},
            "overall_score": 0.0,
            "total_questions": 0,
        }

    # Mark the session as completed and store the final score
    db_session.end_time = datetime.utcnow()
    db_session.status = "completed"
    db_session.overall_score = result["overall_score"]
    db.commit()

    return {
        "session_id": body.session_id,
        "overall_score": result["overall_score"],
        "topic_scores": result["topic_scores"],
        "topic_question_counts": result["topic_question_counts"],
        "total_questions": result["total_questions"],
    }


@router.post("/switch-topic")
def switch_topic(body: SwitchTopicRequest, db: DBSession = Depends(get_db)):
    """
    Switch to a different topic mid-session.
    Resets difficulty level to 1 on the new topic and clears checkpoint state.
    Called by the frontend when the adaptive engine returns show_topic_modal=True.
    """
    db_session = db.query(Session).filter(Session.id == body.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Prevent switching topics on a session that is already finished
    if db_session.status != "active":
        raise HTTPException(status_code=409, detail="Session is not active")

    # Reject topics that were not in the original topic list for this session
    allowed_topics = json.loads(db_session.topic_list) if db_session.topic_list else []
    if body.new_topic not in allowed_topics:
        raise HTTPException(status_code=400, detail="Invalid topic")

    adaptive_state = json.loads(db_session.adaptive_state)

    # Record the topic being abandoned so it is not selected again
    old_topic = adaptive_state["current_topic"]
    if old_topic not in adaptive_state["switched_topics"]:
        adaptive_state["switched_topics"].append(old_topic)

    # Switch to the new topic and reset per-topic counters
    adaptive_state["current_topic"] = body.new_topic
    adaptive_state["current_level"] = 1
    adaptive_state["questions_on_current_topic"] = 0
    adaptive_state["checkpoint_asked"] = False
    if body.new_topic not in adaptive_state["topic_scores"]:
        adaptive_state["topic_scores"][body.new_topic] = []

    # Persist updated state
    db_session.topic = body.new_topic
    db_session.adaptive_state = json.dumps(adaptive_state)
    db.commit()

    return {
        "session_id": body.session_id,
        "new_topic": body.new_topic,
        "current_level": 1,
    }


@router.get("/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    """
    Get the current state of a session by its ID.
    Returns session details including status, current topic, and progress counters.
    """
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    adaptive_state = (
        json.loads(db_session.adaptive_state) if db_session.adaptive_state else {}
    )

    return {
        "session_id": session_id,
        "student_id": db_session.student_id,
        "subject": db_session.subject,
        "current_topic": db_session.topic,
        "topic_list": json.loads(db_session.topic_list) if db_session.topic_list else [],
        "status": db_session.status,
        "start_time": db_session.start_time,
        "end_time": db_session.end_time,
        "overall_score": db_session.overall_score,
        "current_level": adaptive_state.get("current_level", 1),
        "total_questions_asked": adaptive_state.get("total_questions_asked", 0),
    }
