"""Complaint register CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Complaint, ComplaintStatus, Severity
from app.schemas import (
    ComplaintCreate,
    ComplaintListItem,
    ComplaintOut,
    ComplaintUpdate,
    DashboardStats,
)
from app.services import complaint_service

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)) -> DashboardStats:
    return DashboardStats(**complaint_service.dashboard_stats(db))


@router.get("", response_model=list[ComplaintListItem])
def list_complaints(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Free-text search"),
    status: ComplaintStatus | None = None,
    severity: Severity | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> list[Complaint]:
    stmt = select(Complaint).order_by(Complaint.id.desc())

    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.complaint_number.ilike(pattern),
                Complaint.customer_name.ilike(pattern),
                Complaint.product_name.ilike(pattern),
                Complaint.batch_number.ilike(pattern),
                Complaint.description.ilike(pattern),
            )
        )
    if status:
        stmt = stmt.where(Complaint.status == status)
    if severity:
        stmt = stmt.where(Complaint.severity == severity)

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)) -> Complaint:
    complaint = complaint_service.load_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")
    return complaint


@router.post("", response_model=ComplaintOut, status_code=201)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)) -> Complaint:
    data = payload.model_dump(exclude={"analysis", "source_text", "source_filename"})

    if not any(v for v in data.values()):
        raise HTTPException(422, "Cannot save an entirely empty complaint.")

    complaint = Complaint(
        complaint_number=complaint_service.next_complaint_number(db),
        status=ComplaintStatus.PENDING_TRIAGE,
        **data,
    )
    db.add(complaint)

    if payload.analysis:
        complaint_service.attach_analysis(db, complaint, payload.analysis.model_dump())
    if payload.source_text:
        complaint_service.attach_document(
            db, complaint, payload.source_filename or "pasted-text.txt", payload.source_text
        )

    db.commit()
    db.refresh(complaint)
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: int, payload: ComplaintUpdate, db: Session = Depends(get_db)
) -> Complaint:
    complaint = complaint_service.load_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(complaint, key, value)

    db.commit()
    db.refresh(complaint)
    return complaint


@router.delete("/{complaint_id}", status_code=204, response_class=Response)
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")
    db.delete(complaint)
    db.commit()
    return Response(status_code=204)
