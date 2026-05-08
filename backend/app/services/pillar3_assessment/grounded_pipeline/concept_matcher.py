"""
Grounded concept matching features for Step 3.3.
"""

from __future__ import annotations

from dataclasses import asdict

from app.services.pillar3_assessment.grounded_pipeline.answer_preprocess import PreprocessedAnswer


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    phrase_text = (phrase or "").strip().lower()
    if not normalized_text or not phrase_text:
        return False
    return phrase_text in normalized_text


def _token_ratio(answer_tokens: set[str], concept: str) -> float:
    concept_tokens = {token for token in concept.lower().split() if token}
    if not concept_tokens:
        return 0.0

    overlap = len(concept_tokens.intersection(answer_tokens))
    return overlap / max(1, len(concept_tokens))


def score_concept_features(
    answer_profile: PreprocessedAnswer,
    must_concepts: list[str],
    optional_concepts: list[str],
    key_phrases: list[str],
) -> dict:
    answer_tokens = set(answer_profile.content_tokens)
    normalized_text = answer_profile.normalized_text

    matched_must = [concept for concept in must_concepts if _contains_phrase(normalized_text, concept) or _token_ratio(answer_tokens, concept) >= 0.6]
    missing_must = [concept for concept in must_concepts if concept not in matched_must]

    matched_optional = [concept for concept in optional_concepts if _contains_phrase(normalized_text, concept) or _token_ratio(answer_tokens, concept) >= 0.55]
    missing_optional = [concept for concept in optional_concepts if concept not in matched_optional]

    matched_phrases = [phrase for phrase in key_phrases if _contains_phrase(normalized_text, phrase)]
    missing_phrases = [phrase for phrase in key_phrases if phrase not in matched_phrases]

    must_ratio = len(matched_must) / max(1, len(must_concepts)) if must_concepts else 1.0
    optional_ratio = len(matched_optional) / max(1, len(optional_concepts)) if optional_concepts else 1.0
    phrase_ratio = len(matched_phrases) / max(1, len(key_phrases)) if key_phrases else 1.0

    synonym_aware_hits = 0.0
    synonym_denominator = 0
    for concept in must_concepts + optional_concepts:
        concept_tokens = {token for token in concept.lower().split() if token}
        if not concept_tokens:
            continue
        synonym_denominator += 1
        token_overlap = len(concept_tokens.intersection(answer_tokens)) / len(concept_tokens)
        phrase_bonus = 1.0 if _contains_phrase(normalized_text, concept) else 0.0
        synonym_aware_hits += max(token_overlap, phrase_bonus)

    synonym_aware_match = synonym_aware_hits / max(1, synonym_denominator)

    return {
        "must_ratio": round(must_ratio, 4),
        "optional_ratio": round(optional_ratio, 4),
        "phrase_ratio": round(phrase_ratio, 4),
        "concept_coverage_score": round(must_ratio * 10.0, 4),
        "synonym_aware_match_score": round(synonym_aware_match * 10.0, 4),
        "phrase_match_score": round(phrase_ratio * 10.0, 4),
        "matched_must_concepts": matched_must,
        "missing_must_concepts": missing_must,
        "matched_optional_concepts": matched_optional,
        "missing_optional_concepts": missing_optional,
        "matched_phrases": matched_phrases,
        "missing_phrases": missing_phrases,
    }


def build_concept_summary(features: dict) -> dict:
    return {
        "matched_must_concepts": features.get("matched_must_concepts", []),
        "missing_must_concepts": features.get("missing_must_concepts", []),
        "matched_optional_concepts": features.get("matched_optional_concepts", []),
        "missing_optional_concepts": features.get("missing_optional_concepts", []),
        "matched_phrases": features.get("matched_phrases", []),
        "missing_phrases": features.get("missing_phrases", []),
    }
