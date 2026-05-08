"""
Phase 2.4 - Lexical indices (TF-IDF, BM25, phrase index) with persistence.
"""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+\-]*", text.lower())


def build_indices(chunks: list[dict]) -> dict:
    chunk_texts = [ch["text"] for ch in chunks]
    chunk_ids = [ch["chunk_id"] for ch in chunks]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        min_df=1,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(chunk_texts)

    tokenized_chunks = [_tokenize(text) for text in chunk_texts]
    bm25 = BM25Okapi(tokenized_chunks)

    # Weighted phrase index from frequent bigrams/trigrams per chunk.
    phrase_index: dict[str, dict] = {}
    for ch in chunks:
        text_tokens = _tokenize(ch["text"])
        local_counts: dict[str, int] = {}
        for n in (2, 3):
            for i in range(0, len(text_tokens) - n + 1):
                phrase = " ".join(text_tokens[i:i + n])
                local_counts[phrase] = local_counts.get(phrase, 0) + 1

        for phrase, freq in local_counts.items():
            entry = phrase_index.setdefault(
                phrase,
                {"weight": 0.0, "chunk_ids": set()},
            )
            entry["weight"] += float(freq)
            entry["chunk_ids"].add(ch["chunk_id"])

    for phrase, entry in phrase_index.items():
        entry["chunk_ids"] = sorted(entry["chunk_ids"])

    return {
        "chunk_ids": chunk_ids,
        "chunk_texts": chunk_texts,
        "tfidf_vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "bm25": bm25,
        "phrase_index": phrase_index,
    }


def save_indices(asset_dir: Path, indices: dict) -> None:
    asset_dir.mkdir(parents=True, exist_ok=True)

    with (asset_dir / "tfidf_vectorizer.pkl").open("wb") as f:
        pickle.dump(indices["tfidf_vectorizer"], f)

    with (asset_dir / "tfidf_matrix.pkl").open("wb") as f:
        pickle.dump(indices["tfidf_matrix"], f)

    with (asset_dir / "bm25.pkl").open("wb") as f:
        pickle.dump(indices["bm25"], f)

    with (asset_dir / "chunk_texts.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "chunk_ids": indices["chunk_ids"],
                "chunk_texts": indices["chunk_texts"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with (asset_dir / "phrase_index.json").open("w", encoding="utf-8") as f:
        json.dump(indices["phrase_index"], f, ensure_ascii=False, indent=2)


def load_indices(asset_dir: Path) -> dict:
    with (asset_dir / "tfidf_vectorizer.pkl").open("rb") as f:
        vectorizer = pickle.load(f)

    with (asset_dir / "tfidf_matrix.pkl").open("rb") as f:
        tfidf_matrix = pickle.load(f)

    with (asset_dir / "bm25.pkl").open("rb") as f:
        bm25 = pickle.load(f)

    with (asset_dir / "chunk_texts.json").open("r", encoding="utf-8") as f:
        chunk_blob = json.load(f)

    with (asset_dir / "phrase_index.json").open("r", encoding="utf-8") as f:
        phrase_index = json.load(f)

    return {
        "tfidf_vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "bm25": bm25,
        "chunk_ids": chunk_blob["chunk_ids"],
        "chunk_texts": chunk_blob["chunk_texts"],
        "phrase_index": phrase_index,
    }
