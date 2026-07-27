"""Shared state passed between LangGraph nodes."""
from __future__ import annotations

from typing import Annotated, Any, TypedDict


def _merge_list(left: list | None, right: list | None) -> list:
    """Reducer so parallel branches can each append to the trace without clobbering."""
    return (left or []) + (right or [])


class AgentState(TypedDict, total=False):
    # Inputs
    raw_text: str
    filename: str | None
    known_complaints: list[dict]

    # parse / extract
    normalised_text: str
    fields: dict[str, Any]
    field_confidence: dict[str, float]

    # completeness
    completeness_score: int
    missing_fields: list[str]
    completeness_notes: str

    # risk
    risk_level: str
    risk_score: int
    risk_rationale: str
    regulatory_reportable: bool
    suggested_severity: str
    suggested_priority: str

    # duplicates
    duplicate_candidates: list[dict]

    # investigation
    root_causes: list[dict]
    capa_recommendations: list[dict]
    summary: str

    # bookkeeping
    trace: Annotated[list[dict], _merge_list]
    engines: Annotated[list[str], _merge_list]
    models_used: dict[str, str]
