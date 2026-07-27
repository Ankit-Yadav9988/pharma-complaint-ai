"""Conversational assistant grounded on the complaint currently in the form."""
from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.llm import chat_text
from app.agents.prompts import CHAT_SYSTEM
from app.config import get_settings
from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services import complaint_service

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


def _complaint_context(db: Session, complaint_id: int | None) -> str:
    if not complaint_id:
        return ""
    complaint = complaint_service.load_complaint(db, complaint_id)
    if not complaint:
        return ""

    analysis = complaint.latest_analysis
    block = {
        "complaint_number": complaint.complaint_number,
        "customer_name": complaint.customer_name,
        "product_name": complaint.product_name,
        "batch_number": complaint.batch_number,
        "complaint_type": complaint.complaint_type.value if complaint.complaint_type else None,
        "severity": complaint.severity.value if complaint.severity else None,
        "status": complaint.status.value,
        "description": complaint.description,
    }
    if analysis:
        block |= {
            "risk_level": analysis.risk_level,
            "risk_rationale": analysis.risk_rationale,
            "completeness_score": analysis.completeness_score,
            "missing_fields": analysis.missing_fields,
            "root_causes": analysis.root_causes,
            "capa_recommendations": analysis.capa_recommendations,
            "summary": analysis.summary,
        }
    return json.dumps(block, indent=2, default=str)


def _keyword_answer(message: str, context: str) -> str:
    """Offline fallback: pull the relevant lines out of the context.

    Deliberately extractive rather than generative — without a model it is better
    to quote the record than to compose an answer that sounds authoritative.
    """
    if not context.strip():
        return (
            "I don't have a complaint loaded yet. Upload a document or paste the complaint "
            "text and I'll extract the details, then I can answer questions about it."
        )

    stop = {
        "what", "which", "when", "where", "who", "whom", "the", "this", "that", "is",
        "are", "was", "were", "does", "did", "do", "for", "and", "with", "about",
        "tell", "me", "please", "can", "you", "of", "in", "on", "a", "an", "how",
    }
    terms = {w for w in re.findall(r"[a-z0-9]+", message.lower()) if w not in stop and len(w) > 2}

    hits = [
        line.strip().rstrip(",")
        for line in context.splitlines()
        if line.strip() not in "{}" and any(t in line.lower() for t in terms)
    ]

    if hits:
        body = "\n".join(f"• {h}" for h in hits[:8])
        return (
            f"From the complaint record:\n{body}\n\n"
            "(Heuristic mode — add a GROQ_API_KEY to backend/.env for full conversational answers.)"
        )
    return (
        "I couldn't find that in the current complaint record. The record holds the customer, "
        "product, batch, dates, defect type, risk assessment, root causes and CAPA plan — "
        "try asking about one of those, or request the detail from the complainant.\n\n"
        "(Heuristic mode — add a GROQ_API_KEY to backend/.env for full conversational answers.)"
    )


@router.post("", response_model=ChatResponse)
def ask(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    context = _complaint_context(db, payload.complaint_id)
    if payload.context_text:
        context = (context + "\n\nWORKING DRAFT / SOURCE DOCUMENT:\n" + payload.context_text[:6000]).strip()

    history = ""
    for turn in payload.history[-6:]:
        role = "Officer" if turn.get("role") == "user" else "Assistant"
        history += f"{role}: {turn.get('content', '')}\n"

    reply, engine = chat_text(
        system=CHAT_SYSTEM,
        user=(
            f"COMPLAINT CONTEXT:\n{context or '(no complaint loaded yet)'}\n\n"
            f"CONVERSATION SO FAR:\n{history or '(none)'}\n\n"
            f"OFFICER'S QUESTION: {payload.message}"
        ),
        model=settings.groq_reasoning_model,
        fallback=lambda: _keyword_answer(payload.message, context),
        temperature=0.3,
    )
    return ChatResponse(reply=reply, engine=engine)
