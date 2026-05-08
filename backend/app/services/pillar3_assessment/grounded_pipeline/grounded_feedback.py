"""
Grounded feedback formatting for Step 3.3.
"""

from __future__ import annotations


def build_grounded_feedback(
    score_band: str,
    concept_features: dict,
    penalties: list[dict] | None = None,
) -> dict:
    penalties = penalties or []
    missing_must = concept_features.get("missing_must_concepts", [])
    missing_phrases = concept_features.get("missing_phrases", [])

    if score_band == "strong":
        recommendation = "Strong answer. Keep using explicit domain terms and concrete examples."
    elif score_band == "partial":
        recommendation = "Good direction. Add the missing core concepts and one supporting example."
    else:
        recommendation = "Answer needs more rubric-aligned concepts and clearer evidence from the source material."

    summary_parts = [
        f"Band: {score_band}.",
        f"Missing must concepts: {len(missing_must)}.",
        f"Missing phrases: {len(missing_phrases)}.",
    ]

    if penalties:
        summary_parts.append(f"Penalties: {', '.join(item.get('name', 'unknown') for item in penalties)}.")

    return {
        "feedback_summary": " ".join(summary_parts),
        "recommendation": recommendation,
        "missing_must_concepts": missing_must,
        "missing_phrases": missing_phrases,
    }
