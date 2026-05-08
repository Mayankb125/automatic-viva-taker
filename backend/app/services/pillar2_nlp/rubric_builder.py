"""
Phase 2.5 - Rubric builder (no LLM).

Builds must/optional concepts, key phrases, and evidence sentences from
selected source chunks.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z][A-Za-z0-9+\-]*", text.lower()))


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _sentence_similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    overlap = len(ta.intersection(tb))
    denom = math.sqrt(len(ta) * len(tb))
    return overlap / denom if denom else 0.0


def _textrank_sentences(sentences: list[str], top_k: int) -> list[str]:
    if not sentences:
        return []
    n = len(sentences)
    if n <= top_k:
        return sentences

    damping = 0.85
    scores = [1.0 for _ in range(n)]

    sim = [[0.0 for _ in range(n)] for _ in range(n)]
    out_sum = [0.0 for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            s = _sentence_similarity(sentences[i], sentences[j])
            sim[i][j] = s
            out_sum[i] += s

    for _ in range(25):
        new_scores = [(1.0 - damping) for _ in range(n)]
        for i in range(n):
            acc = 0.0
            for j in range(n):
                if i == j or out_sum[j] == 0.0:
                    continue
                acc += (sim[j][i] / out_sum[j]) * scores[j]
            new_scores[i] += damping * acc
        scores = new_scores

    ranked_idx = sorted(range(n), key=lambda i: scores[i], reverse=True)[:top_k]
    ranked_idx = sorted(ranked_idx)  # preserve source order for readability
    return [sentences[i] for i in ranked_idx]


def build_rubric(
    source_chunk_ids: list[str],
    chunks: list[dict],
    concept_bank: dict,
    phrase_index: dict,
    evidence_count: int = 4,
) -> dict:
    chunk_map = {ch["chunk_id"]: ch for ch in chunks}
    selected_chunks = [chunk_map[cid] for cid in source_chunk_ids if cid in chunk_map]

    if not selected_chunks:
        raise ValueError("No valid source chunks found for rubric construction")

    selected_set = {ch["chunk_id"] for ch in selected_chunks}

    ranked_concepts: list[dict] = []
    for c in concept_bank.get("concepts", []):
        overlap = selected_set.intersection(set(c.get("chunk_ids", [])))
        if not overlap:
            continue
        ranked_concepts.append(
            {
                "name": c["name"],
                "importance": c.get("importance", "low"),
                "aliases": c.get("aliases", []),
                "frequency": c.get("frequency", 1),
                "overlap_count": len(overlap),
            }
        )

    ranked_concepts.sort(
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(item["importance"], 3),
            -item["overlap_count"],
            -item["frequency"],
            item["name"],
        )
    )

    must_concepts = [c["name"] for c in ranked_concepts if c["importance"] == "high"][:8]
    if not must_concepts:
        must_concepts = [c["name"] for c in ranked_concepts[:6]]
    optional_concepts = [
        c["name"]
        for c in ranked_concepts
        if c["name"] not in must_concepts
    ][:12]

    phrase_items = []
    for phrase, info in phrase_index.items():
        chunk_ids = set(info.get("chunk_ids", []))
        if not selected_set.intersection(chunk_ids):
            continue
        phrase_items.append((phrase, float(info.get("weight", 0.0))))

    phrase_items.sort(key=lambda item: (-item[1], item[0]))
    key_phrases = [p for p, _ in phrase_items[:15]]

    text_blob = "\n".join(ch["text"] for ch in selected_chunks)
    sentences = _split_sentences(text_blob)
    evidence_sentences = _textrank_sentences(sentences, top_k=evidence_count)

    return {
        "must_concepts": must_concepts,
        "optional_concepts": optional_concepts,
        "key_phrases": key_phrases,
        "evidence_sentences": evidence_sentences,
        "source_chunk_ids": [ch["chunk_id"] for ch in selected_chunks],
        "rubric_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "classical_nlp",
    }
