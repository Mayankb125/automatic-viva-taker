"""Integrity event helpers for building and persisting CV flags."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy.orm import Session as DBSession

from app.models.integrity_flag import IntegrityFlag


def build_integrity_event(
    session_id: str,
    question_id: str | None,
    flag_type: str,
    description: str | None = None,
    timestamp: datetime | None = None,
):
    """Build a normalized integrity event payload."""
    ts = timestamp or datetime.utcnow()
    return {
        "session_id": session_id,
        "question_id": question_id,
        "flag_type": flag_type,
        "description": description,
        "timestamp": ts.isoformat(),
    }


def save_integrity_flag(
    db: DBSession,
    session_id: str,
    question_id: str | None,
    flag_type: str,
    description: str | None = None,
    timestamp: datetime | None = None,
    video_clip_path: str | None = None,
):
    """Persist one integrity flag row and return normalized payload."""
    ts = timestamp or datetime.utcnow()
    db_flag = IntegrityFlag(
        id=str(uuid.uuid4()),
        session_id=session_id,
        question_id=question_id,
        timestamp=ts,
        flag_type=flag_type,
        description=description,
        video_clip_path=video_clip_path,
    )
    db.add(db_flag)

    return build_integrity_event(
        session_id=session_id,
        question_id=question_id,
        flag_type=flag_type,
        description=description,
        timestamp=ts,
    )
