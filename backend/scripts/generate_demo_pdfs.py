"""Generate five demo complaint PDFs for the assessment walkthrough.

Each document is engineered to make a different part of the agent visible:

    D1  Critical contamination     -> Critical risk, reportable, contamination CAPA
    D2  Cold-chain efficacy        -> Lack of Efficacy, distribution root causes
    D3  Wrong-strength labelling   -> Labelling Error, patient-safety escalation
    D4  Sterile injectable AE      -> Adverse Event, pharmacovigilance path
    D5  Sparse / vague report      -> Completeness checker fires, low risk

Run:  python scripts/generate_demo_pdfs.py
Out:  backend/samples/demo/D1..D5 .pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent.parent / "samples" / "demo"

_base = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_base["Heading1"], fontSize=15, spaceAfter=2, textColor=colors.HexColor("#12305c"))
SUB = ParagraphStyle("SUB", parent=_base["Normal"], fontSize=9.5, textColor=colors.HexColor("#5a6472"), spaceAfter=10)
H3 = ParagraphStyle("H3", parent=_base["Heading3"], fontSize=10.5, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#12305c"))
BODY = ParagraphStyle("BODY", parent=_base["Normal"], fontSize=9.8, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=7)
SMALL = ParagraphStyle("SMALL", parent=_base["Normal"], fontSize=8.6, textColor=colors.HexColor("#5a6472"))


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", SMALL), Paragraph(v, ParagraphStyle("v", parent=SMALL, textColor=colors.black))] for k, v in rows]
    table = Table(data, colWidths=[52 * mm, 108 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dfe4ea")),
            ]
        )
    )
    return table


def build(filename: str, title: str, subtitle: str, meta: list[tuple[str, str]], sections: list[tuple[str, list[str]]], footer: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
    )

    flow: list = [Paragraph(title, H1), Paragraph(subtitle, SUB), HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#12305c")), Spacer(1, 8), _kv_table(meta)]
    for heading, paras in sections:
        flow.append(Paragraph(heading, H3))
        for p in paras:
            flow.append(Paragraph(p, BODY))
    flow += [Spacer(1, 10), HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#dfe4ea")), Spacer(1, 5), Paragraph(footer, SMALL)]

    doc.build(flow)
    return path


# --------------------------------------------------------------------------
# D1 — Critical contamination (Critical risk, regulatory reportable)
# --------------------------------------------------------------------------
D1 = dict(
    filename="D1_contamination_critical.pdf",
    title="CUSTOMER COMPLAINT NOTIFICATION",
    subtitle="Aurora Biocare Ltd &mdash; Quality Assurance Department &mdash; Ref ABC/QA/2026/0412",
    meta=[
        ("Complaint Source", "Distributor"),
        ("Customer Name", "Beacon Hospital Group Pharmacy"),
        ("Contact", "qa.pharmacy@beaconhospital.org / +44 20 7946 0733"),
        ("Product Name", "Cefuroxime Sodium for Injection"),
        ("Strength / Grade", "750 mg vial"),
        ("Batch No", "CFZ-6621-A"),
        ("Mfg Date", "14/03/2025"),
        ("Expiry Date", "13/03/2027"),
        ("Quantity Affected", "84 vials"),
        ("Complaint Date", "19/06/2026"),
    ],
    sections=[
        (
            "NATURE OF COMPLAINT",
            [
                "Description: During reconstitution ahead of a scheduled theatre list, the ward pharmacist "
                "observed distinct grey-black particulate matter suspended in the reconstituted solution in "
                "six separate vials from this batch. The particles did not dissolve after two minutes of gentle "
                "agitation and remained visible against both light and dark backgrounds. Under a hand lens the "
                "particles appear fibrous rather than crystalline, which is inconsistent with undissolved active.",
                "One patient received a partial dose from an affected vial before the pharmacist intervened. "
                "The patient developed a low-grade pyrexia within ninety minutes and was moved to the high "
                "dependency unit for observation as a precaution. No lasting harm has been reported at the time "
                "of writing, and the attending consultant has been informed of the suspected product defect.",
                "All remaining 78 vials of this batch have been quarantined in a segregated cage under the "
                "control of the Chief Pharmacist. Photographs and two retained affected vials are available for "
                "collection. Given the sterile route of administration and the confirmed patient exposure, we "
                "consider this a critical defect and request an urgent response within 24 hours.",
            ],
        ),
    ],
    footer="Reported by: Dr Ifeoma Nwosu, Chief Pharmacist, Beacon Hospital Group &mdash; escalated to Aurora Biocare QA on 19 June 2026.",
)

# --------------------------------------------------------------------------
# D2 — Cold-chain / lack of efficacy
# --------------------------------------------------------------------------
D2 = dict(
    filename="D2_efficacy_coldchain.pdf",
    title="PRODUCT COMPLAINT &mdash; SUSPECTED LOSS OF POTENCY",
    subtitle="Received via customer portal &mdash; Ticket #PC-2026-11840",
    meta=[
        ("Complaint Source", "Customer Portal"),
        ("Customer Name", "Silverbrook Retail Pharmacy Chain"),
        ("Contact", "clinical@silverbrookpharmacy.co.uk"),
        ("Product Name", "Insulin Glargine Injection"),
        ("Strength / Grade", "100 IU/mL, 3 mL pen"),
        ("Batch No", "ING-4417-D"),
        ("Mfg Date", "08/09/2025"),
        ("Expiry Date", "07/09/2027"),
        ("Quantity Affected", "150 pens"),
        ("Complaint Date", "02/07/2026"),
    ],
    sections=[
        (
            "NATURE OF COMPLAINT",
            [
                "Description: Four separate patients dispensed from this batch across two branches have "
                "reported that their fasting blood glucose readings have risen materially over the past three "
                "weeks despite no change to diet, dosing schedule or injection technique. Two patients report "
                "morning readings 4&ndash;6 mmol/L above their established baseline. One patient required an "
                "unscheduled diabetic clinic review and a temporary dose increase.",
                "On inspection the pens appear physically normal, correctly labelled and within expiry, with no "
                "visible cloudiness or particulate. However, our goods-in temperature logger for the consignment "
                "containing this batch recorded an excursion to 19.4 degrees Celsius sustained for approximately "
                "eleven hours during transit on 04 June 2026, against the labelled storage requirement of 2 to 8 "
                "degrees Celsius. We suspect a cold-chain failure has degraded the active ingredient.",
                "We are seeking confirmation of whether this batch should be recalled from patient use and "
                "whether the recorded excursion is sufficient to compromise potency. Remaining stock has been "
                "moved to quarantine pending your assessment. The temperature logger export is attached to the "
                "portal ticket.",
            ],
        ),
    ],
    footer="Reported by: Marcus Delaney, Superintendent Pharmacist, Silverbrook Retail Pharmacy Chain.",
)

# --------------------------------------------------------------------------
# D3 — Wrong-strength labelling error
# --------------------------------------------------------------------------
D3 = dict(
    filename="D3_labelling_wrong_strength.pdf",
    title="URGENT &mdash; LABELLING DISCREPANCY REPORT",
    subtitle="Goods-in inspection finding &mdash; delivery hold applied",
    meta=[
        ("Complaint Source", "Distributor"),
        ("Customer Name", "Kingsway Wholesale Distribution Ltd"),
        ("Contact", "goodsin@kingswaywholesale.co.uk"),
        ("Product Name", "Warfarin Sodium Tablets"),
        ("Strength / Grade", "3 mg"),
        ("Batch No", "WAR-2208-F"),
        ("Mfg Date", "21/01/2026"),
        ("Expiry Date", "20/01/2028"),
        ("Quantity Affected", "2400 tablets"),
        ("Complaint Date", "11/07/2026"),
    ],
    sections=[
        (
            "NATURE OF COMPLAINT",
            [
                "Description: During routine goods-in verification our inspector identified that approximately "
                "80 cartons within this delivery bear an outer carton label stating a strength of 5 mg, while the "
                "blister foil inside each carton and the carton end-flap overprint both correctly state 3 mg. The "
                "2D barcode on the mislabelled cartons resolves to the 5 mg product code in our warehouse "
                "management system.",
                "This is a wrong-strength labelling defect on an anticoagulant with a narrow therapeutic index. "
                "Had the discrepancy not been intercepted at goods-in, these units would have been picked, "
                "shipped and dispensed as 5 mg, representing a 67 percent overdose relative to the tablets "
                "actually present. For a warfarin patient this carries a credible risk of serious bleeding events.",
                "The entire delivery has been placed on administrative hold and physically segregated in our "
                "quarantine bay. We require written confirmation of the full scope of the affected batch, "
                "including whether any units from this packaging run were released to other customers, before we "
                "will accept any further stock of this product.",
            ],
        ),
    ],
    footer="Reported by: Sandra Iqbal, Goods-In Supervisor, Kingsway Wholesale Distribution Ltd &mdash; countersigned by Responsible Person.",
)

# --------------------------------------------------------------------------
# D4 — Adverse event, sterile injectable
# --------------------------------------------------------------------------
D4 = dict(
    filename="D4_adverse_event_reaction.pdf",
    title="FIELD ALERT &mdash; ADVERSE REACTION REPORT",
    subtitle="Reported via territory manager &mdash; expedited handling requested",
    meta=[
        ("Complaint Source", "Sales Representative"),
        ("Customer Name", "Northfield Regional Medical Centre"),
        ("Contact", "a.castellano@northfieldrmc.health"),
        ("Product Name", "Iohexol Contrast Injection"),
        ("Strength / Grade", "350 mg I/mL, 100 mL bottle"),
        ("Batch No", "IOH-9075-C"),
        ("Mfg Date", "05/02/2026"),
        ("Expiry Date", "04/02/2028"),
        ("Quantity Affected", "22 bottles"),
        ("Complaint Date", "23/07/2026"),
    ],
    sections=[
        (
            "EVENT NARRATIVE",
            [
                "Description: Five patients undergoing contrast-enhanced imaging on 21 and 22 July developed "
                "acute hypersensitivity reactions within fifteen minutes of administration from bottles drawn "
                "from this batch. Presentations included widespread urticarial rash in all five, facial and "
                "periorbital swelling in three, and bronchospasm with oxygen desaturation in one. The patient "
                "with bronchospasm, a 54-year-old female with no documented contrast allergy, was treated with "
                "intramuscular adrenaline and admitted overnight for monitoring.",
                "The radiology department notes that the observed reaction rate for these two days is markedly "
                "above the historical baseline for this product at this site, and that all five affected patients "
                "received contrast from the same batch. Two patients imaged on the same days using stock from a "
                "different batch experienced no reaction.",
                "On visual inspection the solution in the remaining bottles is clear and colourless with no "
                "visible particulate, and all bottles are within expiry and correctly labelled. The department "
                "has suspended use of this batch and quarantined the remaining 22 bottles pending investigation. "
                "A possible endotoxin or leachable-related aetiology has been raised by the consultant "
                "radiologist and should be evaluated.",
            ],
        ),
    ],
    footer="Reported by: Alessandro Castellano, Territory Manager, on behalf of Dr H.Ravindran, Consultant Radiologist.",
)

# --------------------------------------------------------------------------
# D5 — Sparse / vague phone report (completeness checker demo)
# --------------------------------------------------------------------------
D5 = dict(
    filename="D5_incomplete_vague_report.pdf",
    title="CUSTOMER CARE CALL LOG",
    subtitle="Inbound telephone contact &mdash; unresolved, callback pending",
    meta=[
        ("Complaint Source", "Phone"),
        ("Call Date", "26/07/2026"),
        ("Handled By", "R. Ncube, Customer Care Advisor"),
        ("Call Duration", "6 minutes"),
        ("Outcome", "Insufficient detail captured &mdash; callback requested"),
    ],
    sections=[
        (
            "CALL NOTES",
            [
                "Caller telephoned the customer care line to report a problem with what she described as "
                "&ldquo;my heart tablets&rdquo;. She stated that some of the tablets in the most recent pack "
                "&ldquo;look wrong&rdquo; &mdash; specifically that the colour is uneven across the tablet "
                "surface and that two or three tablets were chipped at the edge when she opened the blister.",
                "The caller did not have the carton or blister to hand at the time of the call and was therefore "
                "unable to provide a batch number, an expiry date, or the product strength. She was not certain "
                "of the full product name and could not confirm which pharmacy dispensed it. She reported no "
                "adverse symptoms and confirmed she has not taken any of the affected tablets.",
                "Advisor requested that the caller retain the affected pack and telephone back with the carton "
                "details so the complaint can be formally logged and investigated. Caller agreed. No product "
                "identification was possible during this call, and no quantity could be established.",
            ],
        ),
    ],
    footer="Note: this record is intentionally incomplete. It cannot be triaged until product and batch identification are obtained.",
)


def main() -> None:
    written = [build(**spec) for spec in (D1, D2, D3, D4, D5)]
    print(f"Wrote {len(written)} demo PDFs to {OUT}\n")
    for path in written:
        print(f"  {path.name:<38} {path.stat().st_size:>7,} bytes")


if __name__ == "__main__":
    main()
