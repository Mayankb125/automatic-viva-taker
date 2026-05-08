"""Computer-vision proctoring API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.session import Session
from app.services.pillar1_cv import (
    analyze_gaze,
    analyze_head_pose,
    decode_frame_base64,
    detect_objects,
    detect_persons,
    run_yolo_inference,
    save_integrity_flag,
)

router = APIRouter(prefix="/api/cv", tags=["cv"])


class AnalyzeFrameRequest(BaseModel):
    session_id: str
    question_id: str | None = None
    frame: str
    captured_at: float | None = None


def _to_live_flag_type(raw_flag_type: str) -> str:
    """Map backend detector names to frontend-facing flag labels."""
    mapping = {
        "gaze_away": "gaze_deviation",
        "head_turned": "head_turned",
        "phone": "phone",
        "book": "book",
        "laptop": "laptop",
        "extra_person": "extra_person",
    }
    return mapping.get(raw_flag_type, raw_flag_type)


def _build_reason(flag_type: str, checks: dict) -> str:
    if flag_type == "gaze_deviation":
        raw = checks.get("gaze_check", {})
        direction = raw.get("gaze_direction", "away")
        duration = raw.get("away_duration_seconds", 0.0)
        return f"Gaze deviated ({direction}) for {duration:.2f}s"
    if flag_type == "head_turned":
        raw = checks.get("head_pose_check", {})
        yaw = raw.get("yaw", 0.0)
        duration = raw.get("turned_duration_seconds", 0.0)
        return f"Head turned (yaw {yaw:.1f}) for {duration:.2f}s"
    if flag_type == "extra_person":
        raw = checks.get("person_check", {})
        count = raw.get("person_count", 0)
        duration = raw.get("extra_person_duration_seconds", 0.0)
        return f"Detected {count} people in frame for {duration:.2f}s"
    if flag_type in {"phone", "book", "laptop"}:
        return f"Detected prohibited object: {flag_type}"
    return f"Detected integrity condition: {flag_type}"


@router.post("/analyze")
def analyze_frame(body: AnalyzeFrameRequest, db: DBSession = Depends(get_db)):
    """Analyze one webcam frame, return live checks, and persist hard flags."""
    db_session = db.query(Session).filter(Session.id == body.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        frame = decode_frame_base64(body.frame)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid frame payload: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    timestamp = float(body.captured_at) if body.captured_at is not None else None

    # Run YOLO once and share the result between object + person detectors.
    yolo_result = None
    try:
        yolo_result = run_yolo_inference(frame, confidence_threshold=0.6)
    except Exception:
        yolo_result = None

    gaze_check = analyze_gaze(frame, session_id=body.session_id, timestamp=timestamp)
    head_pose_check = analyze_head_pose(frame, session_id=body.session_id, timestamp=timestamp)
    object_check = detect_objects(frame, confidence_threshold=0.6, yolo_result=yolo_result)
    person_check = detect_persons(
        frame,
        session_id=body.session_id,
        timestamp=timestamp,
        confidence_threshold=0.6,
        yolo_result=yolo_result,
    )

    detector_checks = {
        "gaze_check": gaze_check,
        "head_pose_check": head_pose_check,
        "object_check": object_check,
        "person_check": person_check,
    }

    live_flags: list[str] = []
    if gaze_check.get("is_flagged"):
        live_flags.append(_to_live_flag_type(str(gaze_check.get("flag_type") or "gaze_away")))
    if head_pose_check.get("is_flagged"):
        live_flags.append(_to_live_flag_type(str(head_pose_check.get("flag_type") or "head_turned")))
    if person_check.get("is_flagged"):
        live_flags.append(_to_live_flag_type(str(person_check.get("flag_type") or "extra_person")))
    if object_check.get("is_flagged"):
        for raw_type in object_check.get("flag_types", []):
            live_flags.append(_to_live_flag_type(str(raw_type)))

    # Keep unique order.
    live_flags = list(dict.fromkeys(live_flags))

    live_flag_reasons = [
        {
            "flag_type": flag_type,
            "reason": _build_reason(flag_type, detector_checks),
        }
        for flag_type in live_flags
    ]

    persisted_flags: list[str] = []
    for flag_type in live_flags:
        db_flag_type = "gaze_away" if flag_type == "gaze_deviation" else flag_type
        reason = _build_reason(flag_type, detector_checks)
        save_integrity_flag(
            db=db,
            session_id=body.session_id,
            question_id=body.question_id,
            flag_type=db_flag_type,
            description=reason,
        )
        persisted_flags.append(flag_type)

    if persisted_flags:
        db.commit()

    return {
        "status": "ok",
        "session_id": body.session_id,
        "question_id": body.question_id,
        "flags": persisted_flags,
        "live_flags": live_flags,
        "live_flag_reasons": live_flag_reasons,
        "details": {
            "gaze_check": {
                "raw": gaze_check,
            },
            "head_pose_check": {
                "raw": head_pose_check,
            },
            "object_check": {
                "raw": object_check,
            },
            "person_check": {
                "raw": person_check,
            },
        },
    }
