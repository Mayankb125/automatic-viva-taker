"""Dual-pipeline routing and result merge helpers for Phase 4."""

from app.services.pillar3_assessment.dual_pipeline.pipeline_router import select_active_mode_result
from app.services.pillar3_assessment.dual_pipeline.result_merger import (
    build_api_response_payload,
    build_legacy_active_result,
    build_legacy_breakdown,
    build_legacy_feedback,
    build_score_row_payload,
)
from app.services.pillar3_assessment.dual_pipeline.session_mode import resolve_pipeline_mode

__all__ = [
    "resolve_pipeline_mode",
    "select_active_mode_result",
    "build_legacy_feedback",
    "build_legacy_breakdown",
    "build_legacy_active_result",
    "build_score_row_payload",
    "build_api_response_payload",
]
