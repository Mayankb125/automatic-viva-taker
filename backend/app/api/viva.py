"""
api/viva.py — Viva Question & Answer Routes
=============================================
The core of the exam experience. Handles the question-answer cycle.

All routes are prefixed with /api/viva.

Endpoints:
    GET  /api/viva/question    — Get the next deterministic NLP question for the student
    POST /api/viva/answer      — Submit the student's audio answer for scoring
"""

import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.session import Session
from app.models.question import Question
from app.models.score import Score
from app.services.pillar2_nlp.question_generator import generate_question, generate_fallback_question
from app.services.pillar2_nlp.adaptive_logic import process_answer
from app.services.pillar2_nlp.speech_to_text import transcribe_audio_blob
from app.services.pillar2_nlp.text_to_speech import synthesize_question_audio
from app.services.pillar3_assessment.answer_evaluator import evaluate_answer
from app.services.pillar3_assessment.dual_pipeline.pipeline_router import select_active_mode_result
from app.services.pillar3_assessment.dual_pipeline.result_merger import build_api_response_payload, build_score_row_payload
from app.services.pillar3_assessment.dual_pipeline.session_mode import resolve_pipeline_mode
from app.services.pillar3_assessment.rubric_evaluator import (
    build_legacy_rubric,
    evaluate_answer_with_rubric,
)

# All routes in this file get the /api/viva prefix automatically
router = APIRouter(prefix="/api/viva", tags=["viva"])


# ── Request schema ────────────────────────────────────────────────────────────

class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer_text: str | None = None
    audio_blob: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/question")
def get_question(session_id: str, db: DBSession = Depends(get_db)):
    """
    Generate and return the next deterministic question for the active session.

    Reads current_topic and current_level from the session's adaptive state,
    builds a local question payload, saves a Question row to the DB, and
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

    # Pull recent same-topic/same-level questions to avoid near-duplicate prompts.
    recent_rows = (
        db.query(Question.question_text)
        .filter(
            Question.session_id == session_id,
            Question.topic == current_topic,
            Question.level == current_level,
        )
        .order_by(Question.asked_at.desc())
        .limit(8)
        .all()
    )
    recent_questions = [row[0] for row in recent_rows if row and row[0]]

    # ── LLM-first question generation with deterministic fallback ──────────
    generated = None
    last_generation_error = None
    for attempt in range(3):
        try:
            generated = generate_question(
                topic=current_topic,
                level=current_level,
                recent_questions=recent_questions,
            )
            break
        except Exception as exc:
            last_generation_error = exc
            logger.warning(
                "generate_question attempt %s/3 failed for topic %s level %s: %s",
                attempt + 1,
                current_topic,
                current_level,
                exc,
            )
            time.sleep(0.4)

    if generated is None:
        logger.warning(
            "LLM question generation unavailable for topic %s level %s; using deterministic fallback. Last error: %s",
            current_topic,
            current_level,
            last_generation_error,
        )
        generated = generate_fallback_question(
            topic=current_topic,
            level=current_level,
            recent_questions=recent_questions,
        )

    # ── Keep LLM-generated fields as canonical scoring reference ───────────
    source_chunk_ids: list[str] = []
    rubric_payload: dict | None = None
    generation_mode = "llm_generated"

    # ── Convert question text to spoken audio ─────────────────────────────
    try:
        question_audio, question_audio_mime = synthesize_question_audio(generated["question"])
    except Exception as exc:
        logger.exception("question TTS failed for topic %s level %s: %s", current_topic, current_level, exc)
        raise HTTPException(
            status_code=503,
            detail="Question audio generation temporarily unavailable — please try again.",
        )

    # ── Persist the question row ───────────────────────────────────────────
    question_id = str(uuid.uuid4())
    db_question = Question(
        id=question_id,
        session_id=session_id,
        topic=current_topic,
        question_text=generated["question"],
        expected_answer=generated["expected_answer"],
        key_keywords=json.dumps(generated["key_keywords"]),
        key_points=json.dumps(generated["key_points"]),
        source_chunk_ids=json.dumps(source_chunk_ids) if source_chunk_ids else None,
        rubric_json=json.dumps(rubric_payload) if rubric_payload else None,
        pipeline_mode=generation_mode,
        generation_mode=generation_mode,
        rubric_version=(rubric_payload or {}).get("rubric_version"),
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
        "question_audio": question_audio,
        "question_audio_mime": question_audio_mime,
        "level": current_level,
        "topic": current_topic,
        "source_chunk_ids": source_chunk_ids,
        "rubric_json": rubric_payload,
        "rubric_version": (rubric_payload or {}).get("rubric_version"),
        "generation_mode": generation_mode,
        "pipeline_mode": generation_mode,
        "grounding": {
            "is_grounded": bool(source_chunk_ids and rubric_payload),
            "asset_id": None,
            "source_chunk_ids": source_chunk_ids,
            "rubric_json": rubric_payload,
            "rubric_version": (rubric_payload or {}).get("rubric_version"),
            "generation_mode": generation_mode,
        },
    }


@router.post("/answer")
def submit_answer(body: SubmitAnswerRequest, db: DBSession = Depends(get_db)):
    """
    Score the student's answer and update the adaptive session state.

        Pipeline:
            1. Load Session + Question from DB
            2. Score the answer with the legacy evaluator
            3. Score the same answer with the grounded evaluator
            4. Save a Score row with both payloads
            5. Pick the active mode result and run process_answer()
            6. Persist updated adaptive state back to the Session row
            7. Return combined compare payload to the frontend

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
    try:
        key_keywords = json.loads(db_question.key_keywords) if db_question.key_keywords else []
    except json.JSONDecodeError:
        key_keywords = []

    try:
        key_points = json.loads(db_question.key_points) if db_question.key_points else []
    except json.JSONDecodeError:
        key_points = []

    # Always build grounded rubric from the LLM-generated reference fields.
    # This keeps both pipelines anchored to the same expected-answer payload.
    rubric_payload = build_legacy_rubric(
        expected_answer=db_question.expected_answer or "",
        key_keywords=key_keywords,
        key_points=key_points,
    )

    # ── Resolve answer text ───────────────────────────────────────────────
    if body.answer_text and body.answer_text.strip():
        transcribed_answer = body.answer_text.strip()
    elif body.audio_blob:
        try:
            transcribed_answer = transcribe_audio_blob(
                body.audio_blob,
                topic=adaptive_state.get("current_topic"),
                keywords=key_keywords,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid audio input: {exc}")
        except Exception as exc:
            logger.exception("Speech transcription failed for question %s: %s", body.question_id, exc)
            raise HTTPException(
                status_code=503,
                detail="Transcription service temporarily unavailable — please record again.",
            )
    else:
        raise HTTPException(status_code=400, detail="Provide answer_text or audio_blob")

    pipeline_mode = resolve_pipeline_mode(db_session.pipeline_mode, db_question.pipeline_mode)

    # ── Run both scorers so the API can compare outputs ──────────────────
    try:
        legacy_result = evaluate_answer(
            question=db_question.question_text,
            expected_answer=db_question.expected_answer or "",
            student_answer=transcribed_answer,
            key_keywords=key_keywords,
            key_points=key_points,
            current_level=adaptive_state["current_level"],
            switched=len(adaptive_state["switched_topics"]) > 0,
        )
        grounded_result = evaluate_answer_with_rubric(
            question=db_question.question_text,
            student_answer=transcribed_answer,
            rubric=rubric_payload,
            current_level=adaptive_state["current_level"],
            switched=len(adaptive_state["switched_topics"]) > 0,
        )
    except Exception as exc:
        logger.exception("deterministic rubric scoring failed for question %s: %s", body.question_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Scoring service temporarily unavailable — please resubmit your answer.",
        )

    active_mode_result = select_active_mode_result(
        pipeline_mode=pipeline_mode,
        legacy_result=legacy_result,
        grounded_result=grounded_result,
        dual_compare_policy="score_max",
    )
    active_final_score = active_mode_result["final_score"]
    score_row_payload = build_score_row_payload(
        pipeline_mode=pipeline_mode,
        active_mode_result=active_mode_result,
        legacy_result=legacy_result,
        grounded_result=grounded_result,
    )

    # ── Save Score row ────────────────────────────────────────────────────
    db_score = Score(
        id=str(uuid.uuid4()),
        question_id=body.question_id,
        session_id=body.session_id,
        topic=adaptive_state["current_topic"],
        student_answer=transcribed_answer,
        semantic_score=score_row_payload["semantic_score"],
        keyword_score=score_row_payload["keyword_score"],
        depth_score=score_row_payload["depth_score"],
        completeness_score=score_row_payload["completeness_score"],
        confidence_score=score_row_payload["confidence_score"],
        final_score=score_row_payload["final_score"],
        depth_reason=score_row_payload["depth_reason"],
        completeness_reason=score_row_payload["completeness_reason"],
        scoring_version=score_row_payload["scoring_version"],
        scoring_mode=score_row_payload["scoring_mode"],
        raw_weighted_score=score_row_payload["raw_weighted_score"],
        total_penalty=score_row_payload["total_penalty"],
        level_bonus_applied=score_row_payload["level_bonus_applied"],
        score_band=score_row_payload["score_band"],
        legacy_score_json=json.dumps(score_row_payload["legacy_score_json"]),
        grounded_score_json=json.dumps(score_row_payload["grounded_score_json"]),
        feature_breakdown_json=json.dumps(score_row_payload["feature_breakdown_json"]),
        penalties_json=json.dumps(score_row_payload["penalties_json"]),
        flags_json=json.dumps(score_row_payload["flags_json"]),
        matched_must_concepts_json=json.dumps(score_row_payload["matched_must_concepts_json"]),
        missing_must_concepts_json=json.dumps(score_row_payload["missing_must_concepts_json"]),
        matched_optional_concepts_json=json.dumps(score_row_payload["matched_optional_concepts_json"]),
        matched_phrases_json=json.dumps(score_row_payload["matched_phrases_json"]),
        missing_phrases_json=json.dumps(score_row_payload["missing_phrases_json"]),
        rubric_snapshot_json=json.dumps(rubric_payload),
        feedback_summary=score_row_payload["feedback_summary"],
        recommendation=score_row_payload["recommendation"],
        adaptive_decision=None,   # filled in after process_answer runs
    )
    db.add(db_score)

    # ── Run adaptive logic ────────────────────────────────────────────────
    updated_state = process_answer(adaptive_state, active_final_score)
    db_score.adaptive_decision = updated_state["decision"]

    # Sync session row: topic may have changed, session may now be completed
    db_session.topic = updated_state["current_topic"]
    db_session.adaptive_state = json.dumps(updated_state)
    if updated_state["state"] == "completed":
        db_session.status = "completed"

    db.commit()

    return build_api_response_payload(
        compare_mode_enabled=pipeline_mode == "dual_compare",
        transcribed_text=transcribed_answer,
        pipeline_mode=pipeline_mode,
        legacy_result=legacy_result,
        grounded_result=grounded_result,
        active_mode_result=active_mode_result,
        updated_state=updated_state,
    )
