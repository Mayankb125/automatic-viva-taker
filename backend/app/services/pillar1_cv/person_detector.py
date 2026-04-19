"""YOLO person-count detector for extra-person proctoring flags."""

from __future__ import annotations

import time

from .object_detector import run_yolo_inference


_SESSION_EXTRA_PERSON_STARTED_AT: dict[str, float | None] = {}


def detect_persons(
    frame,
    session_id: str,
    timestamp: float | None = None,
    confidence_threshold: float = 0.6,
    extra_person_seconds_threshold: float = 3.0,
    yolo_result=None,
):
    """Count people in frame and flag sustained multi-person presence."""
    now = timestamp if timestamp is not None else time.time()

    try:
        result = yolo_result if yolo_result is not None else run_yolo_inference(
            frame,
            confidence_threshold=confidence_threshold,
        )
    except Exception as exc:
        return {
            "available": False,
            "person_count": 0,
            "is_flagged": False,
            "flag_type": None,
            "extra_person_duration_seconds": 0.0,
            "error": f"person detector unavailable: {exc}",
        }

    person_count = 0
    if result is not None and result.boxes is not None:
        names = result.names or {}
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            label = str(names.get(class_id, class_id)).lower()
            if label == "person":
                person_count += 1

    extra_person = person_count > 1
    started_at = _SESSION_EXTRA_PERSON_STARTED_AT.get(session_id)

    if not extra_person:
        _SESSION_EXTRA_PERSON_STARTED_AT[session_id] = None
        duration = 0.0
        is_flagged = False
    else:
        if started_at is None:
            started_at = now
            _SESSION_EXTRA_PERSON_STARTED_AT[session_id] = started_at
        duration = max(0.0, now - started_at)
        is_flagged = duration >= extra_person_seconds_threshold

    return {
        "available": True,
        "person_count": person_count,
        "is_flagged": is_flagged,
        "flag_type": "extra_person" if is_flagged else None,
        "extra_person_duration_seconds": round(duration, 2),
    }
