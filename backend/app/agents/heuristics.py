"""Deterministic fallback engine.

Every LangGraph node pairs its LLM prompt with one of these functions. They use
regex + a small pharmaceutical-QA knowledge base rather than a model, which
makes the app fully demoable without a Groq key and gives the LLM path a safety
net when a call fails or returns malformed JSON.
"""
from __future__ import annotations

import re
from datetime import datetime

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

SOURCE_PATTERNS = {
    # Mail headers and addresses are the strongest signal that this arrived by email.
    "Email": r"(\be-?mail\b|\binbox\b|sent from|forwarded message|mailto|^\s*(from|to|subject|cc)\s*:|[\w.+-]+@[\w-]+\.[\w.]+)",
    "Phone": r"\b(phone|call(?:ed)?|telephone|spoke with|voicemail)\b",
    "Customer Portal": r"\b(portal|web ?form|online submission|ticket raised)\b",
    "Field Alert": r"\b(field alert|far\b|field report)\b",
    "Distributor": r"\b(distributor|wholesaler|depot|stockist)\b",
    "Regulatory Body": r"\b(fda|cdsco|mhra|ema|regulator|inspector|health authority)\b",
    "Sales Representative": r"\b(sales rep|medical rep|field officer|territory manager)\b",
}

TYPE_PATTERNS = {
    "Contamination": r"\b(contaminat\w*|foreign (?:particle\w*|matter|body|substance)|particulate matter|(?:black|white|brown|metallic|glass|fibre|fiber) particle\w*|visible particle\w*|microbial|fungal|mould|mold|bio ?burden|cross[- ]contamination|endotoxin|pyrogen)\b",
    # "Appearance" is listed before "Packaging" so that a tie on hit count resolves
    # to the more specific physical-defect classification.
    "Appearance / Physical Defect": r"\b(discolo\w*|colou?r (?:change|patchy)|patchy colou?r|crack\w*|chipped|broken tablet|capping|lamination|mottl\w*|odou?r|smell)\b",
    "Packaging Defect": r"\b(packag\w*|seal(?:ing|ed)?|blister|foil lidding|leak\w*|cap loose|broken bottle|(?:damaged|crushed|torn|dented|open) (?:box|carton|shipper|pack)|tamper)\b",
    "Labelling Error": r"\b(label\w*|mislabel\w*|artwork|printed text|barcode|expiry (?:printed|mismatch))\b",
    "Adverse Event": r"\b(adverse (?:event|reaction)|side ?effect|hospitali[sz]ed|rash|anaphyla\w*|nausea|patient harm|injur\w*)\b",
    "Lack of Efficacy": r"\b(not effective|no relief|lack of efficacy|ineffective|therapeutic failure|did ?n[o']t work)\b",
    "Quantity / Shortage": r"\b(short (?:supply|quantity|shipment)|missing (?:units|vials|bottles)|count mismatch|under ?weight|shortage)\b",
    "Documentation Discrepancy": r"\b(coa\b|certificate of analysis|batch record|document\w* (?:error|discrepanc)|missing (?:coa|document))\b",
    "Product Quality": r"\b(dissolution|assay|impurit\w*|out of specification|oos\b|potency|degrad\w*|sterility|ph (?:value|out))\b",
}

CRITICAL_SIGNALS = r"\b(hospitali[sz]ed|death|fatal|anaphyla\w*|sterility failure|recall|life[- ]threatening|serious adverse|injection site|contaminat\w*|foreign (?:particle\w*|matter|body|substance)|particulate matter|visible particle\w*|(?:black|white|brown|metallic|glass) particle\w*|wrong (?:drug|product|strength)|microbial|endotoxin|patients? (?:received|were given|reported|ingested)|under observation)\b"
MAJOR_SIGNALS = r"\b(oos\b|out of specification|mislabel\w*|seal(?:ing)? failure|leak\w*|discolo\w*|efficacy|potency|impurit\w*|broken|crack\w*)\b"

FIELD_LABELS = {
    "customer_name": r"(?:customer|client|complainant|reported by|hospital|pharmacy|account)\s*(?:name)?\s*[:\-]\s*(.+)",
    "customer_contact": r"(?:contact|email|e-mail|phone|tel|mobile)\s*(?:no\.?|number)?\s*[:\-]\s*(.+)",
    "product_name": r"(?:product|drug|item|material|medicine|preparation)\s*(?:name)?\s*[:\-]\s*(.+)",
    "product_strength": r"(?:strength|grade|dosage|potency|concentration)\s*[:\-]\s*(.+)",
    "batch_number": r"(?:batch|lot|b\.?no|batch/lot)\s*(?:no\.?|number|#)?\s*[:\-]\s*(.+)",
    "manufacturing_date": r"(?:mfg|manufactur\w*|mfd|date of manufacture)\s*(?:date)?\s*[:\-]\s*(.+)",
    "expiry_date": r"(?:exp|expiry|expiration|use before|best before)\s*(?:date)?\s*[:\-]\s*(.+)",
    "complaint_date": r"(?:complaint|report|incident|received|occurrence)\s*(?:date|on)\s*[:\-]\s*(.+)",
    "quantity_affected": r"(?:quantity|qty|affected|units?)\s*(?:affected|involved)?\s*[:\-]\s*(.+)",
}

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%d %b, %Y",
    "%m/%d/%Y", "%b %Y", "%B %Y", "%m/%Y", "%d/%m/%y", "%b-%Y",
]

# Root-cause / CAPA knowledge base, keyed by complaint type.
KNOWLEDGE_BASE: dict[str, dict[str, list[dict]]] = {
    "Contamination": {
        "root_causes": [
            {"cause": "Breach of cleanroom environmental control (HVAC / differential pressure excursion) during the fill stage", "likelihood": "High", "area": "Manufacturing Environment"},
            {"cause": "Inadequate cleaning validation between product changeovers leaving carry-over residue", "likelihood": "Medium", "area": "Cleaning & Changeover"},
            {"cause": "Compromised container-closure integrity allowing ingress during storage or transit", "likelihood": "Medium", "area": "Packaging"},
        ],
        "capa": [
            {"action": "Quarantine the implicated batch and all batches sharing the same line and campaign; issue a stock-hold notice", "type": "Correction", "owner": "QA Head", "due_days": 2},
            {"action": "Review environmental monitoring, differential-pressure and personnel-gowning records for the manufacturing window", "type": "Corrective", "owner": "Production Manager", "due_days": 10},
            {"action": "Re-qualify the cleaning procedure and increase EM sampling frequency on the affected line for three campaigns", "type": "Preventive", "owner": "Validation Lead", "due_days": 30},
        ],
    },
    "Packaging Defect": {
        "root_causes": [
            {"cause": "Sealing temperature or dwell time drifting outside validated range on the blister/filling machine", "likelihood": "High", "area": "Packaging Line"},
            {"cause": "Incoming packaging material out of dimensional specification (foil gauge, cap liner)", "likelihood": "Medium", "area": "Supplier Quality"},
            {"cause": "In-process leak-test sampling frequency insufficient to detect an intermittent defect", "likelihood": "Medium", "area": "In-Process Control"},
        ],
        "capa": [
            {"action": "Hold and physically inspect retained samples of the implicated batch for seal integrity", "type": "Correction", "owner": "QC Manager", "due_days": 3},
            {"action": "Recalibrate and re-qualify the sealing station; review the machine setup log for the batch", "type": "Corrective", "owner": "Engineering Lead", "due_days": 14},
            {"action": "Tighten incoming-material AQL for the packaging component and add supplier scorecard review", "type": "Preventive", "owner": "Supplier Quality", "due_days": 45},
        ],
    },
    "Labelling Error": {
        "root_causes": [
            {"cause": "Superseded artwork version released to the packaging line without change-control verification", "likelihood": "High", "area": "Artwork Control"},
            {"cause": "Line-clearance step not effectively removing the previous product's labels", "likelihood": "High", "area": "Line Clearance"},
            {"cause": "Manual overprint (batch/expiry) set incorrectly at machine setup", "likelihood": "Medium", "area": "Coding & Overprint"},
        ],
        "capa": [
            {"action": "Reconcile label issuance and destruction records for the batch; verify all distributed units", "type": "Correction", "owner": "Packaging Supervisor", "due_days": 3},
            {"action": "Retrain packaging operators on line-clearance SOP with documented effectiveness check", "type": "Corrective", "owner": "Training Coordinator", "due_days": 21},
            {"action": "Implement vision-system barcode/text verification at 100% on the coding station", "type": "Preventive", "owner": "Engineering Lead", "due_days": 60},
        ],
    },
    "Adverse Event": {
        "root_causes": [
            {"cause": "Product-related quality attribute (impurity, degradation or potency deviation) contributing to the reaction", "likelihood": "Medium", "area": "Product Quality"},
            {"cause": "Patient-specific factor or known labelled reaction rather than a batch defect", "likelihood": "Medium", "area": "Pharmacovigilance"},
            {"cause": "Administration or dosing error at the point of care", "likelihood": "Low", "area": "Clinical Use"},
        ],
        "capa": [
            {"action": "Escalate to Pharmacovigilance within 24 hours and assess expedited regulatory reportability", "type": "Correction", "owner": "PV Officer", "due_days": 1},
            {"action": "Pull batch records and full release testing data; test retention samples for impurity profile", "type": "Corrective", "owner": "QC Manager", "due_days": 10},
            {"action": "Trend the reaction against the product's historical safety signal database", "type": "Preventive", "owner": "PV Lead", "due_days": 30},
        ],
    },
    "Lack of Efficacy": {
        "root_causes": [
            {"cause": "Dissolution or content-uniformity drift within specification but at the edge of the validated range", "likelihood": "Medium", "area": "Formulation"},
            {"cause": "Storage or transport temperature excursion degrading the active ingredient", "likelihood": "Medium", "area": "Cold Chain / Distribution"},
            {"cause": "Patient non-adherence or inappropriate indication rather than a product defect", "likelihood": "Medium", "area": "Clinical Use"},
        ],
        "capa": [
            {"action": "Test retention samples for assay, dissolution and content uniformity against release data", "type": "Correction", "owner": "QC Manager", "due_days": 7},
            {"action": "Review the distribution temperature-monitoring records for the consignment", "type": "Corrective", "owner": "Logistics QA", "due_days": 14},
            {"action": "Trend efficacy complaints for this product across the last 12 batches", "type": "Preventive", "owner": "QA Analyst", "due_days": 30},
        ],
    },
    "Appearance / Physical Defect": {
        "root_causes": [
            {"cause": "Compression parameter drift causing capping, lamination or friability issues", "likelihood": "High", "area": "Compression"},
            {"cause": "Moisture ingress during storage due to inadequate desiccant or closure fit", "likelihood": "Medium", "area": "Packaging / Storage"},
            {"cause": "Excipient or colourant lot variability affecting appearance", "likelihood": "Medium", "area": "Raw Material"},
        ],
        "capa": [
            {"action": "Inspect retention samples and photograph the defect for the investigation file", "type": "Correction", "owner": "QC Analyst", "due_days": 3},
            {"action": "Review compression in-process data (hardness, friability, weight variation) for the batch", "type": "Corrective", "owner": "Production Manager", "due_days": 14},
            {"action": "Add accelerated stability monitoring for the affected pack configuration", "type": "Preventive", "owner": "Stability Lead", "due_days": 45},
        ],
    },
    "Quantity / Shortage": {
        "root_causes": [
            {"cause": "Reconciliation error at the packaging or dispatch stage", "likelihood": "High", "area": "Packaging / Dispatch"},
            {"cause": "Pilferage or damage during transit", "likelihood": "Medium", "area": "Logistics"},
            {"cause": "Counting-machine miscalibration at the filling stage", "likelihood": "Medium", "area": "Filling"},
        ],
        "capa": [
            {"action": "Reconcile dispatch documentation and shipper weights against the customer's receipt record", "type": "Correction", "owner": "Warehouse Manager", "due_days": 5},
            {"action": "Recalibrate the counting/filling equipment and verify with a challenge test", "type": "Corrective", "owner": "Engineering Lead", "due_days": 14},
            {"action": "Introduce tamper-evident shipper seals with serial capture at dispatch", "type": "Preventive", "owner": "Logistics QA", "due_days": 60},
        ],
    },
    "Documentation Discrepancy": {
        "root_causes": [
            {"cause": "Transcription error when issuing the certificate of analysis", "likelihood": "High", "area": "QC Documentation"},
            {"cause": "Batch record review not catching an incomplete or contradictory entry", "likelihood": "Medium", "area": "Batch Release"},
        ],
        "capa": [
            {"action": "Issue a corrected, version-controlled document to the customer with a covering note", "type": "Correction", "owner": "QA Documentation", "due_days": 3},
            {"action": "Perform a retrospective review of the last 10 CoAs issued for this product", "type": "Corrective", "owner": "QC Manager", "due_days": 21},
            {"action": "Move CoA generation to an automated LIMS-driven template to remove manual transcription", "type": "Preventive", "owner": "IT / LIMS Lead", "due_days": 90},
        ],
    },
}

DEFAULT_KNOWLEDGE = {
    "root_causes": [
        {"cause": "Process parameter deviation during manufacture of the implicated batch", "likelihood": "Medium", "area": "Manufacturing"},
        {"cause": "Raw material or component variability from the supplier", "likelihood": "Medium", "area": "Supplier Quality"},
        {"cause": "Storage or distribution condition excursion after release", "likelihood": "Low", "area": "Distribution"},
    ],
    "capa": [
        {"action": "Quarantine remaining stock of the implicated batch pending investigation", "type": "Correction", "owner": "QA Head", "due_days": 3},
        {"action": "Open a formal deviation investigation and review the full batch manufacturing record", "type": "Corrective", "owner": "QA Investigator", "due_days": 21},
        {"action": "Trend this complaint against historical complaints for the same product family", "type": "Preventive", "owner": "QA Analyst", "due_days": 45},
    ],
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _clean(value: str) -> str:
    value = value.strip().strip("*|").strip()
    value = re.split(r"\s{3,}|\s*\|\s*", value)[0]
    return value.strip(" .,;:-").strip()


def parse_date(value: str | None) -> str | None:
    """Best-effort date normalisation to ISO ``YYYY-MM-DD``."""
    if not value:
        return None
    raw = _clean(value)
    raw = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1", raw, flags=re.I)
    match = re.search(
        r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|"
        r"\d{1,2}[ \-][A-Za-z]{3,9}[ \-,]+\d{2,4}|[A-Za-z]{3,9}[ \-]\d{1,2},?[ \-]\d{2,4}|"
        r"[A-Za-z]{3,9}[ \-]\d{4})",
        raw,
    )
    candidate = match.group(1) if match else raw
    candidate = candidate.replace(",", " ").replace(".", "/")
    candidate = re.sub(r"\s+", " ", candidate).strip()

    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(candidate, fmt)
        except ValueError:
            continue
        # "Feb 2026" style expiry -> treat as end of that month.
        if fmt in {"%b %Y", "%B %Y", "%m/%Y", "%b-%Y"}:
            month, year = parsed.month, parsed.year
            next_month = datetime(year + (month == 12), month % 12 + 1, 1)
            return (next_month - __import__("datetime").timedelta(days=1)).date().isoformat()
        return parsed.date().isoformat()
    return None


def _label_search(text: str, pattern: str) -> str | None:
    for line in text.splitlines():
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            value = _clean(match.group(1))
            if value and value.lower() not in {"n/a", "na", "none", "-", "tbd", "unknown"}:
                return value
    return None


def _match_vocab(text: str, patterns: dict[str, str]) -> str | None:
    """Pick the label with the most keyword hits; dict order breaks ties."""
    scores: dict[str, int] = {}
    for label, pattern in patterns.items():
        hits = len(re.findall(pattern, text, re.IGNORECASE | re.MULTILINE))
        if hits:
            scores[label] = hits
    if not scores:
        return None
    return max(scores.items(), key=lambda kv: kv[1])[0]


# --------------------------------------------------------------------------
# Node fallbacks
# --------------------------------------------------------------------------


def extract_fields(text: str) -> dict:
    """Regex-driven field extraction over a complaint document."""
    fields: dict = {}
    confidence: dict = {}

    for field, pattern in FIELD_LABELS.items():
        value = _label_search(text, pattern)
        if value:
            fields[field] = value
            confidence[field] = 0.82

    # Normalise dates.
    for date_field in ("manufacturing_date", "expiry_date", "complaint_date"):
        if date_field in fields:
            iso = parse_date(fields[date_field])
            if iso:
                fields[date_field] = iso
            else:
                fields.pop(date_field)
                confidence.pop(date_field, None)

    # Quantity: split the number from its unit.
    if "quantity_affected" in fields:
        qty_match = re.search(
            r"([\d,]+(?:\.\d+)?)\s*(kg|g|mg|units?|tablets?|vials?|bottles?|boxes|strips?|litres?|l\b|ml)?",
            str(fields["quantity_affected"]),
            re.IGNORECASE,
        )
        if qty_match:
            fields["quantity_affected"] = float(qty_match.group(1).replace(",", ""))
            if qty_match.group(2):
                fields["quantity_unit"] = qty_match.group(2).lower()
                confidence["quantity_unit"] = 0.8
        else:
            fields.pop("quantity_affected")
            confidence.pop("quantity_affected", None)

    # Batch numbers are usually alphanumeric tokens; fall back to a free scan.
    # The token must contain a digit, otherwise phrases like "batch number" or
    # "lot details" match the following English word and become a fake batch.
    if "batch_number" not in fields:
        loose = re.search(
            r"\b(?:batch|lot)\b[^A-Za-z0-9]{0,8}((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{3,})",
            text,
        )
        if loose:
            fields["batch_number"] = loose.group(1).strip()
            confidence["batch_number"] = 0.6

    # Strength embedded in the product name, e.g. "Amoxicillin 500 mg".
    if "product_strength" not in fields:
        strength = re.search(r"\b(\d+(?:\.\d+)?\s?(?:mg|mcg|g|iu|%|mg/ml|ml))\b", text, re.I)
        if strength:
            fields["product_strength"] = strength.group(1).strip()
            confidence["product_strength"] = 0.65

    source = _match_vocab(text, SOURCE_PATTERNS)
    if source:
        fields["complaint_source"] = source
        confidence["complaint_source"] = 0.7

    ctype = _match_vocab(text, TYPE_PATTERNS)
    if ctype:
        fields["complaint_type"] = ctype
        confidence["complaint_type"] = 0.75

    # Description: prefer an explicit block, else the longest paragraph.
    desc = re.search(
        r"(?:description|details|issue|observation|nature of complaint|complaint description)\s*[:\-]\s*(.+?)(?:\n\s*\n|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if desc:
        fields["description"] = re.sub(r"\s+", " ", desc.group(1)).strip()[:2000]
        confidence["description"] = 0.85
    else:
        paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
        paragraphs = [p for p in paragraphs if len(p) > 80]
        if paragraphs:
            fields["description"] = max(paragraphs, key=len)[:2000]
            confidence["description"] = 0.6

    if "customer_name" not in fields:
        org = re.search(
            r"\b([A-Z][A-Za-z&.\-]+(?:\s+[A-Z][A-Za-z&.\-]+){0,4}\s+"
            r"(?:Hospital|Pharmacy|Pharmaceuticals?|Healthcare|Medical Centre|Medical Center|Clinic|Labs?|Laboratories|Distributors?|Ltd\.?|Limited|Inc\.?|Pvt\.?))\b",
            text,
        )
        if org:
            fields["customer_name"] = org.group(1).strip()
            confidence["customer_name"] = 0.55

    return {"fields": fields, "confidence": confidence}


REQUIRED_FIELDS = {
    "complaint_source": "Complaint Source",
    "customer_name": "Customer Name",
    "product_name": "Product Name",
    "batch_number": "Batch / Lot Number",
    "complaint_type": "Complaint Type",
    "complaint_date": "Complaint Date",
    "description": "Detailed Complaint Description",
}
OPTIONAL_FIELDS = {
    "product_strength": "Product Strength / Grade",
    "manufacturing_date": "Manufacturing Date",
    "expiry_date": "Expiry Date",
    "quantity_affected": "Quantity Affected",
    "customer_contact": "Customer Contact",
}


def completeness(fields: dict) -> dict:
    def present(key: str) -> bool:
        value = fields.get(key)
        return value not in (None, "", [], {})

    missing_required = [label for key, label in REQUIRED_FIELDS.items() if not present(key)]
    missing_optional = [label for key, label in OPTIONAL_FIELDS.items() if not present(key)]

    required_score = (len(REQUIRED_FIELDS) - len(missing_required)) / len(REQUIRED_FIELDS)
    optional_score = (len(OPTIONAL_FIELDS) - len(missing_optional)) / len(OPTIONAL_FIELDS)
    score = round((required_score * 0.8 + optional_score * 0.2) * 100)

    if missing_required:
        notes = (
            f"{len(missing_required)} mandatory field(s) could not be sourced from the document: "
            f"{', '.join(missing_required)}. These must be completed before the complaint can be triaged."
        )
    elif missing_optional:
        notes = (
            "All mandatory fields captured. Supporting detail still open: "
            f"{', '.join(missing_optional)}. Request these from the complainant to strengthen the investigation."
        )
    else:
        notes = "All mandatory and supporting fields captured. The record is ready for QA triage."

    return {
        "completeness_score": score,
        "missing_fields": missing_required + [f"{m} (optional)" for m in missing_optional],
        "completeness_notes": notes,
    }


def risk(fields: dict, text: str) -> dict:
    blob = f"{text}\n{fields.get('description', '')}"
    ctype = fields.get("complaint_type") or ""

    score = 25
    reasons: list[str] = []

    critical_hits = re.findall(CRITICAL_SIGNALS, blob, re.IGNORECASE)
    major_hits = re.findall(MAJOR_SIGNALS, blob, re.IGNORECASE)

    if critical_hits:
        score += 45
        reasons.append(
            f"patient-safety / sterility signals detected ({', '.join(sorted({h.lower() for h in critical_hits})[:3])})"
        )
    if major_hits:
        score += 18
        reasons.append(
            f"quality-attribute signals detected ({', '.join(sorted({h.lower() for h in major_hits})[:3])})"
        )
    if ctype in {"Contamination", "Adverse Event"}:
        score += 15
        reasons.append(f"complaint type '{ctype}' carries inherent regulatory exposure")
    elif ctype in {"Labelling Error", "Product Quality", "Lack of Efficacy"}:
        score += 8
        reasons.append(f"complaint type '{ctype}' can affect product identity or performance")

    qty = fields.get("quantity_affected")
    if isinstance(qty, (int, float)) and qty >= 100:
        score += 8
        reasons.append(f"a large quantity is affected ({qty:g} {fields.get('quantity_unit', 'units')})")

    if re.search(r"\b(multiple (?:batches|lots)|several units|recurring|repeat complaint|third time)\b", blob, re.I):
        score += 10
        reasons.append("wording suggests a recurring or multi-batch issue")

    score = max(5, min(99, score))

    if score >= 70:
        level, severity, priority = "Critical", "Critical", "P1 - Urgent"
    elif score >= 50:
        level, severity, priority = "High", "Major", "P2 - High"
    elif score >= 32:
        level, severity, priority = "Medium", "Major", "P3 - Medium"
    else:
        level, severity, priority = "Low", "Minor", "P4 - Low"

    reportable = bool(critical_hits) or ctype in {"Contamination", "Adverse Event"}

    rationale = (
        f"Scored {score}/100 ({level}). "
        + (
            "Drivers: " + "; ".join(reasons) + "."
            if reasons
            else "No elevated safety or quality signals were found in the narrative."
        )
        + (
            " Assess for expedited regulatory reporting (e.g. FDA Field Alert within 3 working days)."
            if reportable
            else " No expedited regulatory reporting trigger identified."
        )
    )

    return {
        "risk_level": level,
        "risk_score": score,
        "risk_rationale": rationale,
        "regulatory_reportable": reportable,
        "suggested_severity": severity,
        "suggested_priority": priority,
    }


def root_causes(fields: dict) -> dict:
    kb = KNOWLEDGE_BASE.get(fields.get("complaint_type") or "", DEFAULT_KNOWLEDGE)
    return {"root_causes": kb["root_causes"]}


def capa(fields: dict) -> dict:
    kb = KNOWLEDGE_BASE.get(fields.get("complaint_type") or "", DEFAULT_KNOWLEDGE)
    return {"capa_recommendations": kb["capa"]}


def summary(fields: dict, risk_result: dict) -> str:
    product = fields.get("product_name") or "an unidentified product"
    strength = f" {fields['product_strength']}" if fields.get("product_strength") else ""
    batch = fields.get("batch_number") or "an unrecorded batch"
    customer = fields.get("customer_name") or "an unnamed complainant"
    ctype = fields.get("complaint_type") or "quality"
    source = fields.get("complaint_source") or "an unspecified channel"
    when = fields.get("complaint_date") or "an unrecorded date"
    qty = (
        f" Approximately {fields['quantity_affected']:g} {fields.get('quantity_unit', 'units')} are affected."
        if isinstance(fields.get("quantity_affected"), (int, float))
        else ""
    )
    detail = (fields.get("description") or "").strip()
    detail_sentence = f" Reported detail: {detail[:260]}{'...' if len(detail) > 260 else ''}" if detail else ""

    return (
        f"{customer} raised a {ctype.lower()} complaint via {source.lower()} on {when} concerning "
        f"{product}{strength}, batch {batch}.{qty}{detail_sentence} "
        f"Automated triage rates this {risk_result.get('risk_level', 'Medium')} risk "
        f"({risk_result.get('risk_score', 50)}/100), suggesting "
        f"{risk_result.get('suggested_severity', 'Major')} severity at "
        f"{risk_result.get('suggested_priority', 'P3 - Medium')}."
    )
