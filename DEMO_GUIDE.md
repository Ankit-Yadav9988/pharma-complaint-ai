# Demo Guide & Complete Technical Walkthrough

Everything you need to run the demonstration and explain the system end to end.

- **Part 1** — the five demo datasets, what to say, what the AI returns
- **Part 2** — how the whole system works, feature by feature, with the exact file and function behind each one
- **Part 3** — what happens when you press Save
- **Part 4** — likely interview questions and answers

---

# Part 1 — The Five Demo Datasets

The PDFs live in `backend/samples/demo/`. Each one is engineered to make a **different part of the agent visible**, so together they demonstrate all six AI features.

Regenerate them any time with:

```bash
python scripts/generate_demo_pdfs.py
```

## Summary table

| # | File | Demonstrates | Type | Risk | Complete |
|---|------|--------------|------|------|----------|
| D1 | `D1_contamination_critical.pdf` | Critical escalation, regulatory reporting | Contamination | **Critical 85** | 100% |
| D2 | `D2_efficacy_coldchain.pdf` | Cold-chain root causes, specific classification | Lack of Efficacy | **High 59** | 100% |
| D3 | `D3_labelling_wrong_strength.pdf` | Labelling defect, narrow-therapeutic-index reasoning | Labelling Error | **High 59** | 100% |
| D4 | `D4_adverse_event_reaction.pdf` | Pharmacovigilance path, patient harm | Adverse Event | **Critical 85** | 100% |
| D5 | `D5_incomplete_vague_report.pdf` | **Completeness checker firing** | Appearance / Physical Defect | **Low 25** | **50%** |

All five were verified against the live Groq API. These are the actual returned values, not expected ones.

---

## D1 — Critical contamination

**Product:** Cefuroxime Sodium for Injection 750 mg · Batch `CFZ-6621-A`
**Story:** Grey-black particulate matter in reconstituted vials. **One patient received a partial dose** and developed pyrexia.

**Extracted:** source Distributor · Beacon Hospital Group Pharmacy · mfg `2025-03-14` · exp `2027-03-13` · 84 vials · complaint date `2026-06-19`

**AI verdict:** Contamination · **Critical, 85/100** · **Regulatory reportable = TRUE** · Severity Critical · Priority P1 - Urgent

**What to say:**
> "This is the worst case a QA department sees — a sterile injectable with visible particulate and confirmed patient exposure. Notice three things. The agent picked **Contamination**, not the vaguer 'Product Quality', because the prompt tells it to choose the most specific type. It flagged this as **regulatory reportable**, which in FDA terms means a Field Alert Report inside three days. And it scored 85 — driven by the sterile route plus the patient exposure, both of which the risk prompt treats as critical signals."

This is your strongest opener. Lead with it.

---

## D2 — Cold-chain efficacy failure

**Product:** Insulin Glargine 100 IU/mL · Batch `ING-4417-D`
**Story:** Four patients' blood glucose rose. Product looks perfect. A temperature logger recorded **19.4 °C for eleven hours** against a 2–8 °C requirement.

**Extracted:** source Customer Portal · Silverbrook Retail Pharmacy Chain · mfg `2025-09-08` · exp `2027-09-07` · 150 pens

**AI verdict:** **Lack of Efficacy** · High, 59/100 · Severity Major · Priority P2 - High

**What to say:**
> "This one is subtle and it's the best demonstration of *reasoning* rather than keyword matching. There is no visible defect at all — the pens look fine. The complaint is that the drug stopped working. The agent classifies it as **Lack of Efficacy**, not Product Quality, because Product Quality is reserved for a laboratory finding on the product; this is a reported clinical failure. Then the root-cause node connects the symptom to the temperature excursion in the narrative and proposes cold-chain hypotheses — that's the LLM linking cause to effect across paragraphs."

---

## D3 — Wrong-strength labelling

**Product:** Warfarin Sodium Tablets 3 mg · Batch `WAR-2208-F`
**Story:** ~80 cartons labelled **5 mg**; the blister foil inside says **3 mg**. Caught at goods-in.

**Extracted:** source Distributor · Kingsway Wholesale Distribution Ltd · mfg `2026-01-21` · exp `2028-01-20` · 2400 tablets

**AI verdict:** Labelling Error · High, 59/100 · Severity Major · Priority P2 - High

**What to say:**
> "Warfarin is an anticoagulant with a narrow therapeutic index — a 67% overdose is a serious bleeding risk. The agent identifies the labelling defect and rates it High. It's *not* Critical, and that's correct reasoning, not a miss: the error was intercepted at goods-in, so no patient was ever exposed. Compare it to D1, which is Critical precisely because a patient did receive product. The model is weighing actual exposure, not just the theoretical hazard."

**Use this one if they ask "how do you know it isn't just pattern-matching?"** — the contrast between D1 and D3 is the answer.

---

## D4 — Adverse event

**Product:** Iohexol Contrast Injection 350 mg I/mL · Batch `IOH-9075-C`
**Story:** Five hypersensitivity reactions in two days, all from one batch. One patient needed adrenaline and overnight admission.

**Extracted:** source Sales Representative · Northfield Regional Medical Centre · mfg `2026-02-05` · exp `2028-02-04` · 22 bottles

**AI verdict:** Adverse Event · **Critical, 85/100** · **Reportable = TRUE** · Severity Critical · Priority P1 - Urgent

**What to say:**
> "D1 and D4 are both Critical but for different reasons, and the rationale text shows that. D1 is a *visible product defect* that harmed someone. D4 has **no visible defect** — the solution is clear, in-date and correctly labelled — yet five patients reacted from one batch while a different batch on the same days caused none. The agent picks up that batch-level clustering signal and routes it down the pharmacovigilance path rather than a physical-defect investigation."

---

## D5 — Deliberately incomplete phone call

**Story:** A caller says her "heart tablets" look wrong — uneven colour, chipped edges. She doesn't have the carton. **No batch, no expiry, no strength, no product name.**

**Extracted:** source Phone · complaint date `2026-07-26` · type Appearance / Physical Defect · everything else **blank**

**AI verdict:** **Completeness 50%** · 7 missing fields · Low, 25/100 · Priority P4 - Low

**Missing fields shown as amber badges:** Customer Name, Product Name, Batch / Lot Number, Product Strength *(optional)*, Manufacturing Date *(optional)*, Expiry Date *(optional)*, Quantity Affected *(optional)*

**What to say:**
> "Save this one for last, because it demonstrates the feature nobody expects. A real complaint intake system spends most of its life dealing with *incomplete* reports, not tidy ones. The agent doesn't hallucinate a batch number to fill the box — it leaves the field empty, drops completeness to 50%, and lists exactly what the QA officer has to chase before this can be triaged. It also correctly classifies **Appearance / Physical Defect** — the tablets look wrong — rather than Packaging Defect, even though the caller mentions opening a blister."

**This is the answer to "what stops the AI making things up?"**

---

## Suggested 8-minute demo order

| Time | Do this | Point being made |
|------|---------|------------------|
| 0:00 | Show the empty form + LIVE badge | Groq is connected |
| 0:30 | Drop **D1** | Watch the progress bar tick through the agent nodes |
| 1:30 | Walk the populated form + AI panel | Extraction, risk, CAPA all at once |
| 3:00 | Press **Save** | Complaint number assigned, register updated |
| 4:00 | Drop **D5** | Completeness checker; AI declines to invent data |
| 5:30 | Drop **D3**, compare to D1 | Reasoning about exposure, not keywords |
| 6:30 | Ask the chat panel *"What is the risk assessment?"* | Grounded conversational layer |
| 7:30 | Open the dashboard | Persistence and stats |

**Tip:** after saving D1, re-upload it. The duplicate detector will flag the saved complaint. That's the cleanest way to demo duplicate detection live.

---

## If you want to paste text instead of uploading

The pasted-text path uses a different endpoint (`/api/intake/extract`) but the same agent. Worth doing once to show both work. Paste this:

```
From: qa.pharmacy@beaconhospital.org
Subject: URGENT product complaint - particulate in Cefuroxime vials

Customer: Beacon Hospital Group Pharmacy
Product: Cefuroxime Sodium for Injection
Strength: 750 mg vial
Batch No: CFZ-6621-A
Mfg Date: 14/03/2025
Expiry Date: 13/03/2027
Quantity Affected: 84 vials
Complaint Date: 19/06/2026

During reconstitution the ward pharmacist observed distinct grey-black
particulate matter suspended in the solution in six separate vials.
One patient received a partial dose before the pharmacist intervened
and developed a low-grade pyrexia within ninety minutes.
```

There are also seven ready-made samples as one-click chips in the UI (`backend/samples/`), covering `.eml`, `.pdf`, `.txt` and `.docx` so you can show every supported format.

---

# Part 2 — How The Whole System Works

## The 10-second version

> A QA officer receives a complaint as an email, PDF or phone note. Instead of typing 17 fields by hand, they drop the document in. A LangGraph agent reads it, fills the form, and produces a risk assessment, a completeness check, duplicate matches, probable root causes and a recommended CAPA plan. The officer reviews, corrects anything wrong, and saves.

## Technology map

| Layer | Technology | Why |
|-------|-----------|-----|
| UI | React 18 + Vite | Required by brief |
| State | Redux Toolkit | Required by brief |
| API | FastAPI (Python) | Required by brief |
| Agent | LangGraph `StateGraph` | Required by brief |
| LLM | Groq — `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` | Required by brief* |
| DB | PostgreSQL + SQLAlchemy 2.0 | Required by brief |
| Parsing | pypdf, python-docx, `email.parser` | Read PDF / DOCX / EML |
| Streaming | Server-Sent Events | Live per-node progress |
| Font | Google Inter | Required by brief |

\* **The brief named `gemma2-9b-it`. Groq decommissioned that model** — it returns `400 model_decommissioned`. I substituted `llama-3.1-8b-instant`, Groq's documented successor for fast structured extraction, and documented the swap in `.env.example`, `config.py` and the README. **Say this before they ask.** It shows you verified rather than copied.

### Why two models

| Model | Used for | Reason |
|-------|----------|--------|
| `llama-3.1-8b-instant` | Field extraction, completeness | Fast, cheap; this is transcription, not reasoning |
| `llama-3.3-70b-versatile` | Risk, root cause, CAPA, summary | Needs real pharma judgement |

Routing lives in `backend/app/agents/nodes.py` — each node picks `EXTRACTION_MODEL` or `REASONING_MODEL`.

---

## The complete request journey

### Step 1 — User drops a file

`frontend/src/components/IntakePanel.jsx` → `handleFile()` → dispatches `runExtraction({ file })`.

### Step 2 — Redux thunk opens a stream

`frontend/src/store/intakeSlice.js` → `runExtraction`. It calls `streamExtraction()` and dispatches `nodeCompleted` on every `node` event — that's what drives the live progress bar.

> **Why not `EventSource`?** The browser's built-in SSE client is GET-only and can't send a file. So the client uses `fetch` with a `POST` and reads the response body as a stream manually. Good detail to volunteer — it shows you understood the constraint rather than reaching for the obvious API.

### Step 3 — FastAPI receives it

`backend/app/routers/intake.py`

| Endpoint | Purpose |
|----------|---------|
| `POST /api/intake/stream-upload` | File + live progress ← **the demo path** |
| `POST /api/intake/stream` | Pasted text + live progress |
| `POST /api/intake/upload` | File, single response |
| `POST /api/intake/extract` | Pasted text, single response |
| `POST /api/intake/reanalyze/{id}` | Re-run agent on a saved complaint |
| `GET /api/intake/capabilities` | Drives the LIVE / OFFLINE badge |
| `GET /api/intake/samples` | The one-click sample chips |

### Step 4 — Text extraction

`backend/app/services/document_parser.py` → `parse_document(filename, data)` dispatches on extension:

| Format | Function | Library |
|--------|----------|---------|
| PDF | `_parse_pdf` | `pypdf` — `PdfReader`, page by page |
| DOCX | `_parse_docx` | `python-docx` — paragraphs **and table cells** |
| EML | `_parse_eml` | stdlib `email.parser` — headers + body |
| TXT / MD | direct decode | — |

Two deliberate choices worth mentioning:

- **A single corrupt PDF page doesn't kill the upload.** `_parse_pdf` catches per page and continues.
- **No OCR.** A scanned image-only PDF raises `EmptyDocument` with a clear message rather than silently returning nothing. Failing loudly beats failing quietly.

### Step 5 — The LangGraph agent

`backend/app/agents/graph.py` — `build_graph()`:

```
              START
                │
          normalise            clean whitespace, strip signatures
                │
         extract_fields        ← llama-3.1-8b-instant
                │
      ┌─────────┼─────────┐    FAN OUT — three run in parallel
      │         │         │
completeness  risk    duplicate
   _check  _classification _detection
      │         │         │
      └─────────┼─────────┘    FAN IN
                │
           root_cause          ← llama-3.3-70b-versatile
                │
              capa             ← llama-3.3-70b-versatile
                │
       executive_summary       ← llama-3.3-70b-versatile
                │
               END
```

**Why this shape?** Completeness, risk and duplicates only need the extracted fields — they don't need each other, so they run concurrently and the wall-clock cost is the slowest of the three, not their sum. Root cause genuinely needs all three (it reasons about the risk level and the duplicate history), so that's a real barrier.

**Parallel branches need a merge strategy.** In `state.py`:

```python
trace: Annotated[list, _merge_list]
engines: Annotated[list, _merge_list]
```

Without the `Annotated` reducer the three parallel branches would each write `trace` and the last writer would win, silently losing two nodes' worth of history. That `Annotated[...]` is the single most important line in the state file.

### Step 6 — Node-by-node

| # | Node | Function | Model | Produces |
|---|------|----------|-------|----------|
| 1 | `normalise` | `normalise_document` | none | Clean text |
| 2 | `extract_fields` | `extract_fields` | 8b | 17 form fields + per-field confidence |
| 3 | `completeness_check` | `check_completeness` | 8b | Score, missing list, advisory notes |
| 4 | `risk_classification` | `classify_risk` | 70b | Level, score, rationale, reportable flag |
| 5 | `duplicate_detection` | `detect_duplicates` | 70b | Candidate matches with similarity |
| 6 | `root_cause` | `recommend_root_cause` | 70b | Ranked hypotheses |
| 7 | `capa` | `recommend_capa` | 70b | Correction / Corrective / Preventive |
| 8 | `executive_summary` | `write_summary` | 70b | Management paragraph |

---

## Feature → file → function

| Bonus feature | Where | Function |
|---------------|-------|----------|
| Complaint Completeness Checker | `nodes.py` + `heuristics.py` | `check_completeness` / `completeness` |
| AI Risk Classification | `nodes.py` + `heuristics.py` | `classify_risk` / `risk` |
| Duplicate Detection | `nodes.py` | `detect_duplicates` |
| Root Cause Recommendation | `nodes.py` + `heuristics.py` | `recommend_root_cause` / `KNOWLEDGE_BASE` |
| CAPA Recommendation | `nodes.py` + `heuristics.py` | `recommend_capa` / `KNOWLEDGE_BASE` |
| Complaint Summary | `nodes.py` + `heuristics.py` | `write_summary` / `summary` |

---

## The dual-engine design — your strongest talking point

**Every single node has two implementations.**

```python
result, engine = chat_json(
    system=prompts.RISK_SYSTEM,
    user=_context(state),
    model=REASONING_MODEL,
    fallback=lambda: heuristics.risk(fields, text),   # ← deterministic backup
)
```

`chat_json()` in `agents/llm.py` **never raises**. No API key, rate limit, timeout, malformed JSON — any failure falls through to a regex-and-knowledge-base implementation in `heuristics.py`, and the returned `engine` string records which one actually ran.

Three consequences:

1. **The app never shows a blank screen.** Pull the API key and it still works, just less nuanced.
2. **It never claims an AI result it didn't produce.** `engine` is `groq`, `heuristic`, or `groq+heuristic`.
3. **It's testable.** The heuristic path is deterministic, so it can be unit-tested — you can't assert on LLM output.

> "I treated the LLM as an enhancement layer over a working deterministic system, not as the system itself."

---

## The output guards — how hallucination is actually prevented

**Every one of these was written after watching the failure happen live.** Say that. It's the difference between defensive engineering and speculation.

### Guard 1 — Date arbitration

`05/01/2025` is 5 January in pharma (day-first), but the model kept reading it as May 1st. I added a `DATE ORDER` rule to the prompt — it helped but didn't fully hold. So `extract_fields` now **overrides every date field with the regex parser's day-first result**. The prompt is guidance; the regex is enforcement.

### Guard 2 — Severity/priority coherence

The model once returned severity `Major` with priority `P1 - Urgent` — incoherent. `classify_risk` now re-derives **both** from `risk_level`, so the three can never disagree.

### Guard 3 — Duplicate grounding

The model invented a plausible-looking complaint number that didn't exist. `detect_duplicates` now **discards any candidate whose `complaint_number` is not in the register** passed into the prompt.

### Guard 4 — Batch number sanity

The loose fallback regex matched the *words* "batch number" and stored the literal string `"number"`. Two fixes: a digit-requiring lookahead in the regex, and a drop guard in `_coerce_fields` — a batch code always contains a digit.

### Guard 5 — Completeness grounding

The model reported `expiry_date` as missing on a record that had one. **Which fields are blank is arithmetic over a dict, not a judgement call**, so the score and the missing list are now always computed in `heuristics.completeness()`. The LLM contributes only the advisory prose — the part that actually benefits from domain knowledge.

> **The principle:** anything I can verify, I verify. The model is only trusted with things I genuinely cannot compute.

### Guard 6 — Two-column PDF tables

Real bug, found building these demo PDFs. `pypdf` flattens a table cell pair onto **separate lines**:

```
Batch No
CFZ-6621-A
```

The extractor only matched the inline `Batch No: CFZ-6621-A` shape, so it found nothing — which silently disabled Guard 1 and let wrong LLM dates through. Fixed by making `FIELD_LABELS` a `(label_regex, inline_regex)` tuple and teaching `_label_search` to look ahead to the next line.

**The interesting part:** my first attempt just made the separator optional. That "fix" caused the document title *"CUSTOMER COMPLAINT NOTIFICATION"* to be extracted as the customer name. The two-pattern approach was the correct fix. Worth telling — it shows you validate fixes instead of assuming they worked.

---

# Part 3 — What Happens When You Press Save

1. **`ComplaintForm.jsx`** `onSave()` → dispatches `saveComplaint()`.
2. **`intakeSlice.js`** `saveComplaint` reads `form`, `analysis`, `rawText`, `filename` from state, drops empty values, coerces `quantity_affected` to a number, and `POST`s to `/api/complaints`.
3. **`routers/complaints.py`** `create_complaint()`:
   - `next_complaint_number(db)` issues a sequential ID — `CMP-2026-0001`
   - Inserts the `Complaint` row (17 business fields + status + timestamps)
   - `attach_analysis()` writes an `AIAnalysis` row — risk, completeness, duplicates, root causes, CAPA, summary, and **which engine produced it**, stored in JSON columns
   - `attach_document()` stores the source text and filename for audit
   - Commits — one transaction, all or nothing
4. **Response** → Redux stores `savedComplaint` → green confirmation banner with the complaint number.

### Three tables

| Table | Holds | Relationship |
|-------|-------|--------------|
| `complaints` | The 17 business fields, status, timestamps | parent |
| `ai_analyses` | One row **per agent run** | many-to-one |
| `source_documents` | Original text + filename | many-to-one |

**Why is `ai_analyses` a separate table and not columns on `complaints`?** Because re-analysis is a real workflow — `/api/intake/reanalyze/{id}` re-runs the agent and inserts a *new* row. You keep the full history of what the AI said and when. In a regulated industry (21 CFR Part 11) you must never overwrite a prior assessment.

### Known limitation — volunteer this one

`POST /api/complaints` accepts the `analysis` payload from the client. Convenient for the demo, but in production a user could forge a risk score. The fix is to re-run the agent server-side on save and ignore the client's copy. **Say this before they find it.** Knowing your own weak points reads far better than being caught by them.

---

# Part 4 — Likely Interview Questions

### "Why LangGraph instead of just calling the LLM six times in a loop?"

Three reasons. The topology is **explicit** — the fan-out/fan-in is declared in `build_graph()`, so the concurrency is visible and reviewable rather than buried in `asyncio` calls. The **shared typed state** means nodes communicate through one `AgentState` object instead of me threading arguments through six functions. And it **streams naturally** — LangGraph emits an event per node, which is exactly what the progress bar consumes. A plain loop would give me none of that.

### "How do you stop it hallucinating?"

Six specific guards, all written after observing the actual failure — see Part 2. The one-line principle: **anything I can verify deterministically, I verify.** The model is only trusted with genuinely open judgements like root-cause hypotheses. And even those are labelled *"Hypotheses to investigate — not conclusions"* in the UI.

### "What if Groq is down?"

The app keeps working. Every node has a deterministic fallback and `chat_json()` never raises. You'd see the badge flip to OFFLINE and the analysis get less nuanced, but nothing breaks and no page goes blank. I can demo it — delete the API key and reload.

### "Why did you change the model from the brief?"

`gemma2-9b-it` has been decommissioned by Groq; it returns `400 model_decommissioned`. I tested it, confirmed the failure, and moved to `llama-3.1-8b-instant`, which Groq documents as the successor for fast structured extraction. The substitution is documented in `.env.example`, `config.py` and the README rather than made silently.

### "Walk me through what happens when I upload a PDF."

Use the Part 2 chain: `IntakePanel.handleFile` → `runExtraction` thunk → `POST /api/intake/stream-upload` → `parse_document` → `build_graph()` → 8 nodes → SSE events → `nodeCompleted` reducers → form populates.

### "Why Server-Sent Events and not WebSockets?"

The data only flows one way — server to client — and SSE is a plain HTTP response, so no extra protocol or connection upgrade. WebSockets would be over-engineering for a one-directional progress feed. The one wrinkle is that the browser's `EventSource` is GET-only and I needed to POST a file, so the client reads the stream manually with `fetch`.

### "How would you productionise this?"

Four things, in order:
1. **Recompute the analysis server-side on save** — currently the client's copy is trusted.
2. **Auth and an audit trail** — 21 CFR Part 11 requires attributable, signed records.
3. **Move the agent to a task queue** — a 70b model chain takes seconds; that belongs in Celery with a job ID, not a request thread.
4. **Real duplicate detection** — currently the register snapshot is passed into the prompt, which won't scale past a few thousand complaints. Production wants pgvector embeddings with a similarity index.

### "What was the hardest bug?"

The two-column PDF table one — because it was **silent**. Extraction returned `200 OK` and a fully populated form. The only symptom was that one date was subtly wrong. The regex found nothing, which meant the date-arbitration guard had no value to arbitrate with, so the LLM's wrong date passed through unchallenged. It taught me that a fallback that silently produces nothing is more dangerous than one that throws — and that I should have been asserting on the *extracted values*, not on the status code.

### "What would you do differently?"

Write the heuristic layer first and the LLM layer second. I did it in that order by accident — the fallbacks were meant as safety nets — but it turned out to be the right architecture, because it gave me a deterministic oracle to check the LLM against. Every one of my six guards came from a heuristic and an LLM disagreeing. If I'd built LLM-only I'd have had no way to notice any of them.

---

## Pre-demo checklist

```bash
# 1. Postgres running?
psql -U postgres -c "SELECT 1"

# 2. Backend
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload

# 3. Health should say llm_live: true
curl http://127.0.0.1:8000/api/health

# 4. Frontend
cd frontend && npm run dev
```

Then confirm the **LIVE** badge is showing in the intake panel before you start talking.

### On the API key

Verified: `backend/.env` is gitignored and **has never been committed** — `git log --all -- backend/.env` is empty, and the only tracked env file is `.env.example`, which has a blank key. So pushing to GitHub will not leak it.

Two things still worth doing:
- **Don't show `.env` on screen** while screen-sharing or recording the demo video.
- **Rotate the key afterwards** if the recording is shared publicly, as ordinary hygiene.
