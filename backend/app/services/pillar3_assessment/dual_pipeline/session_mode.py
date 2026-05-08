"""Session/question mode helpers for Phase 4 routing."""

from __future__ import annotations

VALID_PIPELINE_MODES = {"legacy_only", "grounded_only", "dual_compare"}

# Existing rows can carry generation tags; map them to compare mode.
MODE_ALIASES = {
    "llm_generated": "dual_compare",
    "grounded_nlp": "dual_compare",
    "rubric_classical": "grounded_only",
}


def normalize_pipeline_mode(mode_value: str | None, default: str = "dual_compare") -> str:
    value = (mode_value or "").strip().lower()
    if value in VALID_PIPELINE_MODES:
        return value
    if value in MODE_ALIASES:
        return MODE_ALIASES[value]
    return default


def resolve_pipeline_mode(session_mode: str | None, question_mode: str | None, default: str = "dual_compare") -> str:
    """Resolve active scoring mode from session/question hints with sane fallback."""
    resolved_session = normalize_pipeline_mode(session_mode, default="")
    if resolved_session:
        return resolved_session

    resolved_question = normalize_pipeline_mode(question_mode, default="")
    if resolved_question:
        return resolved_question

    return default
