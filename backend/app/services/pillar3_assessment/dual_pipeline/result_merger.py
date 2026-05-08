"""Legacy/grounded payload normalization and merge helpers."""

from __future__ import annotations



def _legacy_band(score: float) -> str:
    if score >= 7.0:
        return "strong"
    if score >= 4.5:
        return "partial"
    return "weak"


def build_legacy_feedback(legacy_result: dict) -> dict:
    score_band = _legacy_band(float(legacy_result.get("final_score", 0.0)))
    summary = (
        f"Band: {score_band}. Depth: {legacy_result.get('depth_reason', 'n/a')} "
        f"Completeness: {legacy_result.get('completeness_reason', 'n/a')}"
    )

    if score_band == "strong":
        recommendation = "Strong answer. Keep your explanation structured and precise."
    elif score_band == "partial":
        recommendation = "Good direction. Add missing concepts and one concrete example."
    else:
        recommendation = "Answer needs stronger concept coverage and clearer reasoning."

    return {
        "depth_reason": legacy_result.get("depth_reason", ""),
        "completeness_reason": legacy_result.get("completeness_reason", ""),
        "summary": summary,
        "recommendation": recommendation,
    }


def build_legacy_breakdown(legacy_result: dict) -> dict:
    return {
        "semantic_score": legacy_result.get("semantic_score", 0.0),
        "keyword_score": legacy_result.get("keyword_score", 0.0),
        "depth_score": legacy_result.get("depth_score", 0.0),
        "completeness_score": legacy_result.get("completeness_score", 0.0),
        "confidence_score": legacy_result.get("confidence_score", 0.0),
        "weighted_score": legacy_result.get("weighted_score", 0.0),
        "level_bonus": legacy_result.get("level_bonus", 0.0),
        "switch_penalty": legacy_result.get("switch_penalty", 0.0),
        "final_score": legacy_result.get("final_score", 0.0),
    }


def build_legacy_active_result(legacy_result: dict) -> dict:
    final_score = float(legacy_result.get("final_score", 0.0))
    return {
        "mode": "legacy_only",
        "final_score": final_score,
        "score_band": _legacy_band(final_score),
        "score_breakdown": build_legacy_breakdown(legacy_result),
        "feedback": build_legacy_feedback(legacy_result),
    }


def build_grounded_active_result(grounded_result: dict) -> dict:
    return {
        "mode": "grounded_only",
        "final_score": grounded_result.get("final_score", 0.0),
        "score_band": grounded_result.get("score_band", "weak"),
        "score_breakdown": {
            "semantic_score": grounded_result.get("semantic_score", 0.0),
            "keyword_score": grounded_result.get("keyword_score", 0.0),
            "depth_score": grounded_result.get("depth_score", 0.0),
            "completeness_score": grounded_result.get("completeness_score", 0.0),
            "confidence_score": grounded_result.get("confidence_score", 0.0),
            "weighted_score": grounded_result.get("weighted_score", 0.0),
            "level_bonus": grounded_result.get("level_bonus", 0.0),
            "switch_penalty": grounded_result.get("switch_penalty", 0.0),
            "final_score": grounded_result.get("final_score", 0.0),
        },
        "feedback": {
            "depth_reason": grounded_result.get("depth_reason", ""),
            "completeness_reason": grounded_result.get("completeness_reason", ""),
            "summary": grounded_result.get("feedback_summary", ""),
            "recommendation": grounded_result.get("recommendation", ""),
        },
    }


def build_score_row_payload(
    *,
    pipeline_mode: str,
    active_mode_result: dict,
    legacy_result: dict,
    grounded_result: dict,
) -> dict:
    active_score_breakdown = active_mode_result["score_breakdown"]
    active_is_grounded = active_mode_result["mode"] == "grounded_only"

    return {
        "semantic_score": active_score_breakdown["semantic_score"],
        "keyword_score": active_score_breakdown["keyword_score"],
        "depth_score": active_score_breakdown["depth_score"],
        "completeness_score": active_score_breakdown["completeness_score"],
        "confidence_score": active_score_breakdown["confidence_score"],
        "final_score": active_mode_result["final_score"],
        "depth_reason": active_mode_result["feedback"]["depth_reason"],
        "completeness_reason": active_mode_result["feedback"]["completeness_reason"],
        "scoring_version": grounded_result.get("scoring_version", "v2_classical_nlp") if active_is_grounded else "v1_legacy",
        "scoring_mode": pipeline_mode,
        "raw_weighted_score": grounded_result.get("raw_weighted_score", 0.0) if active_is_grounded else active_score_breakdown["weighted_score"],
        "total_penalty": grounded_result.get("total_penalty", 0.0) if active_is_grounded else 0.0,
        "level_bonus_applied": active_score_breakdown["level_bonus"],
        "score_band": active_mode_result["score_band"],
        "legacy_score_json": legacy_result,
        "grounded_score_json": grounded_result,
        "feature_breakdown_json": grounded_result.get("feature_breakdown", {}),
        "penalties_json": grounded_result.get("penalties", []),
        "flags_json": grounded_result.get("flags", {}),
        "matched_must_concepts_json": grounded_result.get("matched_must_concepts", []),
        "missing_must_concepts_json": grounded_result.get("missing_must_concepts", []),
        "matched_optional_concepts_json": grounded_result.get("matched_optional_concepts", []),
        "matched_phrases_json": grounded_result.get("matched_phrases", []),
        "missing_phrases_json": grounded_result.get("missing_phrases", []),
        "feedback_summary": active_mode_result["feedback"]["summary"],
        "recommendation": active_mode_result["feedback"]["recommendation"],
    }


def build_api_response_payload(
    *,
    compare_mode_enabled: bool,
    transcribed_text: str,
    pipeline_mode: str,
    legacy_result: dict,
    grounded_result: dict,
    active_mode_result: dict,
    updated_state: dict,
) -> dict:
    """Build API response with optional side-by-side comparison view."""
    response = {
        "transcribed_text": transcribed_text,
        "pipeline_mode": pipeline_mode,
        "compare_mode_enabled": compare_mode_enabled,
        "active_mode_result": active_mode_result,
        # Backward-compatible fields for current frontend.
        "score_breakdown": active_mode_result["score_breakdown"],
        "feedback": active_mode_result["feedback"],
        "adaptive": {
            "decision": updated_state.get("decision"),
            "show_topic_modal": updated_state.get("show_topic_modal"),
            "current_topic": updated_state.get("current_topic"),
            "current_level": updated_state.get("current_level"),
            "total_questions": updated_state.get("total_questions_asked"),
        },
    }

    # Add side-by-side comparison view when enabled
    if compare_mode_enabled and legacy_result and grounded_result:
        response["comparison"] = {
            "legacy": {
                "score": legacy_result.get("final_score", 0.0),
                "band": _legacy_band(legacy_result.get("final_score", 0.0)),
                "breakdown": build_legacy_breakdown(legacy_result),
                "feedback": build_legacy_feedback(legacy_result),
            },
            "grounded": {
                "score": grounded_result.get("final_score", 0.0),
                "band": grounded_result.get("score_band", "weak"),
                "breakdown": {
                    "semantic_score": grounded_result.get("semantic_score", 0.0),
                    "keyword_score": grounded_result.get("keyword_score", 0.0),
                    "depth_score": grounded_result.get("depth_score", 0.0),
                    "completeness_score": grounded_result.get("completeness_score", 0.0),
                    "confidence_score": grounded_result.get("confidence_score", 0.0),
                    "weighted_score": grounded_result.get("weighted_score", 0.0),
                    "level_bonus": grounded_result.get("level_bonus", 0.0),
                    "switch_penalty": grounded_result.get("switch_penalty", 0.0),
                    "final_score": grounded_result.get("final_score", 0.0),
                },
                "feedback": {
                    "depth_reason": grounded_result.get("depth_reason", ""),
                    "completeness_reason": grounded_result.get("completeness_reason", ""),
                    "summary": grounded_result.get("feedback_summary", ""),
                    "recommendation": grounded_result.get("recommendation", ""),
                },
                "feature_breakdown": grounded_result.get("feature_breakdown", {}),
                "penalties": grounded_result.get("penalties", []),
                "flags": grounded_result.get("flags", {}),
            },
            "difference": {
                "score_delta": round(grounded_result.get("final_score", 0.0) - legacy_result.get("final_score", 0.0), 2),
                "higher_score": "grounded" if grounded_result.get("final_score", 0.0) > legacy_result.get("final_score", 0.0) else "legacy" if legacy_result.get("final_score", 0.0) > grounded_result.get("final_score", 0.0) else "equal",
            },
        }

    return response
