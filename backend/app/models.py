"""SQLAlchemy ORM models for the complaint management system."""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ComplaintSource(str, enum.Enum):
    EMAIL = "Email"
    PHONE = "Phone"
    PORTAL = "Customer Portal"
    FIELD_ALERT = "Field Alert"
    DISTRIBUTOR = "Distributor"
    REGULATORY = "Regulatory Body"
    SALES_REP = "Sales Representative"
    OTHER = "Other"


class ComplaintType(str, enum.Enum):
    PRODUCT_QUALITY = "Product Quality"
    PACKAGING_DEFECT = "Packaging Defect"
    LABELLING_ERROR = "Labelling Error"
    CONTAMINATION = "Contamination"
    ADVERSE_EVENT = "Adverse Event"
    EFFICACY = "Lack of Efficacy"
    APPEARANCE = "Appearance / Physical Defect"
    SHORTAGE = "Quantity / Shortage"
    DOCUMENTATION = "Documentation Discrepancy"
    OTHER = "Other"


class Severity(str, enum.Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class Priority(str, enum.Enum):
    P1_URGENT = "P1 - Urgent"
    P2_HIGH = "P2 - High"
    P3_MEDIUM = "P3 - Medium"
    P4_LOW = "P4 - Low"


class ComplaintStatus(str, enum.Enum):
    PENDING_TRIAGE = "Pending Triage"
    UNDER_INVESTIGATION = "Under Investigation"
    CAPA_ASSIGNED = "CAPA Assigned"
    CLOSED = "Closed"
    REJECTED = "Rejected"


def _enum(py_enum, name: str):
    """Store enums by their human-readable value rather than the member name."""
    return Enum(
        py_enum,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=False,
        length=64,
    )


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # 1. Origin & customer details
    complaint_source: Mapped[ComplaintSource | None] = mapped_column(
        _enum(ComplaintSource, "complaint_source"), nullable=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_contact: Mapped[str | None] = mapped_column(String(255))

    # 2. Product & batch identification
    product_name: Mapped[str | None] = mapped_column(String(255), index=True)
    product_strength: Mapped[str | None] = mapped_column(String(128))
    batch_number: Mapped[str | None] = mapped_column(String(128), index=True)
    manufacturing_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    quantity_affected: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(32), default="kg")

    # 3. Complaint details
    complaint_type: Mapped[ComplaintType | None] = mapped_column(
        _enum(ComplaintType, "complaint_type"), nullable=True
    )
    complaint_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)

    # 4. Initial assessment & priority
    severity: Mapped[Severity | None] = mapped_column(
        _enum(Severity, "severity"), nullable=True
    )
    priority: Mapped[Priority | None] = mapped_column(
        _enum(Priority, "priority"), nullable=True
    )

    status: Mapped[ComplaintStatus] = mapped_column(
        _enum(ComplaintStatus, "complaint_status"),
        default=ComplaintStatus.PENDING_TRIAGE,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    analyses: Mapped[list["AIAnalysis"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="AIAnalysis.id.desc()",
    )
    documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )

    @property
    def latest_analysis(self) -> "AIAnalysis | None":
        return self.analyses[0] if self.analyses else None


class AIAnalysis(Base):
    """Output of one full LangGraph agent run against a complaint."""

    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int | None] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )

    engine: Mapped[str] = mapped_column(String(64), default="heuristic")
    models_used: Mapped[dict | None] = mapped_column(JSON)

    extracted_fields: Mapped[dict | None] = mapped_column(JSON)
    field_confidence: Mapped[dict | None] = mapped_column(JSON)

    completeness_score: Mapped[int | None] = mapped_column(Integer)
    missing_fields: Mapped[list | None] = mapped_column(JSON)
    completeness_notes: Mapped[str | None] = mapped_column(Text)

    risk_level: Mapped[str | None] = mapped_column(String(32))
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_rationale: Mapped[str | None] = mapped_column(Text)
    regulatory_reportable: Mapped[bool | None] = mapped_column(default=False)

    duplicate_candidates: Mapped[list | None] = mapped_column(JSON)

    root_causes: Mapped[list | None] = mapped_column(JSON)
    capa_recommendations: Mapped[list | None] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text)

    trace: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    complaint: Mapped["Complaint"] = relationship(back_populates="analyses")


class SourceDocument(Base):
    """The raw document a complaint was extracted from."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int | None] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    complaint: Mapped["Complaint"] = relationship(back_populates="documents")
