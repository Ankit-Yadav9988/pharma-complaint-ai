"""FastAPI application entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import chat, complaints, intake

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Pharma Complaint Intelligence API",
    description=(
        "AI-assisted customer complaint management for pharmaceutical manufacturing. "
        "Document intake and triage run through a LangGraph agent backed by Groq."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(complaints.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    mode = "Groq (live)" if settings.llm_live else "heuristic fallback (no GROQ_API_KEY set)"
    logger.info("Database ready. AI engine: %s", mode)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_live": settings.llm_live,
        "extraction_model": settings.groq_extraction_model,
        "reasoning_model": settings.groq_reasoning_model,
    }
3