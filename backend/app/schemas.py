"""Pydantic request/response models."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    ComplaintSource,
    ComplaintStatus,
    ComplaintType,
    Priority,
    Severity,
)


class ComplaintBase(BaseModel):
    complaint_source: ComplaintSource | None = None
    customer_name: str | None = None
    customer_contact: str | None = None

    product_name: str | None = None
    product_strength: str | None = None
    batch_number: str | None = None
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    quantity_affected: float | None = None
    quantity_unit: str | None = "kg"

    complaint_type: ComplaintType | None = None
    complaint_date: date | None = None
    description: str | None = None

    severity: Severity | None = None
    priority: Priority | None = None


class ComplaintCreate(ComplaintBase):
    """Payload the form posts on Save Complaint."""

    analysis: "AnalysisPayload | None" = None
    source_text: str | None = None
    source_filename: str | None = None


class ComplaintUpdate(ComplaintBase):
    status: ComplaintStatus | None = None


class AnalysisPayload(BaseModel):
    """AI analysis as returned by /intake/extract, echoed back on save."""

    model_config = ConfigDict(extra="ignore")

    engine: str = "heuristic"
    models_used: dict | None = None
    extracted_fields: dict | None = None
    field_confidence: dict | None = None
    completeness_score: int | None = None
    missing_fields: list | None = None
    completeness_notes: str | None = None
    risk_level: str | None = None
    risk_score: int | None = None
    risk_rationale: str | None = None
    regulatory_reportable: bool | None = None
    duplicate_candidates: list | None = None
    root_causes: list | None = None
    capa_recommendations: list | None = None
    summary: str | None = None
    trace: list | None = None


class AnalysisOut(AnalysisPayload):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    created_at: datetime


class ComplaintOut(ComplaintBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_number: str
    status: ComplaintStatus
    created_at: datetime
    updated_at: datetime
    latest_analysis: AnalysisOut | None = None


class ComplaintListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    complaint_number: str
    customer_name: str | None
    product_name: str | None
    batch_number: str | None
    complaint_type: ComplaintType | None
    severity: Severity | None
    priority: Priority | None
    status: ComplaintStatus
    complaint_date: date | None
    created_at: datetime


class ExtractRequest(BaseModel):
    """Paste-text intake."""

    text: str = Field(min_length=10)
    filename: str | None = None


class ExtractResponse(BaseModel):
    raw_text: str
    filename: str | None = None
    form: dict
    analysis: AnalysisPayload


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    complaint_id: int | None = None
    context_text: str | None = None
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    engine: str


class DashboardStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    by_type: dict[str, int]
    open_critical: int
    avg_completeness: float | None


ComplaintCreate.model_rebuild()
