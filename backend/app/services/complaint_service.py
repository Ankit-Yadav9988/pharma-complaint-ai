"""Database-facing helpers for complaints and agent runs."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AIAnalysis, Complaint, ComplaintStatus, SourceDocument


def next_complaint_number(db: Session) -> str:
    """Sequential, human-readable reference: CMP-2026-0001."""
    year = datetime.now(timezone.utc).year
    prefix = f"CMP-{year}-"
    latest = db.scalar(
        select(func.max(Complaint.complaint_number)).where(
            Complaint.complaint_number.like(f"{prefix}%")
        )
    )
    seq = int(latest.rsplit("-", 1)[1]) + 1 if latest else 1
    return f"{prefix}{seq:04d}"


def register_snapshot(db: Session, limit: int = 40) -> list[dict]:
    """Compact view of existing complaints, fed to the duplicate-detection node."""
    rows = db.scalars(
        select(Complaint).order_by(Complaint.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "complaint_number": r.complaint_number,
            "product_name": r.product_name,
            "batch_number": r.batch_number,
            "complaint_type": r.complaint_type.value if r.complaint_type else None,
            "complaint_date": r.complaint_date.isoformat() if r.complaint_date else None,
            "customer_name": r.customer_name,
            "description": (r.description or "")[:240],
        }
        for r in rows
    ]


def load_complaint(db: Session, complaint_id: int) -> Complaint | None:
    return db.scalar(
        select(Complaint)
        .options(selectinload(Complaint.analyses), selectinload(Complaint.documents))
        .where(Complaint.id == complaint_id)
    )


def attach_analysis(db: Session, complaint: Complaint, payload: dict) -> AIAnalysis:
    analysis = AIAnalysis(
        complaint=complaint,
        engine=payload.get("engine", "heuristic"),
        models_used=payload.get("models_used"),
        extracted_fields=payload.get("extracted_fields"),
        field_confidence=payload.get("field_confidence"),
        completeness_score=payload.get("completeness_score"),
        missing_fields=payload.get("missing_fields"),
        completeness_notes=payload.get("completeness_notes"),
        risk_level=payload.get("risk_level"),
        risk_score=payload.get("risk_score"),
        risk_rationale=payload.get("risk_rationale"),
        regulatory_reportable=payload.get("regulatory_reportable"),
        duplicate_candidates=payload.get("duplicate_candidates"),
        root_causes=payload.get("root_causes"),
        capa_recommendations=payload.get("capa_recommendations"),
        summary=payload.get("summary"),
        trace=payload.get("trace"),
    )
    db.add(analysis)
    return analysis


def attach_document(
    db: Session, complaint: Complaint, filename: str, text: str, content_type: str | None = None
) -> SourceDocument:
    document = SourceDocument(
        complaint=complaint,
        filename=filename,
        content_type=content_type,
        size_bytes=len(text.encode("utf-8")),
        extracted_text=text,
    )
    db.add(document)
    return document


def dashboard_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(Complaint.id))) or 0

    def group(column) -> dict[str, int]:
        rows = db.execute(
            select(column, func.count(Complaint.id)).group_by(column)
        ).all()
        out = {}
        for value, count in rows:
            if value is None:
                continue
            out[value.value if hasattr(value, "value") else str(value)] = count
        return out

    open_critical = db.scalar(
        select(func.count(Complaint.id)).where(
            Complaint.severity == "Critical",
            Complaint.status.notin_([ComplaintStatus.CLOSED, ComplaintStatus.REJECTED]),
        )
    ) or 0

    avg_completeness = db.scalar(select(func.avg(AIAnalysis.completeness_score)))

    return {
        "total": total,
        "by_status": group(Complaint.status),
        "by_severity": group(Complaint.severity),
        "by_type": group(Complaint.complaint_type),
        "open_critical": open_critical,
        "avg_completeness": round(float(avg_completeness), 1) if avg_completeness else None,
    }
