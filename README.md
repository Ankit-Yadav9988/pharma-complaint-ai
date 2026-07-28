# Pharma Complaint Intelligence Platform

AI-assisted customer complaint management for pharmaceutical manufacturing. A QA officer
drops in a complaint document — email, PDF, DOCX or plain text — and a **LangGraph** agent
running on **Groq** extracts the regulated fields, populates the intake form, and produces a
full triage assessment: risk, completeness, duplicates, root cause and a CAPA plan.

```
React + Redux Toolkit  ──►  FastAPI  ──►  LangGraph agent  ──►  Groq LLMs
                              │
                              └──►  PostgreSQL
```

---

## Quick start

Two terminals. Requires Python 3.11+, Node 18+, and a running PostgreSQL instance.

**1 · Backend**

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                              # then edit DATABASE_URL + GROQ_API_KEY
python scripts/generate_samples.py                # writes 7 demo complaint documents
uvicorn app.main:app --reload
```

**2 · Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Tables are created automatically on first boot.

**3 · Optional — populate the register with all 7 samples**

```bash
cd backend && python scripts/seed_demo.py
```

### Configuration

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:root@localhost:5432/pharma_complaints` | Create the database first: `CREATE DATABASE pharma_complaints;` |
| `GROQ_API_KEY` | *(empty)* | Leave blank to run entirely on the offline heuristic engine |
| `GROQ_EXTRACTION_MODEL` | `llama-3.1-8b-instant` | Fast model for structured field extraction |
| `GROQ_REASONING_MODEL` | `llama-3.3-70b-versatile` | Reasoning model for risk, root cause, CAPA, summary |
| `MAX_UPLOAD_MB` | `10` | Upload size ceiling |

> **On `gemma2-9b-it`** — the brief named this model, and the code was originally written
> against it. Groq has since **decommissioned** it; calls now return
> `400 model_decommissioned`. `llama-3.1-8b-instant` is Groq's documented successor and
> fills the same fast-and-cheap extraction role. Set `GROQ_EXTRACTION_MODEL=gemma2-9b-it`
> in `.env` if it is ever reinstated — no code change needed.

---

## The agent

`backend/app/agents/graph.py` — a LangGraph `StateGraph` with eight nodes:

```
normalise ─► extract_fields ─┬─► completeness_check ─┐
                             ├─► risk_classification ┼─► root_cause ─► capa ─► executive_summary ─► END
                             └─► duplicate_detection ┘
```

The three assessment nodes **fan out in parallel** — they depend only on the extracted
record — then **fan in** before the investigation chain, which needs the risk verdict to
scale its urgency. Progress is streamed to the browser over SSE, so the progress bar
reflects real node completion rather than a timer.

### Dual-engine design

Every node pairs an LLM prompt with a deterministic fallback in `heuristics.py` (regex plus a
pharmaceutical-QA knowledge base). If no API key is set, a call fails, or a model returns
malformed JSON, that node degrades to the fallback instead of failing the request. The
response reports which engine produced each node, and the UI surfaces it — the app never
claims an AI result it did not produce.

Three guards sit on top of the model output, each written after observing the failure live:

- **Enum validation** — an invented `complaint_type` or `severity` is dropped, not stored.
- **Date arbitration** — small models read `05/01/2025` as May 1st. The regex parser applies
  day-first order explicitly and wins on all date fields.
- **Severity/priority coherence** — a model returning "Minor" severity at "P1 - Urgent" gets
  both re-derived from the risk level, which is the anchor.
- **Duplicate grounding** — a candidate whose complaint number is not in the register is
  discarded, so a hallucinated reference can never reach the UI.

### AI features

| Feature | Node | What it does |
|---|---|---|
| Field extraction | `extract_fields` | 13 regulated fields with per-field confidence |
| Completeness checker | `completeness_check` | 0–100 score, names the missing mandatory fields |
| Risk classification | `risk_classification` | Level, 0–100 score, rationale, regulatory reportability |
| Duplicate detection | `duplicate_detection` | Scores the new complaint against the register |
| Root cause | `root_cause` | 2–4 ranked hypotheses with owning process area |
| CAPA recommendation | `capa` | Correction / Corrective / Preventive, with owner and due date |
| Summary | `executive_summary` | One-paragraph brief for the daily QA review |
| Grounded chat | `/api/chat` | Q&A constrained to the loaded complaint |

---

## API

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status and active models |
| `GET` | `/api/intake/capabilities` | Engine, formats, pipeline shape |
| `POST` | `/api/intake/stream` | Paste text → SSE progress → analysis |
| `POST` | `/api/intake/stream-upload` | Upload file → SSE progress → analysis |
| `POST` | `/api/intake/extract` \| `/upload` | Same, non-streaming |
| `POST` | `/api/intake/reanalyze/{id}` | Re-run the agent on a saved complaint |
| `GET` | `/api/intake/samples` | List the bundled demo documents |
| `GET`/`POST` | `/api/complaints` | List (search + filter) / create |
| `GET`/`PATCH`/`DELETE` | `/api/complaints/{id}` | Read / update status / delete |
| `GET` | `/api/complaints/stats` | Dashboard aggregates |
| `POST` | `/api/chat` | Ask about the loaded complaint |

Interactive docs at <http://localhost:8000/docs>.

---

## Sample documents

`python scripts/generate_samples.py` writes seven documents to `backend/samples/`, each
chosen to exercise a different part of the pipeline:

| File | Exercises |
|---|---|
| `01_contamination_complaint.eml` | Email parsing → Critical risk, regulatory reportable |
| `02_packaging_defect_complaint.pdf` | PDF parsing → supplier-quality root causes |
| `03_labelling_error_complaint.txt` | Wrong-strength labelling → line-clearance CAPA |
| `04_adverse_event_field_alert.pdf` | Patient harm → pharmacovigilance escalation |
| `05_duplicate_of_contamination.txt` | **Duplicate detection** — same batch as #1 |
| `06_incomplete_phone_complaint.txt` | **Completeness checker** — sparse phone log |
| `07_regulatory_oos_notice.docx` | DOCX parsing → out-of-specification result |

Document parsing is deliberately lightweight (no OCR, per the brief). An image-only PDF is
reported clearly rather than silently returning nothing.

### Demonstration set

`python scripts/generate_demo_pdfs.py` writes five presentation-grade PDFs to
`backend/samples/demo/`, each engineered to make a different part of the agent visible:

| File | Demonstrates | Verdict |
|---|---|---|
| `D1_contamination_critical.pdf` | Critical escalation, regulatory reporting | Contamination · Critical 85 |
| `D2_efficacy_coldchain.pdf` | Cold-chain reasoning, specific classification | Lack of Efficacy · High 59 |
| `D3_labelling_wrong_strength.pdf` | Narrow-therapeutic-index risk weighting | Labelling Error · High 59 |
| `D4_adverse_event_reaction.pdf` | Pharmacovigilance path, batch clustering | Adverse Event · Critical 85 |
| `D5_incomplete_vague_report.pdf` | **Completeness checker** — refuses to invent data | Appearance · Low 25, 50% complete |

See **[DEMO_GUIDE.md](DEMO_GUIDE.md)** for the full end-to-end walkthrough: what to say for each
document, how text extraction works, how risk is assessed, which function powers which feature,
what happens on save, and the output guards that prevent hallucination.

---

## Layout

```
backend/
  app/
    agents/      graph.py · nodes.py · prompts.py · heuristics.py · llm.py · state.py
    routers/     intake.py · complaints.py · chat.py
    services/    document_parser.py · complaint_service.py
    models.py · schemas.py · database.py · config.py · main.py
  scripts/       generate_samples.py · seed_demo.py
  samples/       generated demo documents
frontend/
  src/
    components/  ComplaintForm · IntakePanel · AIInsights · ComplaintRegister · ComplaintDrawer
    store/       intakeSlice · registerSlice
    api/client.js · constants.js · styles.css
```

State lives in two Redux Toolkit slices: `intake` (the working document, extraction progress,
analysis, chat) and `register` (the saved complaint list, filters, selection). Async work goes
through `createAsyncThunk`; SSE events dispatch `nodeCompleted` per node so the progress bar
and the checklist stay in sync with the backend.

## Notes and limits

- Every AI output is advisory. Root causes are hypotheses to investigate, not conclusions,
  and the UI labels them that way.
- There is no authentication or audit-trail signing — both would be required before this
  touched a validated GxP environment.
- `POST /api/complaints` accepts a client-supplied `analysis` payload. That is fine for a
  demo but should be server-recomputed in production so the stored analysis cannot be forged.
