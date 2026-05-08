"""
models/question.py — Question Table
===================================
One row per question asked during a viva session.

This table now supports both:
  1) legacy generation payload (expected_answer, key_keywords, key_points)
  2) new grounded payload (source_chunk_ids + rubric_json)

Relationships:
  - Belongs to one Session  (session_id -> sessions.id)
  - Has one Score           (scores.question_id -> questions.id)
"""

from sqlalchemy import Column, Text, Integer, DateTime
from datetime import datetime
from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    # Unique question ID — generated as a UUID string
    id = Column(Text, primary_key=True)

    # Foreign key: which session this question belongs to
    session_id = Column(Text, nullable=False)

    # The actual question text shown/spoken to the student
    question_text = Column(Text, nullable=False)

    # ---------------------------------------------------------------------
    # Legacy generation fields (kept temporarily for compatibility)
    # ---------------------------------------------------------------------

    # Legacy ideal answer.
    expected_answer = Column(Text, nullable=True)

    # Legacy key keywords.
    key_keywords = Column(Text, nullable=True)   # JSON array as string

    # Legacy key conceptual points.
    key_points = Column(Text, nullable=True)     # JSON array as string

    # ---------------------------------------------------------------------
    # New grounded question fields (classical NLP pipeline)
    # ---------------------------------------------------------------------

    # Source chunks used to generate this question.
    # Example: '["chunk_3", "chunk_7"]'
    source_chunk_ids = Column(Text, nullable=True)   # JSON array as string

    # Rubric built from source chunks (must concepts, optional concepts,
    # phrases, evidence sentences, and weights).
    rubric_json = Column(Text, nullable=True)

    # Which evaluation path this question is intended for.
    # Example values: "legacy_only", "grounded_only", "dual_compare"
    pipeline_mode = Column(Text, nullable=True)

    # Optional metadata for generation strategy/audit.
    generation_mode = Column(Text, nullable=True)    # e.g. "grounded_llm"
    rubric_version = Column(Text, nullable=True)     # e.g. "v1"

    # Difficulty level of this question on a scale of 1 (easy) to 5 (hard).
    # The adaptive logic adjusts this based on the student's previous scores.
    level = Column(Integer, default=1)

    # Which topic this question was generated for
    topic = Column(Text, nullable=True)

    # Timestamp when this question was asked (UTC)
    asked_at = Column(DateTime, default=datetime.utcnow)
