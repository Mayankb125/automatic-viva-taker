"""
api/viva.py — Viva Question & Answer Routes
=============================================
The core of the exam experience. Handles the question-answer cycle.

All routes are prefixed with /api/viva.

Endpoints:
    GET  /api/viva/question    — Get the next AI-generated question for the student
    POST /api/viva/answer      — Submit the student's typed answer for scoring
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.session import Session
from app.models.question import Question
from app.models.score import Score
from app.services.pillar2_nlp.question_generator import generate_question
from app.services.pillar2_nlp.adaptive_logic import process_answer
from app.services.pillar3_assessment.answer_evaluator import evaluate_answer

# All routes in this file get the /api/viva prefix automatically
router = APIRouter(prefix="/api/viva", tags=["viva"])


# ── Request schema ────────────────────────────────────────────────────────────

class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    text_answer: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/question")
def get_question(session_id: str, db: DBSession = Depends(get_db)):
    """
    Generate and return the next AI question for the active session.

    Reads current_topic and current_level from the session's adaptive state,
    calls Gemini to produce a question, saves a Question row to the DB, and
    returns the question text + metadata to the frontend.
    """
    # Load the session
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    adaptive_state = json.loads(db_session.adaptive_state)
    current_topic = adaptive_state["current_topic"]
    current_level = adaptive_state["current_level"]

    # ── Call Gemini to generate the question ───────────────────────────────
    # generate_question makes an external Gemini API call which can fail due to
    # network errors, rate limits, or API timeouts. Return a 503 instead of a
    # raw 500 traceback so the frontend can display a meaningful message.
    try:
        generated = generate_question(topic=current_topic, level=current_level)
    except Exception as exc:
        logger.exception("generate_question failed for topic %s level %s: %s", current_topic, current_level, exc)
        raise HTTPException(
            status_code=503,
            detail="Question generation temporarily unavailable — please try again.",
        )

    # ── Persist the question row ───────────────────────────────────────────
    question_id = str(uuid.uuid4())
    db_question = Question(
        id=question_id,
        session_id=session_id,
        question_text=generated["question"],
        expected_answer=generated["expected_answer"],
        key_keywords=json.dumps(generated["key_keywords"]),
        key_points=json.dumps(generated["key_points"]),
        level=current_level,
    )
    db.add(db_question)

    # Track in adaptive state history so we can look back later
    adaptive_state["question_history"].append(question_id)
    db_session.adaptive_state = json.dumps(adaptive_state)
    db.commit()

    return {
        "question_id": question_id,
        "question_text": generated["question"],
        "level": current_level,
        "topic": current_topic,
    }


@router.post("/answer")
def submit_answer(body: SubmitAnswerRequest, db: DBSession = Depends(get_db)):
    """
    Score the student's answer and update the adaptive session state.

    Pipeline:
      1. Load Session + Question from DB
      2. Run all 5 scorers via evaluate_answer()
      3. Save a Score row with the full breakdown
      4. Run process_answer() to get the adaptive decision
      5. Persist updated adaptive state back to the Session row
      6. Return score breakdown + adaptive decision to the frontend

    The 'adaptive.show_topic_modal' flag in the response is True when the student
    must pick a new topic (checkpoint failed twice) — the frontend should show
    a topic-selection modal in that case.
    """
    # ── Load session and question ─────────────────────────────────────────
    db_session = db.query(Session).filter(Session.id == body.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_question = (
        db.query(Question)
        .filter(Question.id == body.question_id, Question.session_id == body.session_id)
        .first()
    )
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")

    adaptive_state = json.loads(db_session.adaptive_state)

    # A switch penalty applies if the student has already switched topics this session
    switched = len(adaptive_state["switched_topics"]) > 0

    # Parse the JSON-string arrays stored in the Question row
    key_keywords = json.loads(db_question.key_keywords) if db_question.key_keywords else []
    key_points = json.loads(db_question.key_points) if db_question.key_points else []

    # ── Run all 5 scorers ─────────────────────────────────────────────────
    # evaluate_answer makes an external Gemini API call (depth scorer) which
    # can fail due to network errors, rate limits, or API timeouts.
    # Catch those failures and return a clear 503 rather than a raw 500 traceback.
    try:
        eval_result = evaluate_answer(
            question=db_question.question_text,
            expected_answer=db_question.expected_answer,
            student_answer=body.text_answer,
            key_keywords=key_keywords,
            key_points=key_points,
            current_level=adaptive_state["current_level"],
            switched=switched,
        )
    except Exception as exc:
        logger.exception("evaluate_answer failed for question %s: %s", body.question_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Scoring service temporarily unavailable — please resubmit your answer.",
        )

    # ── Save Score row ────────────────────────────────────────────────────
    db_score = Score(
        id=str(uuid.uuid4()),
        question_id=body.question_id,
        session_id=body.session_id,
        topic=adaptive_state["current_topic"],
        student_answer=body.text_answer,
        semantic_score=eval_result["semantic_score"],
        keyword_score=eval_result["keyword_score"],
        depth_score=eval_result["depth_score"],
        completeness_score=eval_result["completeness_score"],
        confidence_score=eval_result["confidence_score"],
        final_score=eval_result["final_score"],
        depth_reason=eval_result["depth_reason"],
        completeness_reason=eval_result["completeness_reason"],
        adaptive_decision=None,   # filled in after process_answer runs
    )
    db.add(db_score)

    # ── Run adaptive logic ────────────────────────────────────────────────
    updated_state = process_answer(adaptive_state, eval_result["final_score"])
    db_score.adaptive_decision = updated_state["decision"]

    # Sync session row: topic may have changed, session may now be completed
    db_session.topic = updated_state["current_topic"]
    db_session.adaptive_state = json.dumps(updated_state)
    if updated_state["state"] == "completed":
        db_session.status = "completed"

    db.commit()

    return {
        "score_breakdown": {
            "semantic_score":     eval_result["semantic_score"],
            "keyword_score":      eval_result["keyword_score"],
            "depth_score":        eval_result["depth_score"],
            "completeness_score": eval_result["completeness_score"],
            "confidence_score":   eval_result["confidence_score"],
            "weighted_score":     eval_result["weighted_score"],
            "level_bonus":        eval_result["level_bonus"],
            "switch_penalty":     eval_result["switch_penalty"],
            "final_score":        eval_result["final_score"],
        },
        "feedback": {
            "depth_reason":        eval_result["depth_reason"],
            "completeness_reason": eval_result["completeness_reason"],
        },
        "adaptive": {
            "decision":         updated_state["decision"],
            "show_topic_modal": updated_state["show_topic_modal"],
            "current_topic":    updated_state["current_topic"],
            "current_level":    updated_state["current_level"],
            "total_questions":  updated_state["total_questions_asked"],
        },
    }
