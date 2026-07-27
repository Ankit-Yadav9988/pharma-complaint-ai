"""Run every sample document through the live API and save it to the register.

    python scripts/seed_demo.py

Useful for populating a demo database, and as an end-to-end smoke test: it exercises
document parsing, the LangGraph agent, duplicate detection against previously-saved
complaints, and the persistence layer.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000/api"
SAMPLES = Path(__file__).resolve().parent.parent / "samples"

# Order matters: the contamination email must be saved before its duplicate is analysed.
ORDER = [
    "01_contamination_complaint.eml",
    "02_packaging_defect_complaint.pdf",
    "03_labelling_error_complaint.txt",
    "04_adverse_event_field_alert.pdf",
    "05_duplicate_of_contamination.txt",
    "06_incomplete_phone_complaint.txt",
    "07_regulatory_oos_notice.docx",
]

FORM_KEYS = [
    "complaint_source", "customer_name", "customer_contact",
    "product_name", "product_strength", "batch_number",
    "manufacturing_date", "expiry_date", "quantity_affected", "quantity_unit",
    "complaint_type", "complaint_date", "description", "severity", "priority",
]


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as response:
        return json.load(response)


def main() -> int:
    try:
        health = get("/health")
    except urllib.error.URLError:
        print("Backend is not running. Start it with:")
        print("  uvicorn app.main:app --reload")
        return 1

    engine = "Groq (live)" if health["llm_live"] else "heuristic fallback"
    print(f"Engine: {engine}  ·  extraction={health['extraction_model']}\n")

    for name in ORDER:
        path = SAMPLES / name
        if not path.is_file():
            print(f"  SKIP  {name} (not found — run generate_samples.py first)")
            continue

        sample = get(f"/intake/samples/{name}")
        result = post("/intake/extract", {"text": sample["text"], "filename": name})

        form, analysis = result["form"], result["analysis"]
        payload = {
            "analysis": analysis,
            "source_text": result["raw_text"],
            "source_filename": name,
        }
        for key in FORM_KEYS:
            value = form.get(key)
            if value not in (None, ""):
                payload[key] = value

        saved = post("/complaints", payload)
        dupes = analysis.get("duplicate_candidates") or []
        dupe_note = (
            "  DUPLICATE of " + ", ".join(f"{d['complaint_number']} ({d['similarity']:.0%})" for d in dupes)
            if dupes
            else ""
        )

        print(
            f"  {saved['complaint_number']}  {name[:38]:<40}"
            f"{str(form.get('complaint_type'))[:22]:<24}"
            f"{analysis['risk_level']:<9}{analysis['risk_score']:>3}/100  "
            f"complete {analysis['completeness_score']:>3}%{dupe_note}"
        )

    stats = get("/complaints/stats")
    print(f"\nRegister now holds {stats['total']} complaints "
          f"({stats['open_critical']} open critical, avg completeness {stats['avg_completeness']}%).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
