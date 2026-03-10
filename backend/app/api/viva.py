"""
api/viva.py — Viva Question & Answer Routes
=============================================
The core of the exam experience. Handles the question-answer cycle.

All routes are prefixed with /api/viva.
These are currently STUB implementations.
Real logic integrating the NLP brain (Phase 2) will be added in Phase 3.

Endpoints:
    GET  /api/viva/question    — Get the next AI-generated question for the student
    POST /api/viva/answer      — Submit the student's spoken/typed answer for scoring
"""

from fastapi import APIRouter

# All routes in this file get the /api/viva prefix automatically
router = APIRouter(prefix="/api/viva", tags=["viva"])


@router.get("/question")
def get_question():
    """
    Generate and return the next question for the active session.
    TODO (Phase 3): Accept session_id. Look up current topic and last score.
    Call question_generator.py (Phase 2), which uses Gemini to create
    a question at the appropriate difficulty level (adaptive logic).
    Save the Question row and return question_text + level.
    """
    return {"status": "ok"}


@router.post("/answer")
def submit_answer():
    """
    Accept and score the student's answer to the current question.
    TODO (Phase 3): Accept session_id, question_id, and answer text/audio.
    Pass through the 5 scorers (semantic, keyword, depth, completeness, confidence).
    Save a Score row with all scorer outputs and the final weighted score.
    Return the score breakdown + adaptive decision for the next question.
    """
    return {"status": "ok"}
