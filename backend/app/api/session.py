"""
api/session.py — Viva Session Routes
======================================
Manages the lifecycle of a viva session: starting, ending, and topic switching.

All routes are prefixed with /api/session.
These are currently STUB implementations that return {"status": "ok"}.
Real logic will be added in Phase 3.

Endpoints:
    POST /api/session/start           — Start a new session for the logged-in student
    POST /api/session/end             — End the active session, calculate overall score
    POST /api/session/switch-topic    — Change the current topic mid-session
    GET  /api/session/{session_id}    — Fetch details and status of a specific session
"""

from fastapi import APIRouter

# All routes in this file get the /api/session prefix automatically
router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start")
def start_session():
    """
    Start a new viva session.
    TODO (Phase 3): Accept student_id, subject, and topic_list.
    Create a new Session row with status="active" and return the session_id.
    """
    return {"status": "ok"}


@router.post("/end")
def end_session():
    """
    End the active viva session.
    TODO (Phase 3): Accept session_id. Set end_time=now, status="completed".
    Trigger overall score calculation across all Score rows for this session.
    """
    return {"status": "ok"}


@router.post("/switch-topic")
def switch_topic():
    """
    Switch to a different topic mid-session.
    TODO (Phase 3): Accept session_id + new topic name.
    Update the session's 'topic' field. The question generator will use
    the new topic for all subsequent questions.
    """
    return {"status": "ok"}


@router.get("/{session_id}")
def get_session(session_id: str):
    """
    Get the current state of a session by its ID.
    TODO (Phase 3): Query the sessions table. Return session details including
    status, current topic, start time, and overall_score if completed.
    """
    return {"status": "ok"}
