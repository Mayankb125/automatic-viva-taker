"""
Grounded evidence matching features for Step 3.3.
"""

from __future__ import annotations

import math
from collections import Counter

from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.pillar3_assessment.grounded_pipeline.answer_preprocess import PreprocessedAnswer, STOPWORDS


def _tokenize(text: str) -> list[str]:
    return [token for token in (text or "").lower().split() if token]


def _content_words(text: str) -> list[str]:
    tokens = [token for token in _tokenize(text) if token not in STOPWORDS]
    return tokens


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))


def _normalize_scores(scores: list[float]) -> float:
    if not scores:
        return 0.0
    best = max(scores)
    if best <= 0.0:
        return 0.0
    return best / (best + 1.0)


def score_evidence_features(answer_profile: PreprocessedAnswer, evidence_sentences: list[str]) -> dict:
    answer_text = answer_profile.normalized_text or answer_profile.original_text
    answer_tokens = _content_words(answer_text)
    answer_token_set = set(answer_tokens)

    if not evidence_sentences:
        return {
            "tfidf_similarity_score": 0.0,
            "bm25_relevance_score": 0.0,
            "rouge_recall_score": 0.0,
            "ngram_overlap_score": 0.0,
            "discourse_coherence_score": 0.0,
        }

    # TF-IDF similarity against each evidence sentence, taking the best match.
    corpus = [answer_text] + [sentence or "" for sentence in evidence_sentences]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus)
    answer_vector = matrix[0]
    tfidf_scores: list[float] = []
    for idx in range(1, matrix.shape[0]):
        similarity = float((answer_vector @ matrix[idx].T).toarray()[0][0])
        tfidf_scores.append(max(0.0, similarity))
    tfidf_similarity = _normalize_scores(tfidf_scores) * 10.0

    tokenized_evidence = [_content_words(sentence) for sentence in evidence_sentences]
    bm25 = BM25Okapi(tokenized_evidence)
    bm25_scores = bm25.get_scores(answer_tokens)
    bm25_relevance = _normalize_scores([float(score) for score in bm25_scores]) * 10.0

    rouge_scores: list[float] = []
    for sentence_tokens in tokenized_evidence:
        evidence_set = set(sentence_tokens)
        rouge_scores.append(_jaccard(answer_token_set, evidence_set))
    rouge_recall = _normalize_scores(rouge_scores) * 10.0

    answer_ngrams = set(_ngrams(answer_tokens, 2) + _ngrams(answer_tokens, 3))
    ngram_scores: list[float] = []
    for sentence_tokens in tokenized_evidence:
        evidence_ngrams = set(_ngrams(sentence_tokens, 2) + _ngrams(sentence_tokens, 3))
        ngram_scores.append(_jaccard(answer_ngrams, evidence_ngrams))
    ngram_overlap = _normalize_scores(ngram_scores) * 10.0

    sentence_count = len(answer_profile.sentences)
    connector_hits = sum(
        1 for token in ["because", "therefore", "however", "for example", "thus", "hence", "if", "when"]
        if token in answer_text.lower()
    )
    length_factor = min(1.0, len(answer_tokens) / 90.0)
    structure_factor = min(1.0, sentence_count / 4.0)
    connector_factor = min(1.0, connector_hits / 3.0)
    discourse_coherence = round((0.40 * length_factor + 0.35 * structure_factor + 0.25 * connector_factor) * 10.0, 4)

    return {
        "tfidf_similarity_score": round(tfidf_similarity, 4),
        "bm25_relevance_score": round(bm25_relevance, 4),
        "rouge_recall_score": round(rouge_recall, 4),
        "ngram_overlap_score": round(ngram_overlap, 4),
        "discourse_coherence_score": discourse_coherence,
    }
