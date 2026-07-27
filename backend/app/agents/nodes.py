"""LangGraph node implementations.

Each node pairs an LLM prompt with a deterministic fallback from
:mod:`app.agents.heuristics`, records which engine actually produced the result,
and returns only the slice of state it owns.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from app.agents import heuristics, prompts
from app.agents.llm import chat_json, chat_text
from app.agents.state import AgentState
from app.config import get_settings

settings = get_settings()

EXTRACTION_MODEL = settings.groq_extraction_model
REASONING_MODEL = settings.groq_reasoning_model

VALID_SOURCES = {
    "Email", "Phone", "Customer Portal", "Field Alert",
    "Distributor", "Regulatory Body", "Sales Representative", "Other",
}
VALID_TYPES = {
    "Product Quality", "Packaging Defect", "Labelling Error", "Contamination",
    "Adverse Event", "Lack of Efficacy", "Appearance / Physical Defect",
    "Quantity / Shortage", "Documentation Discrepancy", "Other",
}
VALID_SEVERITY = {"Critical", "Major", "Minor"}
VALID_PRIORITY = {"P1 - Urgent", "P2 - High", "P3 - Medium", "P4 - Low"}
VALID_RISK = {"Low", "Medium", "High", "Critical"}

FIELD_KEYS = [
    "complaint_source", "customer_name", "customer_contact",
    "product_name", "product_strength", "batch_number",
    "manufacturing_date", "expiry_date", "quantity_affected", "quantity_unit",
    "complaint_type", "complaint_date", "description",
]


def _trace(node: str, engine: str, started: float, note: str = "") -> dict:
    return {
        "node": node,
        "engine": engine,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "note": note,
    }


def _context(state: AgentState) -> str:
    """Compact context block reused by the downstream reasoning nodes."""
    fields = {k: v for k, v in (state.get("fields") or {}).items() if v not in (None, "")}
    return (
        f"EXTRACTED COMPLAINT RECORD:\n{json.dumps(fields, indent=2, default=str)}\n\n"
        f"ORIGINAL DOCUMENT (truncated):\n{(state.get('normalised_text') or '')[:4000]}"
    )


# --------------------------------------------------------------------------
# 1. Normalise
# --------------------------------------------------------------------------


def normalise_document(state: AgentState) -> dict:
    started = time.perf_counter()
    text = state.get("raw_text") or ""

    # Strip quoted email chains and signature blocks so extraction sees the complaint,
    # not the reply history.
    text = re.sub(r"\n>+[^\n]*", "", text)
    text = re.sub(r"\n-{2,}\s*(original message|forwarded message)[^\n]*\n.*", "", text, flags=re.I | re.S)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return {
        "normalised_text": text,
        "trace": [_trace("normalise", "deterministic", started, f"{len(text)} chars normalised")],
    }


# --------------------------------------------------------------------------
# 2. Extract
# --------------------------------------------------------------------------


def _coerce_fields(raw: dict) -> tuple[dict, dict]:
    fields_in = raw.get("fields") if isinstance(raw.get("fields"), dict) else raw
    conf_in = raw.get("confidence") if isinstance(raw.get("confidence"), dict) else {}

    fields: dict[str, Any] = {}
    for key in FIELD_KEYS:
        value = fields_in.get(key)
        if value in (None, "", "null", "N/A", "n/a", "unknown", "Unknown"):
            continue
        fields[key] = value

    # Constrain enum-backed fields; drop anything the model invented.
    if fields.get("complaint_source") not in VALID_SOURCES:
        fields.pop("complaint_source", None)
    if fields.get("complaint_type") not in VALID_TYPES:
        fields.pop("complaint_type", None)

    for date_key in ("manufacturing_date", "expiry_date", "complaint_date"):
        if date_key in fields:
            iso = heuristics.parse_date(str(fields[date_key]))
            if iso:
                fields[date_key] = iso
            else:
                fields.pop(date_key)

    if "quantity_affected" in fields:
        try:
            fields["quantity_affected"] = float(
                re.sub(r"[^\d.]", "", str(fields["quantity_affected"])) or 0
            ) or None
            if fields["quantity_affected"] is None:
                fields.pop("quantity_affected")
        except (TypeError, ValueError):
            fields.pop("quantity_affected", None)

    if isinstance(fields.get("description"), str):
        fields["description"] = fields["description"].strip()[:2000]

    # A batch/lot code always carries a digit. Models handed a vague document
    # ("could not give a batch number") sometimes echo the label back as the value.
    batch = fields.get("batch_number")
    if isinstance(batch, str) and not any(ch.isdigit() for ch in batch):
        fields.pop("batch_number")

    confidence = {
        k: round(float(v), 2)
        for k, v in conf_in.items()
        if k in fields and isinstance(v, (int, float))
    }
    for key in fields:
        confidence.setdefault(key, 0.75)

    return fields, confidence


def extract_fields(state: AgentState) -> dict:
    started = time.perf_counter()
    text = state.get("normalised_text") or ""

    def fallback() -> dict:
        return heuristics.extract_fields(text)

    raw, engine = chat_json(
        system=prompts.EXTRACTION_SYSTEM,
        user=f"COMPLAINT DOCUMENT:\n\n{text[:12000]}",
        model=EXTRACTION_MODEL,
        fallback=fallback,
    )
    fields, confidence = _coerce_fields(raw)

    if engine == "groq":
        regex_result = heuristics.extract_fields(text)

        # Backfill anything the LLM left blank — the two engines are complementary,
        # and a populated field beats an empty one.
        for key, value in regex_result["fields"].items():
            if key not in fields:
                fields[key] = value
                confidence[key] = round(regex_result["confidence"].get(key, 0.6) * 0.9, 2)

        # Numeric dates like 05/01/2025 are genuinely ambiguous and small models
        # routinely read them month-first. The regex parser applies day/month order
        # explicitly, so let it win wherever it produced a date from the source text.
        for date_key in ("manufacturing_date", "expiry_date", "complaint_date"):
            regex_date = regex_result["fields"].get(date_key)
            if regex_date and regex_date != fields.get(date_key):
                fields[date_key] = regex_date
                confidence[date_key] = round(regex_result["confidence"].get(date_key, 0.8), 2)

    return {
        "fields": fields,
        "field_confidence": confidence,
        "engines": [engine],
        "models_used": {"extraction": EXTRACTION_MODEL if engine == "groq" else "regex-heuristic"},
        "trace": [_trace("extract_fields", engine, started, f"{len(fields)} fields populated")],
    }


# --------------------------------------------------------------------------
# 3. Completeness checker
# --------------------------------------------------------------------------


def check_completeness(state: AgentState) -> dict:
    started = time.perf_counter()
    fields = state.get("fields") or {}

    result, engine = chat_json(
        system=prompts.COMPLETENESS_SYSTEM,
        user=f"EXTRACTED RECORD:\n{json.dumps(fields, indent=2, default=str)}",
        model=EXTRACTION_MODEL,
        fallback=lambda: heuristics.completeness(fields),
    )

    fallback = heuristics.completeness(fields)
    score = result.get("completeness_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        score = fallback["completeness_score"]

    missing = result.get("missing_fields")
    if not isinstance(missing, list):
        missing = fallback["missing_fields"]

    return {
        "completeness_score": score,
        "missing_fields": [str(m) for m in missing][:12],
        "completeness_notes": str(result.get("completeness_notes") or fallback["completeness_notes"]),
        "engines": [engine],
        "trace": [_trace("completeness_check", engine, started, f"score {score}")],
    }


# --------------------------------------------------------------------------
# 4. Risk classification
# --------------------------------------------------------------------------


def classify_risk(state: AgentState) -> dict:
    started = time.perf_counter()
    fields = state.get("fields") or {}
    text = state.get("normalised_text") or ""
    fallback = heuristics.risk(fields, text)

    result, engine = chat_json(
        system=prompts.RISK_SYSTEM,
        user=_context(state),
        model=REASONING_MODEL,
        fallback=lambda: fallback,
    )

    level = result.get("risk_level") if result.get("risk_level") in VALID_RISK else fallback["risk_level"]
    score = result.get("risk_score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        score = fallback["risk_score"]
    severity = (
        result.get("suggested_severity")
        if result.get("suggested_severity") in VALID_SEVERITY
        else fallback["suggested_severity"]
    )
    priority = (
        result.get("suggested_priority")
        if result.get("suggested_priority") in VALID_PRIORITY
        else fallback["suggested_priority"]
    )

    # Models sometimes return an incoherent pair (e.g. "Minor" severity at "P1 - Urgent").
    # The risk level is the anchor, so re-derive both whenever they contradict it.
    expected = {
        "Critical": ("Critical", "P1 - Urgent"),
        "High": ("Major", "P2 - High"),
        "Medium": ("Major", "P3 - Medium"),
        "Low": ("Minor", "P4 - Low"),
    }[level]
    rank = {"Critical": 3, "Major": 2, "Minor": 1}
    urgency = {"P1 - Urgent": 4, "P2 - High": 3, "P3 - Medium": 2, "P4 - Low": 1}
    if abs(rank[severity] - rank[expected[0]]) > 1 or abs(urgency[priority] - urgency[expected[1]]) > 1:
        severity, priority = expected
    elif rank[severity] >= 3 and urgency[priority] <= 2:
        severity, priority = expected  # Critical severity can never sit at P3/P4
    elif urgency[priority] >= 4 and rank[severity] <= 1:
        severity, priority = expected  # P1 can never sit at Minor

    return {
        "risk_level": level,
        "risk_score": score,
        "risk_rationale": str(result.get("risk_rationale") or fallback["risk_rationale"]),
        "regulatory_reportable": bool(result.get("regulatory_reportable", fallback["regulatory_reportable"])),
        "suggested_severity": severity,
        "suggested_priority": priority,
        "engines": [engine],
        "trace": [_trace("risk_classification", engine, started, f"{level} ({score}/100)")],
    }


# --------------------------------------------------------------------------
# 5. Duplicate detection
# --------------------------------------------------------------------------


def _heuristic_duplicates(fields: dict, known: list[dict]) -> dict:
    batch = str(fields.get("batch_number") or "").strip().lower()
    product = str(fields.get("product_name") or "").strip().lower()
    ctype = str(fields.get("complaint_type") or "").strip().lower()

    candidates = []
    for row in known:
        score, reasons = 0.0, []
        row_batch = str(row.get("batch_number") or "").strip().lower()
        row_product = str(row.get("product_name") or "").strip().lower()
        row_type = str(row.get("complaint_type") or "").strip().lower()

        if batch and row_batch and batch == row_batch:
            score += 0.55
            reasons.append(f"identical batch {row.get('batch_number')}")
        if product and row_product and (product in row_product or row_product in product):
            score += 0.25
            reasons.append("same product")
        if ctype and row_type and ctype == row_type:
            score += 0.20
            reasons.append(f"same defect type ({row.get('complaint_type')})")

        if score >= 0.5:
            candidates.append(
                {
                    "complaint_number": row.get("complaint_number"),
                    "complaint_id": row.get("id"),
                    "similarity": round(min(score, 0.99), 2),
                    "reason": "Shares " + ", ".join(reasons) + ".",
                }
            )

    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    return {"duplicate_candidates": candidates[:5]}


def detect_duplicates(state: AgentState) -> dict:
    started = time.perf_counter()
    fields = state.get("fields") or {}
    known = state.get("known_complaints") or []

    if not known:
        return {
            "duplicate_candidates": [],
            "trace": [_trace("duplicate_detection", "skipped", started, "empty complaint register")],
        }

    fallback = _heuristic_duplicates(fields, known)
    result, engine = chat_json(
        system=prompts.DUPLICATE_SYSTEM,
        user=(
            f"NEW COMPLAINT:\n{json.dumps(fields, indent=2, default=str)}\n\n"
            f"EXISTING REGISTER:\n{json.dumps(known[:40], indent=2, default=str)}"
        ),
        model=REASONING_MODEL,
        fallback=lambda: fallback,
    )

    raw = result.get("duplicate_candidates")
    if not isinstance(raw, list):
        raw = fallback["duplicate_candidates"]

    by_number = {r.get("complaint_number"): r for r in known}
    candidates = []
    for item in raw[:5]:
        if not isinstance(item, dict):
            continue
        number = item.get("complaint_number")
        if number not in by_number:  # never surface a hallucinated complaint number
            continue
        try:
            similarity = round(float(item.get("similarity", 0)), 2)
        except (TypeError, ValueError):
            continue
        if similarity < 0.5:
            continue
        candidates.append(
            {
                "complaint_number": number,
                "complaint_id": by_number[number].get("id"),
                "similarity": min(similarity, 1.0),
                "reason": str(item.get("reason") or "Matched on shared complaint attributes."),
            }
        )

    return {
        "duplicate_candidates": candidates,
        "engines": [engine],
        "trace": [_trace("duplicate_detection", engine, started, f"{len(candidates)} candidate(s)")],
    }


# --------------------------------------------------------------------------
# 6. Root cause
# --------------------------------------------------------------------------


def recommend_root_cause(state: AgentState) -> dict:
    started = time.perf_counter()
    fields = state.get("fields") or {}
    fallback = heuristics.root_causes(fields)

    result, engine = chat_json(
        system=prompts.ROOT_CAUSE_SYSTEM,
        user=f"{_context(state)}\n\nASSESSED RISK: {state.get('risk_level')} ({state.get('risk_score')}/100)",
        model=REASONING_MODEL,
        fallback=lambda: fallback,
        temperature=0.3,
    )

    raw = result.get("root_causes")
    causes = []
    if isinstance(raw, list):
        for item in raw[:4]:
            if isinstance(item, dict) and item.get("cause"):
                causes.append(
                    {
                        "cause": str(item["cause"])[:400],
                        "likelihood": item.get("likelihood") if item.get("likelihood") in {"High", "Medium", "Low"} else "Medium",
                        "area": str(item.get("area") or "Manufacturing")[:80],
                    }
                )
    if not causes:
        causes = fallback["root_causes"]

    return {
        "root_causes": causes,
        "engines": [engine],
        "trace": [_trace("root_cause_analysis", engine, started, f"{len(causes)} hypothesis(es)")],
    }


# --------------------------------------------------------------------------
# 7. CAPA
# --------------------------------------------------------------------------


def recommend_capa(state: AgentState) -> dict:
    started = time.perf_counter()
    fields = state.get("fields") or {}
    fallback = heuristics.capa(fields)

    result, engine = chat_json(
        system=prompts.CAPA_SYSTEM,
        user=(
            f"{_context(state)}\n\n"
            f"ASSESSED RISK: {state.get('risk_level')} ({state.get('risk_score')}/100)\n"
            f"PROBABLE ROOT CAUSES: {json.dumps(state.get('root_causes') or [], indent=2)}"
        ),
        model=REASONING_MODEL,
        fallback=lambda: fallback,
        temperature=0.3,
    )

    raw = result.get("capa_recommendations")
    actions = []
    if isinstance(raw, list):
        for item in raw[:6]:
            if isinstance(item, dict) and item.get("action"):
                try:
                    due = int(item.get("due_days", 30))
                except (TypeError, ValueError):
                    due = 30
                actions.append(
                    {
                        "action": str(item["action"])[:400],
                        "type": item.get("type") if item.get("type") in {"Correction", "Corrective", "Preventive"} else "Corrective",
                        "owner": str(item.get("owner") or "QA Head")[:80],
                        "due_days": max(1, min(due, 365)),
                    }
                )
    if not actions:
        actions = fallback["capa_recommendations"]

    return {
        "capa_recommendations": actions,
        "engines": [engine],
        "trace": [_trace("capa_recommendation", engine, started, f"{len(actions)} action(s)")],
    }


# --------------------------------------------------------------------------
# 8. Summary
# --------------------------------------------------------------------------


def write_summary(state: AgentState) -> dict:
    started = time.perf_counter()
    fields = state.get("fields") or {}
    risk_result = {
        "risk_level": state.get("risk_level"),
        "risk_score": state.get("risk_score"),
        "suggested_severity": state.get("suggested_severity"),
        "suggested_priority": state.get("suggested_priority"),
    }

    text, engine = chat_text(
        system=prompts.SUMMARY_SYSTEM,
        user=_context(state) + f"\n\nRISK ASSESSMENT: {json.dumps(risk_result)}",
        model=REASONING_MODEL,
        fallback=lambda: heuristics.summary(fields, risk_result),
    )

    return {
        "summary": text.strip(),
        "engines": [engine],
        "trace": [_trace("summary", engine, started, f"{len(text.split())} words")],
    }
