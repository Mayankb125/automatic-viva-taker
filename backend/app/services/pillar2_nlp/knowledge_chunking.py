"""
Phase 2.2 - Chunking and topic structuring.

Strategy:
- Split by heading boundaries when possible
- Chunk into ~150-300 words
- Merge tiny chunks
- Add last-sentence overlap from previous chunk
"""

from __future__ import annotations

import re


TARGET_MIN_WORDS = 150
TARGET_MAX_WORDS = 300
SMALL_CHUNK_WORDS = 50


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):
        return True
    if re.match(r"^\d+(\.\d+)*[\)\.]?\s+", s):
        return True
    words = s.split()
    if len(words) <= 8 and s.upper() == s and re.search(r"[A-Z]", s):
        return True
    return False


def _split_sections(clean_text: str) -> list[tuple[str, str]]:
    lines = clean_text.split("\n")
    current_heading = "General"
    buf: list[str] = []
    sections: list[tuple[str, str]] = []

    for ln in lines:
        if _is_heading(ln):
            if buf:
                sections.append((current_heading, "\n".join(buf).strip()))
                buf = []
            current_heading = ln.strip("# ").strip() or "General"
        else:
            buf.append(ln)

    if buf:
        sections.append((current_heading, "\n".join(buf).strip()))
    return [(h, t) for h, t in sections if t]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _paragraphs(section_text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", section_text)
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]


def _chunk_long_paragraph(paragraph: str) -> list[str]:
    wc = _word_count(paragraph)
    if wc <= TARGET_MAX_WORDS:
        return [paragraph]

    sentences = _split_sentences(paragraph)
    chunks: list[str] = []
    cur: list[str] = []
    cur_words = 0
    for sent in sentences:
        sw = _word_count(sent)
        if cur and cur_words + sw > TARGET_MAX_WORDS:
            chunks.append(" ".join(cur).strip())
            cur = []
            cur_words = 0
        cur.append(sent)
        cur_words += sw

    if cur:
        chunks.append(" ".join(cur).strip())
    return chunks


def build_chunks(clean_text: str, subject: str, topic: str) -> list[dict]:
    """Return chunk dicts with metadata required by Phase 2."""
    sections = _split_sections(clean_text)

    raw_chunks: list[dict] = []
    idx = 1

    for heading, sec_text in sections:
        paras = _paragraphs(sec_text)
        normalized: list[str] = []
        for para in paras:
            normalized.extend(_chunk_long_paragraph(para))

        cur_parts: list[str] = []
        cur_words = 0

        for para in normalized:
            pw = _word_count(para)
            if cur_parts and cur_words + pw > TARGET_MAX_WORDS:
                chunk_text = "\n\n".join(cur_parts).strip()
                raw_chunks.append(
                    {
                        "chunk_id": f"chunk_{idx}",
                        "subject": subject,
                        "topic": topic,
                        "heading": heading,
                        "text": chunk_text,
                        "word_count": _word_count(chunk_text),
                        "source_page_range": "unknown",
                    }
                )
                idx += 1
                cur_parts = []
                cur_words = 0

            cur_parts.append(para)
            cur_words += pw

            if cur_words >= TARGET_MIN_WORDS:
                chunk_text = "\n\n".join(cur_parts).strip()
                raw_chunks.append(
                    {
                        "chunk_id": f"chunk_{idx}",
                        "subject": subject,
                        "topic": topic,
                        "heading": heading,
                        "text": chunk_text,
                        "word_count": _word_count(chunk_text),
                        "source_page_range": "unknown",
                    }
                )
                idx += 1
                cur_parts = []
                cur_words = 0

        if cur_parts:
            chunk_text = "\n\n".join(cur_parts).strip()
            raw_chunks.append(
                {
                    "chunk_id": f"chunk_{idx}",
                    "subject": subject,
                    "topic": topic,
                    "heading": heading,
                    "text": chunk_text,
                    "word_count": _word_count(chunk_text),
                    "source_page_range": "unknown",
                }
            )
            idx += 1

    # Merge tiny chunks with predecessor when possible.
    merged: list[dict] = []
    for ch in raw_chunks:
        if merged and ch["word_count"] < SMALL_CHUNK_WORDS:
            merged[-1]["text"] = (merged[-1]["text"] + "\n\n" + ch["text"]).strip()
            merged[-1]["word_count"] = _word_count(merged[-1]["text"])
        else:
            merged.append(ch)

    # Add overlap: prepend last sentence from previous chunk.
    final_chunks: list[dict] = []
    prev_last_sentence = ""
    for ch in merged:
        text = ch["text"].strip()
        if prev_last_sentence and prev_last_sentence not in text:
            text = (prev_last_sentence + " " + text).strip()

        sents = _split_sentences(text)
        prev_last_sentence = sents[-1] if sents else ""

        item = dict(ch)
        item["text"] = text
        item["word_count"] = _word_count(text)
        final_chunks.append(item)

    # Re-number chunk IDs after merges/overlap.
    for i, ch in enumerate(final_chunks, start=1):
        ch["chunk_id"] = f"chunk_{i}"

    return final_chunks
