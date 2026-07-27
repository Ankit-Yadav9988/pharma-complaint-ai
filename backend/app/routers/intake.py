"""Document intake: upload or paste a complaint, run the agent, stream progress."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.graph import NODE_LABELS, run_agent, stream_agent
from app.config import get_settings
from app.database import get_db
from app.schemas import ExtractRequest, ExtractResponse
from app.services import complaint_service
from app.services.document_parser import (
    SUPPORTED_EXTENSIONS,
    EmptyDocument,
    UnsupportedDocument,
    parse_document,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intake", tags=["intake"])
settings = get_settings()


def _read_upload(file: UploadFile) -> str:
    data = file.file.read()
    limit = settings.max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB limit.")
    try:
        return parse_document(file.filename or "upload", data)
    except UnsupportedDocument as exc:
        raise HTTPException(415, str(exc)) from exc
    except EmptyDocument as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to parse upload")
        raise HTTPException(422, f"Could not read this document: {exc}") from exc


@router.get("/capabilities")
def capabilities() -> dict:
    """Lets the UI tell the user which engine and models are actually in play."""
    return {
        "llm_live": settings.llm_live,
        "engine": "groq" if settings.llm_live else "heuristic",
        "extraction_model": settings.groq_extraction_model,
        "reasoning_model": settings.groq_reasoning_model,
        "supported_formats": sorted(e.lstrip(".").upper() for e in SUPPORTED_EXTENSIONS),
        "max_upload_mb": settings.max_upload_mb,
        "pipeline": [{"node": n, "label": lbl} for n, lbl in NODE_LABELS],
    }


@router.post("/extract", response_model=ExtractResponse)
def extract_from_text(payload: ExtractRequest, db: Session = Depends(get_db)) -> ExtractResponse:
    """Non-streaming intake for pasted text."""
    known = complaint_service.register_snapshot(db)
    result = run_agent(payload.text, known, payload.filename)
    return ExtractResponse(
        raw_text=result["normalised_text"],
        filename=payload.filename,
        form=result["form"],
        analysis=result["analysis"],
    )


@router.post("/upload", response_model=ExtractResponse)
def extract_from_upload(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ExtractResponse:
    """Non-streaming intake for an uploaded document."""
    text = _read_upload(file)
    known = complaint_service.register_snapshot(db)
    result = run_agent(text, known, file.filename)
    return ExtractResponse(
        raw_text=result["normalised_text"],
        filename=file.filename,
        form=result["form"],
        analysis=result["analysis"],
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _stream_response(text: str, filename: str | None, known: list[dict]) -> StreamingResponse:
    def generate():
        yield _sse("start", {"filename": filename, "chars": len(text)})
        try:
            for kind, payload in stream_agent(text, known, filename):
                if kind == "node":
                    yield _sse("node", payload)
                else:
                    yield _sse(
                        "result",
                        {
                            "raw_text": payload["normalised_text"],
                            "filename": filename,
                            "form": payload["form"],
                            "analysis": payload["analysis"],
                        },
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent run failed")
            yield _sse("error", {"message": f"Analysis failed: {exc}"})
        yield _sse("done", {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream")
def stream_from_text(payload: ExtractRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """Streaming intake for pasted text — emits one SSE event per agent node."""
    return _stream_response(payload.text, payload.filename, complaint_service.register_snapshot(db))


@router.post("/stream-upload")
def stream_from_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Streaming intake for an uploaded document."""
    text = _read_upload(file)
    return _stream_response(text, file.filename, complaint_service.register_snapshot(db))


@router.post("/reanalyze/{complaint_id}", response_model=ExtractResponse)
def reanalyze(complaint_id: int, db: Session = Depends(get_db)) -> ExtractResponse:
    """Re-run the agent against a saved complaint and store a fresh analysis."""
    complaint = complaint_service.load_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(404, "Complaint not found.")

    source = complaint.documents[0].extracted_text if complaint.documents else None
    text = source or complaint.description or ""
    if len(text) < 10:
        raise HTTPException(422, "This complaint has no source text to re-analyse.")

    known = [c for c in complaint_service.register_snapshot(db) if c["id"] != complaint_id]
    result = run_agent(text, known, f"complaint-{complaint.complaint_number}")
    complaint_service.attach_analysis(db, complaint, result["analysis"])
    db.commit()

    return ExtractResponse(
        raw_text=result["normalised_text"],
        filename=None,
        form=result["form"],
        analysis=result["analysis"],
    )


@router.post("/upload-text")
def upload_text_only(file: UploadFile = File(...), note: str = Form("")) -> dict:
    """Parse a document to text without running the agent (used for previews)."""
    return {"filename": file.filename, "text": _read_upload(file), "note": note}


# --------------------------------------------------------------------------
# Demo samples
# --------------------------------------------------------------------------

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"

SAMPLE_TITLES = {
    "01_contamination_complaint.eml": "Contamination (email)",
    "02_packaging_defect_complaint.pdf": "Packaging defect (PDF)",
    "03_labelling_error_complaint.txt": "Labelling error (text)",
    "04_adverse_event_field_alert.pdf": "Adverse event (PDF)",
    "05_duplicate_of_contamination.txt": "Duplicate of #1 (text)",
    "06_incomplete_phone_complaint.txt": "Incomplete phone log (text)",
    "07_regulatory_oos_notice.docx": "Regulatory OOS (DOCX)",
}


@router.get("/samples")
def list_samples() -> list[dict]:
    """Demo documents shipped with the project, surfaced as one-click chips in the UI."""
    if not SAMPLES_DIR.is_dir():
        return []
    return [
        {
            "filename": path.name,
            "title": SAMPLE_TITLES.get(path.name, path.stem.replace("_", " ").title()),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(SAMPLES_DIR.iterdir())
        if path.is_file()
    ]


@router.get("/samples/{filename}")
def read_sample(filename: str) -> dict:
    """Return a sample document parsed to plain text."""
    if filename not in SAMPLE_TITLES:
        raise HTTPException(404, "Unknown sample document.")

    path = SAMPLES_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "Sample not found on disk. Run scripts/generate_samples.py.")

    try:
        text = parse_document(filename, path.read_bytes())
    except (UnsupportedDocument, EmptyDocument) as exc:
        raise HTTPException(422, str(exc)) from exc

    return {"filename": filename, "title": SAMPLE_TITLES[filename], "text": text}
