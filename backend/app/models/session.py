"""
models/session.py — Viva Session Table
========================================
One row per viva attempt. A session tracks the full lifecycle of a student's
exam from start to finish.

Flow:
  1. Student logs in and picks a subject + topics  → POST /api/session/start creates a row
  2. Questions are asked and answered              → status stays "active"
  3. Student clicks "End" or time is up            → POST /api/session/end sets end_time,
                                                     status="completed", overall_score

Relationships:
  - Belongs to one Student    (student_id → students.id)
  - Has many Questions        (questions.session_id → sessions.id)
  - Has many Scores           (scores.session_id → sessions.id)
  - Has many IntegrityFlags   (integrity_flags.session_id → sessions.id)
"""

from sqlalchemy import Column, Text, DateTime, Float
from datetime import datetime
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    # Unique session ID — generated as a UUID string when the session starts
    id = Column(Text, primary_key=True)

    # Foreign key: which student this session belongs to
    student_id = Column(Text, nullable=False)

    # The broad subject chosen by the student (e.g. "Computer Science")
    subject = Column(Text, nullable=True)

    # The currently active topic being questioned (e.g. "Data Structures").
    # Updated when the student switches topics mid-session.
    topic = Column(Text, nullable=True)

    # JSON array stored as a string listing all topics the student selected.
    # Example: '["Data Structures", "Operating Systems"]'
    # Stored as text because SQLite has no native array type.
    topic_list = Column(Text, nullable=True)   # JSON array stored as string

    # Session-wide evaluation mode.
    # Example values: "legacy_only", "grounded_only", "dual_compare"
    pipeline_mode = Column(Text, nullable=True)

    # When the viva session started (UTC)
    start_time = Column(DateTime, default=datetime.utcnow)

    # When the session ended (UTC). Null while still active.
    end_time = Column(DateTime, nullable=True)

    # Current state of the session. Values: "active" | "completed"
    status = Column(Text, default="active")    # active / completed

    # Final weighted score across all questions (0.0–100.0).
    # Calculated and stored when the session ends.
    overall_score = Column(Float, nullable=True)

    # Full adaptive engine state serialised as a JSON string.
    # Stores current_level, checkpoint state, question counts, topic_scores, etc.
    # Loaded and written back on every question/answer round-trip.
    adaptive_state = Column(Text, nullable=True)
