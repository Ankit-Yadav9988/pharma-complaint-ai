"""The LangGraph complaint-intake agent.

    normalise ─► extract_fields ─┬─► completeness_check ─┐
                                 ├─► risk_classification ┼─► root_cause ─► capa ─► summary ─► END
                                 └─► duplicate_detection ┘

The three assessment nodes fan out in parallel (they only depend on the extracted
record), then fan in before the investigation chain, which needs the risk verdict.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import AgentState


@lru_cache
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("normalise", nodes.normalise_document)
    graph.add_node("extract_fields", nodes.extract_fields)
    graph.add_node("completeness_check", nodes.check_completeness)
    graph.add_node("risk_classification", nodes.classify_risk)
    graph.add_node("duplicate_detection", nodes.detect_duplicates)
    graph.add_node("root_cause", nodes.recommend_root_cause)
    graph.add_node("capa", nodes.recommend_capa)
    # Node names must not collide with state keys, hence "executive_summary".
    graph.add_node("executive_summary", nodes.write_summary)

    graph.add_edge(START, "normalise")
    graph.add_edge("normalise", "extract_fields")

    # Fan out: these three only need the extracted record.
    graph.add_edge("extract_fields", "completeness_check")
    graph.add_edge("extract_fields", "risk_classification")
    graph.add_edge("extract_fields", "duplicate_detection")

    # Fan in: root_cause waits for all three before it runs.
    graph.add_edge("completeness_check", "root_cause")
    graph.add_edge("risk_classification", "root_cause")
    graph.add_edge("duplicate_detection", "root_cause")

    graph.add_edge("root_cause", "capa")
    graph.add_edge("capa", "executive_summary")
    graph.add_edge("executive_summary", END)

    return graph.compile()


NODE_LABELS = [
    ("normalise", "Normalising document"),
    ("extract_fields", "Extracting complaint fields"),
    ("completeness_check", "Checking record completeness"),
    ("risk_classification", "Classifying risk & severity"),
    ("duplicate_detection", "Scanning register for duplicates"),
    ("root_cause", "Generating root-cause hypotheses"),
    ("capa", "Drafting CAPA recommendations"),
    ("executive_summary", "Writing executive summary"),
]


def _initial_state(raw_text: str, known_complaints: list[dict], filename: str | None) -> dict:
    return {
        "raw_text": raw_text,
        "filename": filename,
        "known_complaints": known_complaints,
        "trace": [],
        "engines": [],
    }


def _shape_result(result: dict) -> dict:
    engines = set(result.get("engines") or [])
    if "groq" in engines and len(engines) > 1:
        engine = "groq+heuristic"
    elif "groq" in engines:
        engine = "groq"
    else:
        engine = "heuristic"

    fields = result.get("fields") or {}
    # The risk node's severity/priority suggestions become the form's defaults.
    form = dict(fields)
    form.setdefault("severity", result.get("suggested_severity"))
    form.setdefault("priority", result.get("suggested_priority"))

    analysis = {
        "engine": engine,
        "models_used": result.get("models_used") or {},
        "extracted_fields": fields,
        "field_confidence": result.get("field_confidence") or {},
        "completeness_score": result.get("completeness_score"),
        "missing_fields": result.get("missing_fields") or [],
        "completeness_notes": result.get("completeness_notes"),
        "risk_level": result.get("risk_level"),
        "risk_score": result.get("risk_score"),
        "risk_rationale": result.get("risk_rationale"),
        "regulatory_reportable": result.get("regulatory_reportable"),
        "duplicate_candidates": result.get("duplicate_candidates") or [],
        "root_causes": result.get("root_causes") or [],
        "capa_recommendations": result.get("capa_recommendations") or [],
        "summary": result.get("summary"),
        "trace": result.get("trace") or [],
    }

    return {"form": form, "analysis": analysis, "normalised_text": result.get("normalised_text", "")}


def run_agent(raw_text: str, known_complaints: list[dict], filename: str | None = None) -> dict:
    """Execute the full graph and return a flat analysis payload."""
    result = build_graph().invoke(_initial_state(raw_text, known_complaints, filename))
    return _shape_result(result)


def stream_agent(raw_text: str, known_complaints: list[dict], filename: str | None = None):
    """Yield ``("node", {...})`` per completed node, then ``("result", {...})``.

    Backs the live progress bar in the intake panel — the UI shows real node
    completion rather than a fake timer.
    """
    labels = dict(NODE_LABELS)
    total = len(NODE_LABELS)
    merged: dict = {}
    done = 0

    for chunk in build_graph().stream(
        _initial_state(raw_text, known_complaints, filename), stream_mode="updates"
    ):
        for node_name, update in chunk.items():
            if not isinstance(update, dict):
                continue
            for key, value in update.items():
                if key in ("trace", "engines"):
                    merged.setdefault(key, [])
                    merged[key].extend(value or [])
                else:
                    merged[key] = value
            done += 1
            yield "node", {
                "node": node_name,
                "label": labels.get(node_name, node_name.replace("_", " ").title()),
                "completed": done,
                "total": total,
                "progress": round(done / total * 100),
            }

    yield "result", _shape_result(merged)
