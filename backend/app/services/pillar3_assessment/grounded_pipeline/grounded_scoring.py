"""
Grounded score fusion helpers for Step 3.3.
"""

from __future__ import annotations

from app.services.pillar3_assessment.grounded_pipeline.answer_preprocess import PreprocessedAnswer


WEIGHTS = {
    "semantic": 0.35,
    "keyword": 0.20,
    "completeness": 0.20,
    "depth": 0.15,
    "confidence": 0.10,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def quality_score(answer_profile: PreprocessedAnswer) -> dict:
    word_count = len(answer_profile.content_tokens)
    unique_count = len(set(answer_profile.content_tokens))
    sentence_count = len(answer_profile.sentences)

    length_score = min(1.0, word_count / 90.0)
    diversity_score = 0.0 if word_count == 0 else min(1.0, unique_count / word_count)
    structure_score = min(1.0, sentence_count / 4.0)

    score = round((0.40 * length_score + 0.35 * diversity_score + 0.25 * structure_score) * 10.0, 4)

    return {
        "quality_score": score,
        "length_score": round(length_score * 10.0, 4),
        "diversity_score": round(diversity_score * 10.0, 4),
        "structure_score": round(structure_score * 10.0, 4),
    }


def fuse_grounded_features(concept_features: dict, evidence_features: dict, quality_features: dict) -> dict:
    """
    Build a deterministic raw score from grounded feature outputs.
    Step 3.5 can later add penalties/bonus/clamping on top of this.
    """
    semantic_proxy = (
        0.40 * concept_features.get("concept_coverage_score", 0.0)
        + 0.35 * evidence_features.get("tfidf_similarity_score", 0.0)
        + 0.25 * evidence_features.get("bm25_relevance_score", 0.0)
    )

    keyword_proxy = (
        0.60 * concept_features.get("phrase_match_score", 0.0)
        + 0.40 * evidence_features.get("rouge_recall_score", 0.0)
    )

    completeness_proxy = (
        0.45 * concept_features.get("concept_coverage_score", 0.0)
        + 0.30 * concept_features.get("synonym_aware_match_score", 0.0)
        + 0.25 * concept_features.get("phrase_match_score", 0.0)
    )

    depth_proxy = (
        0.55 * evidence_features.get("discourse_coherence_score", 0.0)
        + 0.45 * quality_features.get("quality_score", 0.0)
    )

    confidence_proxy = quality_features.get("quality_score", 0.0)

    raw_weighted_score = (
        semantic_proxy * 0.35
        + keyword_proxy * 0.20
        + completeness_proxy * 0.20
        + depth_proxy * 0.15
        + confidence_proxy * 0.10
    )

    return {
        "semantic_proxy": round(semantic_proxy, 4),
        "keyword_proxy": round(keyword_proxy, 4),
        "completeness_proxy": round(completeness_proxy, 4),
        "depth_proxy": round(depth_proxy, 4),
        "confidence_proxy": round(confidence_proxy, 4),
        "raw_weighted_score": round(raw_weighted_score, 4),
    }


def compute_component_scores(concept_features: dict, evidence_features: dict, quality_features: dict) -> dict:
    """Compute 0-10 grounded component scores from extracted features."""
    semantic_score = _clamp(
        0.40 * concept_features.get("concept_coverage_score", 0.0)
        + 0.35 * evidence_features.get("tfidf_similarity_score", 0.0)
        + 0.25 * evidence_features.get("bm25_relevance_score", 0.0),
        0.0,
        10.0,
    )

    keyword_score = _clamp(
        0.60 * concept_features.get("phrase_match_score", 0.0)
        + 0.40 * evidence_features.get("rouge_recall_score", 0.0),
        0.0,
        10.0,
    )

    completeness_score = _clamp(
        0.45 * concept_features.get("concept_coverage_score", 0.0)
        + 0.30 * concept_features.get("synonym_aware_match_score", 0.0)
        + 0.25 * concept_features.get("phrase_match_score", 0.0),
        0.0,
        10.0,
    )

    depth_score = _clamp(
        0.55 * evidence_features.get("discourse_coherence_score", 0.0)
        + 0.45 * quality_features.get("quality_score", 0.0),
        0.0,
        10.0,
    )

    confidence_score = _clamp(quality_features.get("quality_score", 0.0), 0.0, 10.0)

    return {
        "semantic_score": round(semantic_score, 4),
        "keyword_score": round(keyword_score, 4),
        "completeness_score": round(completeness_score, 4),
        "depth_score": round(depth_score, 4),
        "confidence_score": round(confidence_score, 4),
    }


def finalize_grounded_score(
    component_scores: dict,
    total_penalty: float,
    current_level: int = 1,
    switched: bool = False,
    level_bonus_per_level: float = 0.5,
    switch_penalty_value: float = 1.0,
) -> dict:
    """
    Step 3.5 policy: weighted fusion -> penalties -> level/switch adjustment -> clamp.
    """
    raw_weighted_score = (
        component_scores.get("semantic_score", 0.0) * WEIGHTS["semantic"]
        + component_scores.get("keyword_score", 0.0) * WEIGHTS["keyword"]
        + component_scores.get("completeness_score", 0.0) * WEIGHTS["completeness"]
        + component_scores.get("depth_score", 0.0) * WEIGHTS["depth"]
        + component_scores.get("confidence_score", 0.0) * WEIGHTS["confidence"]
    )

    weighted_score = _clamp(raw_weighted_score - float(total_penalty), 0.0, 10.0)

    level_bonus = max(0.0, (int(current_level) - 1) * level_bonus_per_level)
    switch_penalty = switch_penalty_value if switched else 0.0
    final_score = _clamp(weighted_score + level_bonus - switch_penalty, 0.0, 10.0)

    if final_score >= 7.0:
        score_band = "strong"
    elif final_score >= 4.5:
        score_band = "partial"
    else:
        score_band = "weak"

    return {
        "raw_weighted_score": round(raw_weighted_score, 4),
        "weighted_score": round(weighted_score, 4),
        "level_bonus": round(level_bonus, 4),
        "switch_penalty": round(switch_penalty, 4),
        "final_score": round(final_score, 4),
        "score_band": score_band,
    }
