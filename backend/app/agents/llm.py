"""Groq LLM access with a deterministic fallback.

The whole agent graph goes through :func:`chat_json` / :func:`chat_text`. When a
``GROQ_API_KEY`` is configured these hit the real Groq endpoints via
``langchain-groq``. When it is absent — or a call fails — we fall back to the
heuristic function supplied by the calling node, so the product stays fully
demoable without credentials. Every result carries the engine that produced it
so the UI can be honest about which one ran.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ENGINE_GROQ = "groq"
ENGINE_HEURISTIC = "heuristic"

_client_cache: dict[str, Any] = {}


def llm_available() -> bool:
    return settings.llm_live


def _get_chat(model: str, temperature: float = 0.0):
    """Lazily build (and memoise) a ChatGroq client for the given model."""
    key = f"{model}:{temperature}"
    if key not in _client_cache:
        from langchain_groq import ChatGroq

        _client_cache[key] = ChatGroq(
            model=model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            max_retries=2,
            timeout=45,
        )
    return _client_cache[key]


def _strip_json(raw: str) -> str:
    """Pull a JSON object out of a model response that may be fenced or chatty."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def chat_json(
    *,
    system: str,
    user: str,
    model: str,
    fallback: Callable[[], dict],
    temperature: float = 0.0,
) -> tuple[dict, str]:
    """Return ``(parsed_json, engine)``. Never raises — always degrades to fallback."""
    if not llm_available():
        return fallback(), ENGINE_HEURISTIC

    try:
        chat = _get_chat(model, temperature)
        resp = chat.invoke(
            [
                ("system", system + "\n\nRespond with a single valid JSON object and nothing else."),
                ("human", user),
            ]
        )
        parsed = json.loads(_strip_json(str(resp.content)))
        if not isinstance(parsed, dict):
            raise ValueError("model did not return a JSON object")
        return parsed, ENGINE_GROQ
    except Exception as exc:  # noqa: BLE001 - degradation is the point
        logger.warning("Groq call failed on %s (%s); using heuristic fallback", model, exc)
        return fallback(), ENGINE_HEURISTIC


def chat_text(
    *,
    system: str,
    user: str,
    model: str,
    fallback: Callable[[], str],
    temperature: float = 0.2,
) -> tuple[str, str]:
    """Free-text completion with the same degradation contract as :func:`chat_json`."""
    if not llm_available():
        return fallback(), ENGINE_HEURISTIC

    try:
        chat = _get_chat(model, temperature)
        resp = chat.invoke([("system", system), ("human", user)])
        content = str(resp.content).strip()
        if not content:
            raise ValueError("empty completion")
        return content, ENGINE_GROQ
    except Exception as exc:  # noqa: BLE001
        logger.warning("Groq call failed on %s (%s); using heuristic fallback", model, exc)
        return fallback(), ENGINE_HEURISTIC
