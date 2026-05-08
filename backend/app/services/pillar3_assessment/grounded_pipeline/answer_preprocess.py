"""
Grounded answer preprocessing utilities.

Step 3.2 keeps the answer in both original and normalized forms, extracts
content-bearing tokens and factual values, and marks simple negation scope
at sentence level for downstream grounded scoring.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
    "with", "this", "these", "those", "or", "not", "if", "then", "than", "into", "their",
    "there", "which", "what", "when", "where", "who", "why", "how", "can", "could", "should",
    "would", "do", "does", "did", "also", "such", "may", "might", "we", "you", "they",
    "i", "am", "been", "being", "but", "so", "because", "therefore", "however",
}

NEGATION_WORDS = {
    "not", "no", "never", "none", "cannot", "can't", "don't", "doesn't", "didn't",
    "isn't", "aren't", "wasn't", "weren't", "without", "neither", "nor",
}


@dataclass(frozen=True)
class PreprocessedAnswer:
    original_text: str
    normalized_text: str
    sentences: list[str]
    tokens: list[str]
    stemmed_tokens: list[str]
    content_tokens: list[str]
    factual_values: list[str]
    negated_terms: list[str]
    negated_sentences: list[str]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [part.strip() for part in parts if part.strip()]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = text.lower()
    text = re.sub(r"[^a-z0-9+\-./%\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+\-./%]*", text.lower())


def _stem_token(token: str) -> str:
    if len(token) <= 3:
        return token

    suffix_rules = (
        ("ization", "ize"),
        ("ational", "ate"),
        ("fulness", "ful"),
        ("iveness", "ive"),
        ("ousness", "ous"),
        ("tional", "tion"),
        ("biliti", "ble"),
        ("less", "less"),
        ("edly", "e"),
        ("ingly", "e"),
        ("ing", ""),
        ("edly", ""),
        ("edly", ""),
        ("ed", ""),
        ("ly", ""),
        ("ies", "y"),
        ("es", ""),
        ("s", ""),
    )

    for suffix, replacement in suffix_rules:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)] + replacement
    return token


def _extract_factual_values(text: str) -> list[str]:
    values: list[str] = []

    for match in re.findall(r"\b\d+(?:\.\d+)?(?:e[+-]?\d+)?%?\b", text, flags=re.IGNORECASE):
        values.append(match.lower())

    for match in re.findall(r"o\s*\(\s*[^)]+\s*\)", text, flags=re.IGNORECASE):
        values.append(re.sub(r"\s+", "", match.lower()))

    for match in re.findall(r"\b(?:\d+\s*[xX]\s*)?\d+\b", text):
        if match not in values:
            values.append(match.lower())

    return sorted({value for value in values if value})


def _detect_negation_scope(sentences: list[str]) -> tuple[list[str], list[str]]:
    negated_terms: set[str] = set()
    negated_sentences: list[str] = []

    for sentence in sentences:
        tokens = _tokenize(sentence)
        if not tokens:
            continue

        sentence_negated = False
        for idx, token in enumerate(tokens):
            if token in NEGATION_WORDS:
                sentence_negated = True
                window = tokens[idx + 1: idx + 6]
                for window_token in window:
                    if window_token not in STOPWORDS:
                        negated_terms.add(window_token)

        if sentence_negated:
            negated_sentences.append(sentence)

    return sorted(negated_terms), negated_sentences


def preprocess_answer(answer_text: str) -> PreprocessedAnswer:
    original_text = (answer_text or "").strip()
    normalized_text = _normalize(original_text)
    sentences = _split_sentences(original_text)
    tokens = _tokenize(normalized_text)
    stemmed_tokens = [_stem_token(token) for token in tokens]
    content_tokens = [token for token in stemmed_tokens if token not in STOPWORDS and len(token) > 1]
    factual_values = _extract_factual_values(original_text)
    negated_terms, negated_sentences = _detect_negation_scope(sentences)

    return PreprocessedAnswer(
        original_text=original_text,
        normalized_text=normalized_text,
        sentences=sentences,
        tokens=tokens,
        stemmed_tokens=stemmed_tokens,
        content_tokens=content_tokens,
        factual_values=factual_values,
        negated_terms=negated_terms,
        negated_sentences=negated_sentences,
    )
