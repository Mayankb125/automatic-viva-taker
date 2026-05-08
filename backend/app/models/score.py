"""
models/score.py — Score Table
==============================
One row per question answered.

This table now supports both:
  1) legacy Phase-2 scoring columns (semantic/keyword/depth/completeness/confidence)
  2) new classical NLP rubric-based scoring (feature breakdown + wrongness penalties)

Relationships:
  - Belongs to one Question  (question_id -> questions.id)
  - Belongs to one Session   (session_id -> sessions.id)
"""

from sqlalchemy import Column, Text, Float
from app.core.database import Base


class Score(Base):
    __tablename__ = "scores"

    # Unique score record ID — generated as a UUID string
    id = Column(Text, primary_key=True)

    # Foreign key: which question this score belongs to
    question_id = Column(Text, nullable=False)

    # Foreign key: which session this score belongs to (denormalised for easy report queries)
    session_id = Column(Text, nullable=False)

    # The raw text of what the student actually said/typed
    student_answer = Column(Text, nullable=True)

    # ---------------------------------------------------------------------
    # Legacy scoring columns (kept temporarily for migration compatibility)
    # ---------------------------------------------------------------------

    # Legacy Pillar 1: semantic similarity score.
    semantic_score = Column(Float, nullable=True)

    # Legacy Pillar 2: keyword coverage score.
    keyword_score = Column(Float, nullable=True)

    # Legacy Pillar 3: answer depth score.
    depth_score = Column(Float, nullable=True)

    # Legacy Pillar 4: completeness score.
    completeness_score = Column(Float, nullable=True)

    # Legacy Pillar 5: confidence score.
    confidence_score = Column(Float, nullable=True)

    # Final score used by adaptive logic and reporting.
    final_score = Column(Float, nullable=True)

    # Full legacy evaluator payload snapshot (optional).
    legacy_score_json = Column(Text, nullable=True)

    # Full grounded evaluator payload snapshot (optional).
    grounded_score_json = Column(Text, nullable=True)

    # Legacy reason fields.
    depth_reason = Column(Text, nullable=True)

    completeness_reason = Column(Text, nullable=True)

    # ---------------------------------------------------------------------
    # New classical NLP scoring columns (rubric-based, explainable)
    # ---------------------------------------------------------------------

    # Explicit versioning helps compare old and new scoring outputs.
    scoring_version = Column(Text, nullable=True)           # e.g. "v2_classical_nlp"
    scoring_mode = Column(Text, nullable=True)              # e.g. "rubric_classical"

    # Raw weighted score before penalties/bonus and post-penalty components.
    raw_weighted_score = Column(Float, nullable=True)
    total_penalty = Column(Float, nullable=True)
    level_bonus_applied = Column(Float, nullable=True)

    # Optional score band used by adaptive flow/UI (strong/partial/weak).
    score_band = Column(Text, nullable=True)

    # JSON blobs for full explainability + auditing.
    feature_breakdown_json = Column(Text, nullable=True)    # per-feature values and evidence
    penalties_json = Column(Text, nullable=True)            # wrongness checks and penalty values
    flags_json = Column(Text, nullable=True)                # contradiction/off-topic/review flags

    # Matched/missing concept and phrase summaries for quick frontend rendering.
    matched_must_concepts_json = Column(Text, nullable=True)
    missing_must_concepts_json = Column(Text, nullable=True)
    matched_optional_concepts_json = Column(Text, nullable=True)
    matched_phrases_json = Column(Text, nullable=True)
    missing_phrases_json = Column(Text, nullable=True)

    # A snapshot of the rubric used for this evaluation (optional but useful for audit).
    rubric_snapshot_json = Column(Text, nullable=True)

    # Short, user-facing explanation fields.
    feedback_summary = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    # Topic under evaluation (denormalized for report grouping).
    topic = Column(Text, nullable=True)

    # Adaptive decision after scoring:
    # "level_up" | "follow_up" | "checkpoint" | "topic_complete" | "session_end" etc.
    adaptive_decision = Column(Text, nullable=True)
