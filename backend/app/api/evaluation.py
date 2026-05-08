"""Phase 7 evaluation API.

This route accepts a batch of labeled answers and returns the metrics used to
validate and calibrate the scoring system.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.pillar3_assessment.phase7_evaluation import build_evaluation_summary


router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


class EvaluationRecord(BaseModel):
    teacher_score: float | None = Field(default=None, ge=0.0, le=10.0)
    legacy_score: float | None = Field(default=None, ge=0.0, le=10.0)
    grounded_score: float | None = Field(default=None, ge=0.0, le=10.0)
    teacher_band: str | None = None
    legacy_band: str | None = None
    grounded_band: str | None = None
    teacher_preference: str | None = None


class EvaluationBatch(BaseModel):
    records: list[EvaluationRecord] = Field(default_factory=list)


@router.post("/summary")
def summarize_evaluation(batch: EvaluationBatch) -> dict[str, Any]:
    """Return evaluation metrics for a batch of labeled answers."""
    return build_evaluation_summary([record.model_dump() for record in batch.records])