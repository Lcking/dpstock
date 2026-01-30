"""
AI Score Models (Spec v1.0)

This module defines the structured ai_score output schema that will be embedded into:
- top-level analyze response chunks (for frontend rendering)
- analysis_v1.ai_score (for archival/structured payload)
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


AiScoreDimensionId = Literal["structure", "relative", "flow", "risk"]


class AiScoreContribItem(BaseModel):
    key: str
    value: Any = None
    impact: float = Field(..., description="Impact on overall score (weighted, signed)")
    note: str = ""


class AiScoreDimension(BaseModel):
    id: AiScoreDimensionId
    name: str
    score: int = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)

    contrib: List[AiScoreContribItem] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)

    available: bool = True
    degraded: bool = False


class AiScoreOverall(BaseModel):
    score: int = Field(..., ge=0, le=100)
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    degraded: bool = False


class AiScoreExplain(BaseModel):
    one_liner: str = ""
    notes: List[str] = Field(default_factory=list)


class AiScore(BaseModel):
    version: str = Field(default="1.0.0")
    overall: AiScoreOverall
    dimensions: List[AiScoreDimension]
    explain: AiScoreExplain

    # optional debug/meta if we ever need it
    meta: Optional[Dict[str, Any]] = None

