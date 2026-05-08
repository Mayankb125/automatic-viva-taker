"""Dual-pipeline active-mode router for Phase 4."""

from __future__ import annotations

from app.services.pillar3_assessment.dual_pipeline.result_merger import (
    build_grounded_active_result,
    build_legacy_active_result,
)


def select_active_mode_result(
    *,
    pipeline_mode: str,
    legacy_result: dict,
    grounded_result: dict,
    dual_compare_policy: str = "score_max",
) -> dict:
    """
    Choose active mode output for adaptive decisions.

    Policies when pipeline_mode=dual_compare:
    - score_max: pick higher final_score
    - grounded_preferred: always grounded
    - legacy_preferred: always legacy
    """
    legacy_active = build_legacy_active_result(legacy_result)
    grounded_active = build_grounded_active_result(grounded_result)

    if pipeline_mode == "legacy_only":
        return legacy_active
    if pipeline_mode == "grounded_only":
        return grounded_active

    if dual_compare_policy == "grounded_preferred":
        return grounded_active
    if dual_compare_policy == "legacy_preferred":
        return legacy_active

    if float(grounded_active["final_score"]) >= float(legacy_active["final_score"]):
        return grounded_active
    return legacy_active
