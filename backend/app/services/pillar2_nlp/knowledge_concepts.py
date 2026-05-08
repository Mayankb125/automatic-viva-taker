"""
Phase 2.3 - Concept bank and reverse index builder.

Deterministic, rule-based extraction without LLM calls.
"""

from __future__ import annotations

import re


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
    "with", "this", "these", "those", "or", "not", "if", "then", "than", "into", "their",
    "there", "which", "what", "when", "where", "who", "why", "how", "can", "could", "should",
    "would", "do", "does", "did", "also", "such", "may", "might", "we", "you", "they",
}

CONNECTOR_WORDS = {"of", "for", "in", "to", "with"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+\-]*", text.lower())


def _normalize_phrase(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    return cleaned


def _ngrams(tokens: list[str], n: int) -> list[str]:
    grams: list[str] = []
    for i in range(0, len(tokens) - n + 1):
        g = tokens[i:i + n]
        if g[0] in STOPWORDS or g[-1] in STOPWORDS:
            continue
        grams.append(" ".join(g))
    return grams


def _connector_phrases(tokens: list[str]) -> list[str]:
    phrases: list[str] = []
    for i in range(1, len(tokens) - 1):
        if tokens[i] not in CONNECTOR_WORDS:
            continue
        left = tokens[i - 1]
        right = tokens[i + 1]
        if left in STOPWORDS or right in STOPWORDS:
            continue
        phrases.append(f"{left} {tokens[i]} {right}")
    return phrases


def _extract_parenthetical_aliases(text: str) -> dict[str, set[str]]:
    """Extract aliases like 'binary search tree (BST)' from chunk text."""
    alias_map: dict[str, set[str]] = {}
    pattern = re.compile(r"\b([A-Za-z][A-Za-z0-9\- ]{3,80}?)\s*\(([A-Za-z][A-Za-z0-9\-]{1,20})\)")
    for full_term, short_term in pattern.findall(text):
        canonical = _normalize_phrase(full_term)
        short = short_term.strip()
        if not canonical or not short:
            continue
        alias_map.setdefault(canonical, set()).add(short)
    return alias_map


def _acronym(phrase: str) -> str | None:
    parts = [p for p in phrase.split() if p]
    if len(parts) < 2:
        return None
    ac = "".join(p[0].upper() for p in parts if p[0].isalpha())
    if len(ac) < 2:
        return None
    return ac


def _importance_by_count(count: int, spread: int) -> str:
    if count >= 4 or spread >= 3:
        return "high"
    if count >= 2 or spread >= 2:
        return "medium"
    return "low"


def build_concept_bank(chunks: list[dict], topic: str) -> tuple[dict, dict]:
    """
    Returns (concept_bank, reverse_index).

    concept_bank schema:
    {
      "topic": "...",
      "concepts": [{"name":..., "aliases": [...], "importance":..., "chunk_ids": [...]}]
    }
    """
    concept_counts: dict[str, int] = {}
    concept_chunks: dict[str, set[str]] = {}
    observed_aliases: dict[str, set[str]] = {}

    for ch in chunks:
        chunk_id = ch["chunk_id"]
        text = ch["text"]
        tokens = _tokenize(text)
        local_aliases = _extract_parenthetical_aliases(text)
        for canonical, aliases in local_aliases.items():
            observed_aliases.setdefault(canonical, set()).update(aliases)

        # Candidate concepts from bigrams and trigrams.
        candidates = _ngrams(tokens, 2) + _ngrams(tokens, 3) + _connector_phrases(tokens)

        # Add selected technical unigrams with enough signal.
        unigram_counts: dict[str, int] = {}
        for token in tokens:
            if token in STOPWORDS or len(token) < 5:
                continue
            unigram_counts[token] = unigram_counts.get(token, 0) + 1
        candidates.extend([term for term, freq in unigram_counts.items() if freq >= 2])

        # Add title-cased entities as high-signal terms.
        entities = re.findall(r"\b(?:[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)+)\b", text)
        candidates.extend(e.lower() for e in entities)

        # Keep only non-trivial phrases.
        filtered = []
        for c in candidates:
            c = _normalize_phrase(c)
            if len(c) < 4:
                continue
            if c in STOPWORDS:
                continue
            filtered.append(c)

        for phrase in filtered:
            concept_counts[phrase] = concept_counts.get(phrase, 0) + 1
            concept_chunks.setdefault(phrase, set()).add(chunk_id)

    concepts = []
    reverse_index: dict[str, list[str]] = {}

    # Keep top concepts by frequency with deterministic ordering.
    ranked = sorted(concept_counts.items(), key=lambda item: (-item[1], item[0]))
    for phrase, cnt in ranked[:300]:
        aliases: list[str] = []

        # Basic plural/singular variants.
        if phrase.endswith("s"):
            aliases.append(phrase[:-1])
        else:
            aliases.append(phrase + "s")

        # Acronym alias if available.
        ac = _acronym(phrase)
        if ac:
            aliases.append(ac)

        # Hyphen/space variants.
        if "-" in phrase:
            aliases.append(phrase.replace("-", " "))
        if " " in phrase:
            aliases.append(phrase.replace(" ", "-"))

        # Observed aliases from source text e.g., Full Term (FT).
        aliases.extend(sorted(observed_aliases.get(phrase, set())))

        # Remove duplicates and self-aliasing.
        aliases = sorted({a for a in aliases if a and a != phrase})

        chunk_ids = sorted(concept_chunks.get(phrase, set()))
        reverse_index[phrase] = chunk_ids

        concepts.append(
            {
                "name": phrase,
                "aliases": aliases,
                "importance": _importance_by_count(cnt, len(chunk_ids)),
                "chunk_ids": chunk_ids,
                "frequency": cnt,
            }
        )

    concept_bank = {
        "topic": topic,
        "concepts": concepts,
    }
    return concept_bank, reverse_index
