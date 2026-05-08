"""
Step 3.4 wrongness validation for grounded scoring.

This module applies deterministic checks that detect common forms of
incorrect but fluent answers. It returns explainable penalties that can
be consumed by the grounded evaluator.
"""

from __future__ import annotations

import re

from app.services.pillar3_assessment.grounded_pipeline.answer_preprocess import PreprocessedAnswer, STOPWORDS


ANTONYM_PAIRS = {
    "increase": "decrease",
    "higher": "lower",
    "high": "low",
    "enable": "disable",
    "enabled": "disabled",
    "allow": "prevent",
    "true": "false",
    "positive": "negative",
    "accept": "reject",
    "synchronous": "asynchronous",
}


# Minimal directional relation templates used to detect A->B vs B->A reversals.
RELATION_PATTERNS = (
    r"\b([a-z][a-z0-9\-]*)\s+(?:causes?|leads to|produces|depends on|requires?)\s+([a-z][a-z0-9\-]*)\b",
)


def _tokens(text: str) -> list[str]:
    """Normalize and tokenize text for rule-based checks."""
    return re.findall(r"[a-z0-9][a-z0-9+\-./%]*", (text or "").lower())


def _extract_values(text: str) -> set[str]:
    """Extract numeric/scalar anchors (numbers, percentages, Big-O style terms)."""
    values = set(re.findall(r"\b\d+(?:\.\d+)?(?:e[+-]?\d+)?%?\b", text or "", flags=re.IGNORECASE))
    values.update(re.sub(r"\s+", "", value) for value in re.findall(r"o\s*\(\s*[^)]+\s*\)", text or "", flags=re.IGNORECASE))
    return {value.lower() for value in values if value}


def _content_terms(phrase: str) -> set[str]:
    """Return informative tokens only (stopwords removed)."""
    return {token for token in _tokens(phrase) if token not in STOPWORDS and len(token) > 1}


def _detect_negation_conflict(answer_profile: PreprocessedAnswer, concept_features: dict) -> dict:
    # If a matched concept is explicitly negated, treat it as likely conceptual wrongness.
    negated = set(answer_profile.negated_terms)
    if not negated:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No negation conflict."}

    conflicts: list[str] = []
    for concept in concept_features.get("matched_must_concepts", []) + concept_features.get("matched_optional_concepts", []):
        c_terms = _content_terms(concept)
        if c_terms.intersection(negated):
            conflicts.append(concept)

    if not conflicts:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No negation conflict."}

    return {
        "triggered": True,
        "penalty": 1.2,
        "evidence": sorted(set(conflicts))[:5],
        "reason": "Negation appears on concept terms that were otherwise matched.",
    }


def _detect_antonym_conflict(answer_profile: PreprocessedAnswer, concept_features: dict) -> dict:
    # Detect polarity inversion (e.g., concept says increase while answer says decrease).
    answer_terms = set(answer_profile.content_tokens)
    matched_concepts = concept_features.get("matched_must_concepts", []) + concept_features.get("matched_optional_concepts", [])

    conflicts: list[str] = []
    for concept in matched_concepts:
        concept_terms = _content_terms(concept)
        for left, right in ANTONYM_PAIRS.items():
            if left in concept_terms and right in answer_terms:
                conflicts.append(f"{left}<->{right}")
            if right in concept_terms and left in answer_terms:
                conflicts.append(f"{right}<->{left}")

    if not conflicts:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No antonym conflict."}

    return {
        "triggered": True,
        "penalty": 0.9,
        "evidence": sorted(set(conflicts))[:5],
        "reason": "Answer includes antonyms that invert matched concept meaning.",
    }


def _detect_factual_value_mismatch(answer_profile: PreprocessedAnswer, rubric: dict) -> dict:
    # Compare numeric/symbolic anchors in rubric evidence vs answer values.
    # Trigger only when both sides have values but there is no overlap.
    expected_values = _extract_values(" ".join(rubric.get("evidence_sentences", []) or []))
    if not expected_values:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No rubric factual anchors found."}

    actual_values = set(answer_profile.factual_values)
    if not actual_values:
        return {
            "triggered": False,
            "penalty": 0.0,
            "evidence": [],
            "reason": "No factual values in student answer.",
        }

    overlap = expected_values.intersection(actual_values)
    if overlap:
        return {"triggered": False, "penalty": 0.0, "evidence": sorted(overlap), "reason": "Factual values overlap with rubric evidence."}

    return {
        "triggered": True,
        "penalty": 1.0,
        "evidence": [f"expected={sorted(expected_values)[:4]}", f"actual={sorted(actual_values)[:4]}"],
        "reason": "Numeric or symbolic factual values do not match rubric evidence anchors.",
    }


def _extract_relations(text: str) -> set[tuple[str, str]]:
    """Extract lightweight directed relations from text using regex patterns."""
    relations: set[tuple[str, str]] = set()
    raw = (text or "").lower()
    for pattern in RELATION_PATTERNS:
        for left, right in re.findall(pattern, raw):
            if left and right:
                relations.add((left, right))
    return relations


def _detect_relationship_reversal(answer_profile: PreprocessedAnswer, rubric: dict) -> dict:
    # If evidence contains A->B and answer contains only B->A, mark reversal.
    evidence_relations = _extract_relations(" ".join(rubric.get("evidence_sentences", []) or []))
    if not evidence_relations:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No directional relations found in evidence."}

    answer_relations = _extract_relations(answer_profile.normalized_text)
    reversals: list[str] = []
    for left, right in evidence_relations:
        if (right, left) in answer_relations and (left, right) not in answer_relations:
            reversals.append(f"{left}->{right} reversed as {right}->{left}")

    if not reversals:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No relation reversal detected."}

    return {
        "triggered": True,
        "penalty": 1.0,
        "evidence": reversals[:5],
        "reason": "Answer reverses directional relationships from rubric evidence.",
    }


def _detect_internal_contradiction(answer_profile: PreprocessedAnswer) -> dict:
    # Heuristic: two semantically overlapping sentences with opposite negation polarity.
    if len(answer_profile.sentences) < 2:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "Single sentence answer."}

    contradictions: list[str] = []
    for sentence in answer_profile.sentences:
        s_tokens = _tokens(sentence)
        content = {token for token in s_tokens if token not in STOPWORDS and len(token) > 1}
        if not content:
            continue
        has_neg = any(token in {"not", "never", "no"} for token in s_tokens)
        for other in answer_profile.sentences:
            if other == sentence:
                continue
            o_tokens = _tokens(other)
            o_content = {token for token in o_tokens if token not in STOPWORDS and len(token) > 1}
            if not o_content:
                continue
            overlap = len(content.intersection(o_content)) / max(1, len(content.union(o_content)))
            if overlap < 0.35:
                continue
            other_has_neg = any(token in {"not", "never", "no"} for token in o_tokens)
            if has_neg != other_has_neg:
                contradictions.append(f"{sentence} || {other}")

    if not contradictions:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No internal contradiction detected."}

    return {
        "triggered": True,
        "penalty": 0.8,
        "evidence": contradictions[:2],
        "reason": "Answer contains potentially contradictory sentence pairs.",
    }


def _detect_off_topic(concept_features: dict, evidence_features: dict, question: str, answer_profile: PreprocessedAnswer) -> dict:
    # Conservative off-topic gate requiring multiple weak-alignment signals.
    must_ratio = float(concept_features.get("must_ratio", 0.0))
    phrase_ratio = float(concept_features.get("phrase_ratio", 0.0))
    tfidf = float(evidence_features.get("tfidf_similarity_score", 0.0)) / 10.0
    question_terms = _content_terms(question)
    answer_terms = set(answer_profile.content_tokens)
    query_overlap = len(question_terms.intersection(answer_terms)) / max(1, len(question_terms)) if question_terms else 0.0

    off_topic = must_ratio < 0.20 and phrase_ratio < 0.20 and tfidf < 0.12 and query_overlap < 0.20
    if not off_topic:
        return {"triggered": False, "penalty": 0.0, "evidence": [], "reason": "No off-topic condition."}

    return {
        "triggered": True,
        "penalty": 1.1,
        "evidence": [
            f"must_ratio={must_ratio:.2f}",
            f"phrase_ratio={phrase_ratio:.2f}",
            f"tfidf={tfidf:.2f}",
            f"question_overlap={query_overlap:.2f}",
        ],
        "reason": "Answer has very low rubric and question alignment.",
    }


def evaluate_wrongness(
    *,
    question: str,
    answer_profile: PreprocessedAnswer,
    rubric: dict,
    concept_features: dict,
    evidence_features: dict,
) -> dict:
    """Run all Step 3.4 deterministic wrongness checks and aggregate penalties."""
    checks = {
        "negation_conflict": _detect_negation_conflict(answer_profile, concept_features),
        "antonym_conflict": _detect_antonym_conflict(answer_profile, concept_features),
        "factual_value_mismatch": _detect_factual_value_mismatch(answer_profile, rubric),
        "relationship_reversal": _detect_relationship_reversal(answer_profile, rubric),
        "internal_contradiction": _detect_internal_contradiction(answer_profile),
        "off_topic": _detect_off_topic(concept_features, evidence_features, question, answer_profile),
    }

    penalties: list[dict] = []
    flags: dict[str, bool] = {}
    for name, result in checks.items():
        triggered = bool(result.get("triggered", False))
        flags[name] = triggered
        if triggered:
            # Keep a flat, explainable penalty structure for downstream reporting/UI.
            penalties.append(
                {
                    "name": name,
                    "value": float(result.get("penalty", 0.0)),
                    "reason": result.get("reason", "Wrongness condition triggered."),
                    "evidence": result.get("evidence", []),
                }
            )

    # Optional Step 3.4 fallback trigger. We do not call an LLM here.
    triggered_count = sum(1 for value in flags.values() if value)
    needs_llm_contradiction_check = (
        flags.get("internal_contradiction", False)
        and not flags.get("factual_value_mismatch", False)
        and triggered_count == 1
    )

    return {
        "penalties": penalties,
        "total_penalty": round(sum(item["value"] for item in penalties), 4),
        "flags": flags,
        "checks": checks,
        "needs_llm_contradiction_check": needs_llm_contradiction_check,
    }
