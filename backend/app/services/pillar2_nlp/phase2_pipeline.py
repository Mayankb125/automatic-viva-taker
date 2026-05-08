"""
Phase 2 orchestration:
- Ingest + clean source
- Chunk and structure
- Build concept bank and reverse index
- Build/persist lexical indices
- Build rubrics from chunk IDs
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.pillar2_nlp.knowledge_chunking import build_chunks
from app.services.pillar2_nlp.knowledge_concepts import build_concept_bank
from app.services.pillar2_nlp.knowledge_indices import build_indices, load_indices, save_indices
from app.services.pillar2_nlp.knowledge_ingestion import clean_text, extract_pdf_pages_text, extract_raw_text
from app.services.pillar2_nlp.rubric_builder import build_rubric


BACKEND_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = BACKEND_DIR.parent
NLP_ASSETS_DIR = PROJECT_DIR / "data" / "nlp_assets"
NLP_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

PAGE_MATCH_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "are", "was",
    "were", "will", "would", "could", "should", "have", "has", "had", "can", "not",
    "but", "you", "your", "our", "their", "about", "when", "where", "what", "which",
}


def _asset_dir(asset_id: str) -> Path:
    return NLP_ASSETS_DIR / asset_id


def _tokenize_query(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+\-]*", (text or "").lower())


def _tokenize_for_page_match(text: str) -> set[str]:
    return {
        tok
        for tok in _tokenize_query(text)
        if len(tok) > 2 and tok not in PAGE_MATCH_STOPWORDS
    }


def assign_source_page_ranges(chunks: list[dict], pdf_pages_text: list[str]) -> list[dict]:
    """
    Estimate source_page_range per chunk by lexical overlap against PDF pages.

    The result is stored as:
    - "p3" for a single matched page
    - "p3-p5" for a multi-page span
    - "unknown" when no robust match is found
    """
    if not chunks or not pdf_pages_text:
        return chunks

    page_token_sets = [_tokenize_for_page_match(page_text) for page_text in pdf_pages_text]

    for chunk in chunks:
        chunk_tokens = _tokenize_for_page_match(chunk.get("text", ""))
        if not chunk_tokens:
            chunk["source_page_range"] = "unknown"
            continue

        overlaps = [len(chunk_tokens.intersection(page_tokens)) for page_tokens in page_token_sets]
        best_overlap = max(overlaps) if overlaps else 0
        if best_overlap <= 1:
            chunk["source_page_range"] = "unknown"
            continue

        threshold = max(2, int(best_overlap * 0.4))
        matched_pages = [idx + 1 for idx, score in enumerate(overlaps) if score >= threshold]

        if not matched_pages:
            best_idx = overlaps.index(best_overlap)
            matched_pages = [best_idx + 1]

        first_page, last_page = min(matched_pages), max(matched_pages)
        if first_page == last_page:
            chunk["source_page_range"] = f"p{first_page}"
        else:
            chunk["source_page_range"] = f"p{first_page}-p{last_page}"

    return chunks


def _parse_iso(ts: str | None) -> datetime:
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _clean_topic_label(label: str | None) -> str:
    text = (label or "").strip()
    if not text:
        return ""

    text = re.sub(r"^\s*\d+(?:\.\d+)*[\)\.]?\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;,.\t")
    if not text:
        return ""

    lowered = text.lower()
    if lowered in {
        "general",
        "contents",
        "table of contents",
        "acknowledgements",
        "acknowledgments",
    }:
        return ""

    if lowered.startswith("chapter ") or lowered.startswith("appendix "):
        return ""

    return text


def extract_topics_from_bundle(bundle: dict, max_topics: int = 20) -> list[str]:
    """
    Derive teacher-facing topic labels from chunk headings, with a concept-bank fallback.

    The goal is to surface clean PDF-derived topics rather than the static global topic list.
    """
    topics: list[str] = []
    seen: set[str] = set()

    for chunk in bundle.get("chunks", []):
        heading = _clean_topic_label(chunk.get("heading"))
        if not heading:
            continue

        normalized = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
        if not normalized or normalized in seen:
            continue

        if len(heading.split()) > 12:
            continue

        seen.add(normalized)
        topics.append(heading)

    if not topics:
        for concept in bundle.get("concept_bank", {}).get("concepts", []):
            if concept.get("importance") not in {"high", "medium"}:
                continue

            name = _clean_topic_label(concept.get("name"))
            if not name:
                continue

            normalized = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
            if not normalized or normalized in seen:
                continue

            if len(name.split()) > 6:
                continue

            if any(token in name.lower() for token in {"let", "have", "look", "named", "shown", "thing"}):
                continue

            seen.add(normalized)
            topics.append(name)

    return topics[:max_topics]


def find_latest_asset_id(subject: str, topic: str) -> str | None:
    """
    Return the newest asset_id for the given subject/topic, if available.
    """
    subject_norm = (subject or "").strip().lower()
    topic_norm = (topic or "").strip().lower()
    candidates: list[tuple[datetime, str]] = []

    for candidate_dir in NLP_ASSETS_DIR.iterdir():
        if not candidate_dir.is_dir():
            continue
        manifest_path = candidate_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            continue

        if (manifest.get("subject", "").strip().lower() != subject_norm):
            continue
        if (manifest.get("topic", "").strip().lower() != topic_norm):
            continue

        candidates.append((_parse_iso(manifest.get("created_at")), manifest.get("asset_id", candidate_dir.name)))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def select_source_chunks_for_question(asset_id: str, question_text: str, top_k: int = 2) -> list[str]:
    """
    Select top chunk IDs for a question using BM25 retrieval from saved Phase 2 assets.
    """
    bundle = load_asset_bundle(asset_id)
    chunk_ids = bundle["indices"].get("chunk_ids", [])
    chunk_texts = bundle["indices"].get("chunk_texts", [])
    bm25 = bundle["indices"].get("bm25")

    if not chunk_ids:
        return []

    query_tokens = _tokenize_query(question_text)
    if not query_tokens or bm25 is None:
        # Fallback: prefer the first chunk(s) when retrieval cannot run.
        return chunk_ids[: max(1, top_k)]

    scores = bm25.get_scores(query_tokens)
    ranked_idx = sorted(
        range(len(chunk_ids)),
        key=lambda i: (float(scores[i]), len(chunk_texts[i]) if i < len(chunk_texts) else 0),
        reverse=True,
    )

    selected = [chunk_ids[i] for i in ranked_idx[: max(1, top_k)] if i < len(chunk_ids)]
    return selected or chunk_ids[: max(1, top_k)]


def build_phase2_assets(
    subject: str,
    topic: str,
    source_file_path: str | None = None,
    raw_text: str | None = None,
    asset_id: str | None = None,
) -> dict:
    if not source_file_path and not raw_text:
        raise ValueError("Provide source_file_path or raw_text")

    resolved_asset_id = asset_id or str(uuid4())
    asset_dir = _asset_dir(resolved_asset_id)
    asset_dir.mkdir(parents=True, exist_ok=True)

    extraction_mode = "inline_text"
    source_path_value = None
    pdf_pages_text: list[str] = []

    if source_file_path:
        source_path = Path(source_file_path)
        source_path_value = str(source_path)
        extracted_raw, extraction_mode = extract_raw_text(str(source_path))

        if source_path.suffix.lower() == ".pdf":
            try:
                pdf_pages_text, _ = extract_pdf_pages_text(
                    str(source_path),
                    enable_ocr_fallback=(extraction_mode == "pdf_ocr"),
                )
            except Exception:
                pdf_pages_text = []
    else:
        extracted_raw = raw_text or ""

    cleaned = clean_text(extracted_raw)
    chunks = build_chunks(cleaned, subject=subject, topic=topic)
    if pdf_pages_text:
        chunks = assign_source_page_ranges(chunks, pdf_pages_text)

    concept_bank, reverse_index = build_concept_bank(chunks, topic=topic)
    indices = build_indices(chunks)
    save_indices(asset_dir, indices)

    with (asset_dir / "raw_text.txt").open("w", encoding="utf-8") as f:
        f.write(extracted_raw)

    with (asset_dir / "clean_text.txt").open("w", encoding="utf-8") as f:
        f.write(cleaned)

    with (asset_dir / "chunks.json").open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    with (asset_dir / "concept_bank.json").open("w", encoding="utf-8") as f:
        json.dump(concept_bank, f, ensure_ascii=False, indent=2)

    with (asset_dir / "reverse_index.json").open("w", encoding="utf-8") as f:
        json.dump(reverse_index, f, ensure_ascii=False, indent=2)

    manifest = {
        "asset_id": resolved_asset_id,
        "subject": subject,
        "topic": topic,
        "source_file_path": source_path_value,
        "extraction_mode": extraction_mode,
        "chunk_count": len(chunks),
        "concept_count": len(concept_bank.get("concepts", [])),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with (asset_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {
        **manifest,
        "chunk_ids": [c["chunk_id"] for c in chunks],
    }


def load_asset_bundle(asset_id: str) -> dict:
    asset_dir = _asset_dir(asset_id)
    if not asset_dir.exists():
        raise FileNotFoundError(f"Asset not found: {asset_id}")

    with (asset_dir / "manifest.json").open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    with (asset_dir / "chunks.json").open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    with (asset_dir / "concept_bank.json").open("r", encoding="utf-8") as f:
        concept_bank = json.load(f)

    with (asset_dir / "reverse_index.json").open("r", encoding="utf-8") as f:
        reverse_index = json.load(f)

    indices = load_indices(asset_dir)

    return {
        "manifest": manifest,
        "chunks": chunks,
        "concept_bank": concept_bank,
        "reverse_index": reverse_index,
        "indices": indices,
        "asset_dir": str(asset_dir),
    }


def build_rubric_for_asset(asset_id: str, source_chunk_ids: list[str], evidence_count: int = 4) -> dict:
    bundle = load_asset_bundle(asset_id)
    rubric = build_rubric(
        source_chunk_ids=source_chunk_ids,
        chunks=bundle["chunks"],
        concept_bank=bundle["concept_bank"],
        phrase_index=bundle["indices"]["phrase_index"],
        evidence_count=evidence_count,
    )

    # Keep a trace file for generated rubrics by asset.
    rubric_dir = Path(bundle["asset_dir"]) / "rubrics"
    rubric_dir.mkdir(parents=True, exist_ok=True)
    rubric_id = str(uuid4())
    with (rubric_dir / f"{rubric_id}.json").open("w", encoding="utf-8") as f:
        json.dump(rubric, f, ensure_ascii=False, indent=2)

    return rubric
