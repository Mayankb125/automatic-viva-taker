"""
Deterministic rubric-based evaluator for viva answers (no LLM calls).
"""

from __future__ import annotations

import math
import re

from app.services.pillar3_assessment.grounded_pipeline.answer_preprocess import preprocess_answer
from app.services.pillar3_assessment.grounded_pipeline.concept_matcher import score_concept_features
from app.services.pillar3_assessment.grounded_pipeline.evidence_matcher import score_evidence_features
from app.services.pillar3_assessment.grounded_pipeline.grounded_feedback import build_grounded_feedback
from app.services.pillar3_assessment.grounded_pipeline.grounded_scoring import (
    compute_component_scores,
    finalize_grounded_score,
    fuse_grounded_features,
    quality_score,
)
from app.services.pillar3_assessment.grounded_pipeline.wrongness_checks import evaluate_wrongness

LEVEL_BONUS_PER_LEVEL = 0.5
SWITCH_PENALTY = 1.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+\-]+", (text or "").lower())


def _sentence_split(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if part.strip()]


def _contains_phrase(answer_tokens: list[str], phrase: str) -> bool:
    phrase_tokens = _tokens(phrase)
    if not phrase_tokens or not answer_tokens:
        return False
    if len(phrase_tokens) == 1:
        return phrase_tokens[0] in set(answer_tokens)

    max_i = len(answer_tokens) - len(phrase_tokens) + 1
    if max_i < 1:
        return False

    for i in range(max_i):
        if answer_tokens[i : i + len(phrase_tokens)] == phrase_tokens:
            return True
    return False


def _contains_phrase_in_text(answer_text: str, phrase: str) -> bool:
    phrase_text = (phrase or "").strip().lower()
    if not answer_text or not phrase_text:
        return False
    return phrase_text in answer_text.lower()


def _concept_matched(answer_tokens: list[str], concept: str) -> bool:
    c_tokens = _tokens(concept)
    if not c_tokens:
        return False

    if _contains_phrase(answer_tokens, concept):
        return True

    overlap = len(set(c_tokens).intersection(set(answer_tokens)))
    ratio = overlap / max(1, len(set(c_tokens)))
    return ratio >= 0.6


def _concept_matched_preprocessed(content_tokens: list[str], concept: str, normalized_text: str) -> bool:
    c_tokens = _tokens(concept)
    if not c_tokens:
        return False

    if _contains_phrase_in_text(normalized_text, concept):
        return True

    normalized_set = set(content_tokens)
    overlap = len(set(c_tokens).intersection(normalized_set))
    ratio = overlap / max(1, len(set(c_tokens)))
    return ratio >= 0.6


def _jaccard_similarity(a_tokens: list[str], b_tokens: list[str]) -> float:
    a_set = set(a_tokens)
    b_set = set(b_tokens)
    if not a_set or not b_set:
        return 0.0
    return len(a_set.intersection(b_set)) / len(a_set.union(b_set))


def build_legacy_rubric(expected_answer: str, key_keywords: list[str], key_points: list[str]) -> dict:
    """
    Build a deterministic rubric from legacy generated fields.
    """
    must_concepts = [point.strip() for point in (key_points or []) if (point or "").strip()]
    optional_concepts = [kw.strip() for kw in (key_keywords or []) if (kw or "").strip()]

    if not must_concepts:
        must_concepts = optional_concepts[:4]

    evidence_sentences = _sentence_split(expected_answer)[:4]

    return {
        "must_concepts": must_concepts[:8],
        "optional_concepts": optional_concepts[:12],
        "key_phrases": optional_concepts[:12],
        "evidence_sentences": evidence_sentences,
        "source_chunk_ids": [],
        "rubric_version": "v1_legacy",
        "mode": "classical_nlp",
    }


def evaluate_answer_with_rubric(
    question: str,
    student_answer: str,
    rubric: dict,
    current_level: int = 1,
    switched: bool = False,
) -> dict:
    answer_profile = preprocess_answer(student_answer)

    must_concepts = rubric.get("must_concepts", []) or []
    optional_concepts = rubric.get("optional_concepts", []) or []
    key_phrases = rubric.get("key_phrases", []) or []
    evidence_sentences = rubric.get("evidence_sentences", []) or []

    concept_features = score_concept_features(answer_profile, must_concepts, optional_concepts, key_phrases)
    evidence_features = score_evidence_features(answer_profile, evidence_sentences)
    quality_features = quality_score(answer_profile)
    grounded_proxy = fuse_grounded_features(concept_features, evidence_features, quality_features)
    component_scores = compute_component_scores(concept_features, evidence_features, quality_features)

    semantic_score = component_scores["semantic_score"]
    keyword_score = component_scores["keyword_score"]
    completeness_score = component_scores["completeness_score"]
    depth_score = component_scores["depth_score"]
    confidence_score = component_scores["confidence_score"]

    matched_must = concept_features["matched_must_concepts"]
    missing_must = concept_features["missing_must_concepts"]
    matched_optional = concept_features["matched_optional_concepts"]
    matched_phrases = concept_features["matched_phrases"]
    missing_phrases = concept_features["missing_phrases"]

    must_ratio = concept_features["must_ratio"]
    optional_ratio = concept_features["optional_ratio"]
    phrase_ratio = concept_features["phrase_ratio"]
    evidence_alignment = evidence_features["tfidf_similarity_score"] / 10.0

    answer_text = answer_profile.original_text
    answer_tokens = answer_profile.tokens
    answer_sentences = answer_profile.sentences
    word_count = len(answer_tokens)
    sentence_count = len(answer_sentences)
    connectors = ["because", "therefore", "however", "for example", "hence", "thus", "if", "when"]
    connector_hits = sum(1 for connector in connectors if connector in answer_text.lower())

    filler_patterns = [
        r"\bum\b",
        r"\buh\b",
        r"\bi think\b",
        r"\bnot sure\b",
        r"\bmaybe\b",
        r"\bkind of\b",
        r"\bsort of\b",
    ]
    filler_hits = sum(len(re.findall(pattern, answer_text.lower())) for pattern in filler_patterns)

    wrongness = evaluate_wrongness(
        question=question,
        answer_profile=answer_profile,
        rubric=rubric,
        concept_features=concept_features,
        evidence_features=evidence_features,
    )
    penalties = wrongness["penalties"]
    flags = wrongness["flags"]
    total_penalty = wrongness["total_penalty"]

    final_policy = finalize_grounded_score(
        component_scores=component_scores,
        total_penalty=total_penalty,
        current_level=current_level,
        switched=switched,
        level_bonus_per_level=LEVEL_BONUS_PER_LEVEL,
        switch_penalty_value=SWITCH_PENALTY,
    )
    raw_weighted = final_policy["raw_weighted_score"]
    weighted_score = final_policy["weighted_score"]
    level_bonus = final_policy["level_bonus"]
    switch_penalty = final_policy["switch_penalty"]
    final_score = final_policy["final_score"]
    score_band = final_policy["score_band"]

    depth_reason = (
        f"Length={word_count} words, sentences={sentence_count}, "
        f"reasoning-connectors={connector_hits}."
    )
    completeness_reason = (
        f"Must concepts matched {len(matched_must)}/{len(must_concepts) if must_concepts else 0}; "
        f"optional matched {len(matched_optional)}/{len(optional_concepts) if optional_concepts else 0}."
    )

    grounded_feedback = build_grounded_feedback(score_band, concept_features, penalties)
    feedback_summary = grounded_feedback["feedback_summary"]
    recommendation = grounded_feedback["recommendation"]

    feature_breakdown = {
        "must_ratio": round(must_ratio, 4),
        "optional_ratio": round(optional_ratio, 4),
        "phrase_ratio": round(phrase_ratio, 4),
        "evidence_alignment": round(evidence_alignment, 4),
        "concept_coverage_score": concept_features["concept_coverage_score"],
        "synonym_aware_match_score": concept_features["synonym_aware_match_score"],
        "phrase_match_score": concept_features["phrase_match_score"],
        "tfidf_similarity_score": evidence_features["tfidf_similarity_score"],
        "bm25_relevance_score": evidence_features["bm25_relevance_score"],
        "rouge_recall_score": evidence_features["rouge_recall_score"],
        "ngram_overlap_score": evidence_features["ngram_overlap_score"],
        "discourse_coherence_score": evidence_features["discourse_coherence_score"],
        "quality_score": quality_features["quality_score"],
        "raw_feature_score": grounded_proxy["raw_weighted_score"],
        "raw_policy_score": raw_weighted,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "connector_hits": connector_hits,
        "filler_hits": filler_hits,
        "wrongness_check_count": len([k for k, v in flags.items() if v]),
        "needs_llm_contradiction_check": wrongness["needs_llm_contradiction_check"],
    }

    preprocessing = {
        "original_text": answer_profile.original_text,
        "normalized_text": answer_profile.normalized_text,
        "tokens": answer_profile.tokens,
        "stemmed_tokens": answer_profile.stemmed_tokens,
        "content_tokens": answer_profile.content_tokens,
        "factual_values": answer_profile.factual_values,
        "negated_terms": answer_profile.negated_terms,
        "negated_sentences": answer_profile.negated_sentences,
        "sentence_boundaries": answer_profile.sentences,
    }

    return {
        "semantic_score": semantic_score,
        "keyword_score": keyword_score,
        "depth_score": depth_score,
        "completeness_score": completeness_score,
        "confidence_score": confidence_score,
        "depth_reason": depth_reason,
        "completeness_reason": completeness_reason,
        "weighted_score": weighted_score,
        "raw_weighted_score": round(raw_weighted, 4),
        "total_penalty": total_penalty,
        "level_bonus": level_bonus,
        "switch_penalty": switch_penalty,
        "final_score": final_score,
        "score_band": score_band,
        "feature_breakdown": feature_breakdown,
        "preprocessing": preprocessing,
        "penalties": penalties,
        "flags": flags,
        "wrongness_checks": wrongness["checks"],
        "needs_llm_contradiction_check": wrongness["needs_llm_contradiction_check"],
        "matched_must_concepts": matched_must,
        "missing_must_concepts": missing_must,
        "matched_optional_concepts": matched_optional,
        "matched_phrases": matched_phrases,
        "missing_phrases": missing_phrases,
        "feedback_summary": feedback_summary,
        "recommendation": recommendation,
        "scoring_version": "v2_classical_nlp",
        "scoring_mode": "rubric_classical",
        "question": question,
    }
