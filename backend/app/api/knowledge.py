"""
api/knowledge.py - Phase 2 knowledge ingestion and rubric APIs.

These routes support professor-side asset creation from source material
and deterministic rubric generation without LLM scoring.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.pillar2_nlp.phase2_pipeline import (
    NLP_ASSETS_DIR,
    build_phase2_assets,
    build_rubric_for_asset,
    extract_topics_from_bundle,
    load_asset_bundle,
)
from app.services.pillar2_nlp.knowledge_ingestion import get_ocr_environment_status


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class BuildFromPathRequest(BaseModel):
    subject: str
    topic: str
    source_file_path: str
    asset_id: str | None = None


class BuildFromTextRequest(BaseModel):
    subject: str
    topic: str
    raw_text: str
    asset_id: str | None = None


class RubricRequest(BaseModel):
    asset_id: str
    source_chunk_ids: list[str] = Field(min_length=1)
    evidence_count: int = Field(default=4, ge=1, le=10)


@router.post("/build-from-path")
def build_from_path(body: BuildFromPathRequest):
    try:
        return build_phase2_assets(
            subject=body.subject,
            topic=body.topic,
            source_file_path=body.source_file_path,
            asset_id=body.asset_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/build-from-text")
def build_from_text(body: BuildFromTextRequest):
    try:
        return build_phase2_assets(
            subject=body.subject,
            topic=body.topic,
            raw_text=body.raw_text,
            asset_id=body.asset_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload")
async def upload_and_build(
    subject: str = Form(...),
    topic: str = Form(...),
    source_file: UploadFile = File(...),
):
    suffix = Path(source_file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Upload PDF, DOCX, TXT, or MD")

    asset_id = str(uuid4())
    upload_dir = NLP_ASSETS_DIR / asset_id / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(source_file.filename or f"source{suffix}").name
    target_path = upload_dir / safe_name

    data = await source_file.read()
    target_path.write_bytes(data)

    try:
        return build_phase2_assets(
            subject=subject,
            topic=topic,
            source_file_path=str(target_path),
            asset_id=asset_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/rubric")
def build_rubric(body: RubricRequest):
    try:
        rubric = build_rubric_for_asset(
            asset_id=body.asset_id,
            source_chunk_ids=body.source_chunk_ids,
            evidence_count=body.evidence_count,
        )
        return {"asset_id": body.asset_id, "rubric": rubric}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/health/ocr")
def get_ocr_health():
    return get_ocr_environment_status()


@router.get("/{asset_id}")
def get_asset_summary(asset_id: str):
    try:
        bundle = load_asset_bundle(asset_id)
        return {
            "asset_id": asset_id,
            "manifest": bundle["manifest"],
            "chunk_count": len(bundle["chunks"]),
            "concept_count": len(bundle["concept_bank"].get("concepts", [])),
            "sample_chunk_ids": [c["chunk_id"] for c in bundle["chunks"][:10]],
            "extracted_topics": extract_topics_from_bundle(bundle),
            "chunk_preview": [
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "heading": chunk.get("heading"),
                    "word_count": chunk.get("word_count"),
                    "source_page_range": chunk.get("source_page_range"),
                    "text": chunk.get("text"),
                }
                for chunk in bundle["chunks"]
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
