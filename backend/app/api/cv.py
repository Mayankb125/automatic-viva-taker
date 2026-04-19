"""api/cv.py - Multi-layer anti-cheating CV route with weighted trust scoring."""

from __future__ import annotations

from datetime import datetime
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.session import Session
from app.services.pillar1_cv import (
    analyze_gaze,
    decode_frame_base64,
    run_yolo_inference,
    save_integrity_flag,
)


router = APIRouter(prefix="/api/cv", tags=["cv"])


class AnalyzeFrameRequest(BaseModel):
    session_id: str
    question_id: str | None = None
    frame: str
    captured_at: float | None = None


STRICT_FLAGS = {
    "extra_person",
    "extra_body_part",
    "phone",
    "tablet",
    "book",
    "laptop",
}
GAZE_FLAG = "gaze_deviation"

STRICT_PENALTY = 30
GAZE_PENALTY = 3

FLAG_COOLDOWN_SECONDS = 5.0
GAZE_AWAY_SECONDS = 2.4

_SESSION_RUNTIME: dict[str, dict[str, Any]] = {}


def _load_adaptive_state(db_session: Session) -> dict[str, Any]:
    if not db_session.adaptive_state:
        return {}
    try:
        return json.loads(db_session.adaptive_state)
    except Exception:
        return {}


def _load_runtime(session_id: str, adaptive_state: dict[str, Any]) -> dict[str, Any]:
    runtime = _SESSION_RUNTIME.get(session_id)
    if runtime is not None:
        return runtime

    cv_state = adaptive_state.get("cv_state", {}) if isinstance(adaptive_state, dict) else {}
    runtime = {
        "trust_score": int(cv_state.get("trust_score", 100)),
        "violation_score": int(cv_state.get("violation_score", 0)),
        "manual_review_required": bool(cv_state.get("manual_review_required", False)),
        "last_emit_ts": {},
    }
    _SESSION_RUNTIME[session_id] = runtime
    return runtime


def _save_runtime_to_session(db_session: Session, adaptive_state: dict[str, Any], runtime: dict[str, Any]):
    adaptive_state["cv_state"] = {
        "trust_score": runtime["trust_score"],
        "violation_score": runtime["violation_score"],
        "manual_review_required": runtime["manual_review_required"],
        "updated_at": datetime.utcnow().isoformat(),
    }
    db_session.adaptive_state = json.dumps(adaptive_state)


def _cooldown_passed(runtime: dict[str, Any], flag_type: str, now_ts: float) -> bool:
    last_emit = runtime["last_emit_ts"].get(flag_type)
    if last_emit is not None and (now_ts - last_emit) < FLAG_COOLDOWN_SECONDS:
        return False
    runtime["last_emit_ts"][flag_type] = now_ts
    return True


def _apply_penalty(runtime: dict[str, Any], flag_type: str) -> tuple[int, int]:
    if flag_type in STRICT_FLAGS:
        trust_delta = STRICT_PENALTY
        violation_delta = STRICT_PENALTY
        runtime["manual_review_required"] = True
    elif flag_type == GAZE_FLAG:
        trust_delta = GAZE_PENALTY
        violation_delta = GAZE_PENALTY
    else:
        trust_delta = 0
        violation_delta = 0

    runtime["trust_score"] = max(0, runtime["trust_score"] - trust_delta)
    runtime["violation_score"] = min(100, runtime["violation_score"] + violation_delta)

    if runtime["trust_score"] <= 40:
        runtime["manual_review_required"] = True

    return trust_delta, violation_delta


def _parse_yolo_result(yolo_result) -> list[dict[str, Any]]:
    if yolo_result is None or yolo_result.boxes is None:
        return []

    names = yolo_result.names or {}
    parsed = []
    for box in yolo_result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
        label = str(names.get(class_id, class_id)).lower()
        parsed.append(
            {
                "label": label,
                "confidence": round(confidence, 3),
                "bbox": [x1, y1, x2, y2],
            }
        )
    return parsed


def _largest_person_bbox(detections: list[dict[str, Any]]) -> list[float] | None:
    people = [item["bbox"] for item in detections if item["label"] == "person"]
    if not people:
        return None

    def area(box: list[float]) -> float:
        return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])

    return max(people, key=area)


def _expand_bbox(box: list[float], margin_ratio: float, frame_w: int, frame_h: int) -> list[float]:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    mx = w * margin_ratio
    my = h * margin_ratio
    return [
        max(0.0, x1 - mx),
        max(0.0, y1 - my),
        min(float(frame_w - 1), x2 + mx),
        min(float(frame_h - 1), y2 + my),
    ]


def _point_in_box(px: float, py: float, box: list[float]) -> bool:
    return box[0] <= px <= box[2] and box[1] <= py <= box[3]


def _detect_extra_person_or_body_part(frame, detections: list[dict[str, Any]]) -> dict[str, Any]:
    people = [item for item in detections if item["label"] == "person"]
    if len(people) > 1:
        return {
            "is_flagged": True,
            "flag_type": "extra_person",
            "reason": f"Detected {len(people)} people in frame",
            "hands_detected": 0,
        }

    primary_box = _largest_person_bbox(detections)
    if primary_box is None:
        return {
            "is_flagged": False,
            "flag_type": None,
            "reason": "No primary person box available",
            "hands_detected": 0,
        }

    try:
        import cv2
        import mediapipe as mp

        if not hasattr(_detect_extra_person_or_body_part, "_hands"):
            _detect_extra_person_or_body_part._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=4,
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hand_result = _detect_extra_person_or_body_part._hands.process(rgb)

        if not hand_result.multi_hand_landmarks:
            return {
                "is_flagged": False,
                "flag_type": None,
                "reason": "No hand landmarks",
                "hands_detected": 0,
            }

        expanded = _expand_bbox(primary_box, margin_ratio=0.20, frame_w=w, frame_h=h)
        outside_hands = 0
        for hand in hand_result.multi_hand_landmarks:
            center_x = sum(point.x for point in hand.landmark) / len(hand.landmark) * w
            center_y = sum(point.y for point in hand.landmark) / len(hand.landmark) * h
            if not _point_in_box(center_x, center_y, expanded):
                outside_hands += 1

        if outside_hands > 0:
            return {
                "is_flagged": True,
                "flag_type": "extra_body_part",
                "reason": f"Detected {outside_hands} hand(s) outside primary body region",
                "hands_detected": len(hand_result.multi_hand_landmarks),
            }

        return {
            "is_flagged": False,
            "flag_type": None,
            "reason": "Hands aligned with primary person",
            "hands_detected": len(hand_result.multi_hand_landmarks),
        }
    except Exception as exc:
        return {
            "is_flagged": False,
            "flag_type": None,
            "reason": f"Body-part detector unavailable: {exc}",
            "hands_detected": 0,
        }


def _detect_contraband(detections: list[dict[str, Any]]) -> dict[str, Any]:
    flag_types: list[str] = []
    matched: list[dict[str, Any]] = []

    for item in detections:
        label = item["label"]
        if label == "cell phone":
            flag_types.append("phone")
            matched.append(item)
        elif label == "book":
            flag_types.append("book")
            matched.append(item)
        elif label == "laptop":
            flag_types.append("laptop")
            matched.append(item)
        elif label in {"tablet", "tv", "monitor"}:
            flag_types.append("tablet")
            matched.append(item)

    unique_flags = []
    seen = set()
    for flag in flag_types:
        if flag not in seen:
            unique_flags.append(flag)
            seen.add(flag)

    return {
        "is_flagged": len(unique_flags) > 0,
        "flag_types": unique_flags,
        "matched_objects": matched,
    }


def _detect_gaze_event(frame, session_id: str, now_ts: float) -> dict[str, Any]:
    gaze = analyze_gaze(
        frame=frame,
        session_id=session_id,
        timestamp=now_ts,
        away_seconds_threshold=GAZE_AWAY_SECONDS,
    )

    direction = gaze.get("gaze_direction", "unknown")
    away_duration = float(gaze.get("away_duration_seconds", 0.0) or 0.0)
    is_event = bool(gaze.get("is_flagged")) and direction in {"left", "right", "up", "down", "no_face", "no_eyes"}

    if not is_event:
        return {
            "is_flagged": False,
            "flag_type": None,
            "reason": "No prolonged gaze deviation",
            "raw": gaze,
        }

    if direction == "no_face":
        reason = f"Face not visible for {round(away_duration, 2)}s"
    elif direction == "no_eyes":
        reason = f"Eyes not trackable for {round(away_duration, 2)}s"
    else:
        reason = f"Gaze deviation ({direction}) for {round(away_duration, 2)}s"

    return {
        "is_flagged": True,
        "flag_type": GAZE_FLAG,
        "reason": reason,
        "raw": gaze,
    }


@router.post("/analyze")
def analyze_frame(body: AnalyzeFrameRequest, db: DBSession = Depends(get_db)):
    """Analyze one webcam frame and apply weighted anti-cheating penalties."""
    db_session = db.query(Session).filter(Session.id == body.session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    adaptive_state = _load_adaptive_state(db_session)
    runtime = _load_runtime(body.session_id, adaptive_state)

    timestamp = body.captured_at if body.captured_at is not None else time.time()
    event_time = datetime.utcfromtimestamp(timestamp)

    try:
        frame = decode_frame_base64(body.frame)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid frame input: {exc}")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    yolo_result = None
    try:
        yolo_result = run_yolo_inference(frame, confidence_threshold=0.55)
    except Exception:
        yolo_result = None

    detections = _parse_yolo_result(yolo_result)
    body_check = _detect_extra_person_or_body_part(frame, detections)
    contraband_check = _detect_contraband(detections)
    gaze_check = _detect_gaze_event(frame, session_id=body.session_id, now_ts=timestamp)

    candidate_flags: list[tuple[str, str]] = []
    if body_check.get("is_flagged") and body_check.get("flag_type"):
        candidate_flags.append((body_check["flag_type"], body_check["reason"]))
    for flag in contraband_check.get("flag_types", []):
        candidate_flags.append((flag, f"Detected restricted object: {flag}"))
    if gaze_check.get("is_flagged") and gaze_check.get("flag_type"):
        candidate_flags.append((gaze_check["flag_type"], gaze_check["reason"]))

    deduped_flags: dict[str, str] = {}
    for flag_type, reason in candidate_flags:
        if flag_type not in deduped_flags:
            deduped_flags[flag_type] = reason

    live_flag_reasons = [
        {"flag_type": flag_type, "reason": reason}
        for flag_type, reason in deduped_flags.items()
    ]

    persisted_events = []
    suppressed_flags = []
    applied_penalties = []

    for flag_type, reason in deduped_flags.items():
        if not _cooldown_passed(runtime, flag_type, timestamp):
            suppressed_flags.append(flag_type)
            continue

        trust_delta, violation_delta = _apply_penalty(runtime, flag_type)
        applied_penalties.append(
            {
                "flag_type": flag_type,
                "trust_delta": trust_delta,
                "violation_delta": violation_delta,
            }
        )

        event = save_integrity_flag(
            db=db,
            session_id=body.session_id,
            question_id=body.question_id,
            flag_type=flag_type,
            description=reason,
            timestamp=event_time,
        )
        persisted_events.append(event)

    _save_runtime_to_session(db_session, adaptive_state, runtime)
    db.commit()

    return {
        "flags": [event["flag_type"] for event in persisted_events],
        "live_flags": [item["flag_type"] for item in live_flag_reasons],
        "live_flag_reasons": live_flag_reasons,
        "persisted_events": persisted_events,
        "suppressed_flags": suppressed_flags,
        "applied_penalties": applied_penalties,
        "trust_score": runtime["trust_score"],
        "violation_score": runtime["violation_score"],
        "manual_review_required": runtime["manual_review_required"],
        "details": {
            "detections": detections,
            "body_part_check": body_check,
            "contraband_check": contraband_check,
            "gaze_check": gaze_check,
        },
    }
