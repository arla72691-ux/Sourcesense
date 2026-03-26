# PHASE 2 — RFQ & EVALUATION AGENTS (RFQ.04 → EVAL.10)
## Paste into OpenCode-Vertex-Gemini 2.5 Pro

---

## CONTEXT

You are continuing to build **Sourcesense** in Python + LangGraph. Phase 1 files (`state.py`, `db.py`, `config.py`, `agents/pr_01-03`, `graphs/phase1_graph.py`) already exist. Do not regenerate them. Import from them.

**Generate executable Python files only. No n8n JSON.**

---

## IMPORTS TO USE

```python
from state import S2CState
from db import get_db
from config import GEMINI_API_KEY, DMS_ROOT, SMTP_CONFIG
import google.generativeai as genai
import sqlite3, os, smtplib, logging
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
```

---

## DATABASE SCHEMA (new tables used in Phase 2)

### RFQ_Log (WRITE)
```
RFQ_ID (PK), Consolidation_Cluster_ID, RFQ_Status, Evaluation_Criteria,
Submission_Deadline, Created_By, Created_At, Updated_At
```
RFQ_Status values: Draft → Ready_For_Approval → Approved → Dispatched → Submissions_Closed

### Vendor_Shortlist (WRITE)
```
Shortlist_ID (PK), RFQ_ID, Vendor_Code, Shortlist_Reason, Historical_Score, Added_At
```

### RFQ_Dispatch_Log (WRITE)
```
Dispatch_ID (PK), RFQ_ID, Vendor_Code, Dispatch_Method, Dispatched_At, Delivery_Status
```

### RFQ_Submissions (READ/WRITE)
```
Submission_ID (PK), RFQ_ID, Vendor_Code, Quoted_Unit_Price, Lead_Time_Days,
Submission_File_ID, Submitted_At
```

### RFQ_Tech_Evaluations (WRITE)
```
Tech_Eval_ID (PK), Submission_ID, Tech_Score (0-100), Tech_Remarks
```

### RFQ_Comm_Evaluations (WRITE)
```
Comm_Eval_ID (PK), Submission_ID, Price_Score (0-100), Payment_Score (0-100),
Delivery_Score (0-100), Comm_Remarks
```

### RFQ_Overall_Evaluations (WRITE)
```
Overall_Eval_ID (PK), Submission_ID, Tech_Weighted_Score, Comm_Weighted_Score,
Overall_Score
```

### SVJ_Log (WRITE — only if < 3 vendors)
```
SVJ_ID (PK), RFQ_ID, Justification_Reason, Supporting_Doc_File_ID,
Approval_Status, Created_By, Created_At, Approved_By, Decided_At
```

### Supplier_Master (READ)
```
Supplier_Code (=Vendor_Code), Overall_Score, Status, Last_Evaluation_Date
```

### Monthly_Performance (READ)
```
Supplier_Code, Month, Year, Quality_Incidents, Delivery_On_Time_Pct
```

### Vendor_History (READ)
```
Vendor_Code, Material_Code, Last_PO_Date, Last_PO_Price, Total_POs_12M,
Avg_Delivery_Days, Quality_Rating
```

### Onboarding_Tracker (READ)
```
Onboarding_ID, GST_Number, PAN_Valid, GST_Valid, Finance_Decision, Vendor_Activated_At
```

### Procurement_Historical_Pricing (READ)
```
Pricing_ID, Material_Code, Vendor_Code, PO_Date, Unit_Price, Quantity, Currency
```

---

## PHASE 2: GENERATE THESE FILES

### FILE 1: `agents/rfq_04_vendor_shortlisting.py`

**Process ID:** S2C.RFQ.04
**LangGraph node name:** `vendor_shortlisting`

```python
def vendor_shortlisting(state: S2CState) -> S2CState:
    """
    For each cluster with PR_Status = 'Buyer_Assigned':

    1. Get Material_Code and Material_Group from Consolidated_PRs
    2. Query Vendor_Master WHERE Active_Status='Active' AND Blacklisted=0
    3. Join Supplier_Master for Overall_Score
    4. Join Monthly_Performance (last 3 months): SUM(Quality_Incidents),
       AVG(Delivery_On_Time_Pct)
    5. Join Vendor_History WHERE Material_Code matches: get Total_POs_12M,
       Last_PO_Price, Quality_Rating
    6. CTRL-007: Hard exclude any vendor with Blacklisted=1 → log to Compliance_Log
    7. CTRL-008: Check Onboarding_Tracker via GSTIN match on Vendor_Master.GSTIN.
       Finance_Decision must = 'Approved'. If not, exclude + log.
    8. Build scoring dict per vendor:
       score = (Overall_Score * 0.4) + (Delivery_On_Time_Pct_avg * 0.3)
               + (material_experience_score * 0.3)
       where material_experience_score = 100 if Total_POs_12M > 5, else 60 if > 0, else 30
    9. Call Gemini to review the scoring and recommend final shortlist (top 3-5):
       Prompt: "Review these vendor scores for {material}. Recommend 3-5 vendors
       considering: compliance history, material-specific experience, MSME diversity
       (prefer including at least 1 MSME vendor if available). Output JSON:
       [{vendor_code, reason, recommended_rank}]"
    10. INSERT Vendor_Shortlist for each recommended vendor
    11. UPDATE Consolidated_PRs.PR_Status = 'Vendors_Shortlisted'
    12. INSERT Compliance_Log for CTRL-007, CTRL-008
    13. INSERT Process_Events_Log
    """
```

---

### FILE 2: `agents/rfq_05_rfq_creation.py`

**Process ID:** S2C.RFQ.05
**LangGraph node name:** `rfq_creation`

```python
def rfq_creation(state: S2CState) -> S2CState:
    """
    For each cluster with PR_Status = 'Vendors_Shortlisted':

    1. Read cluster details (material, qty, value, delivery date, payment terms)
    2. If Payment_Terms is NULL, set defaults:
       - OPEX + value < 500,000 → "Net 30 days from GRN"
       - OPEX + value >= 500,000 → "Net 45 days from GRN"
       - CAPEX → "Net 45 days from GRN"
    3. UPDATE Consolidated_PRs.Payment_Terms and Comm_Terms_Received_At = now()
    4. Generate RFQ_ID: f"RFQ-{year}-{seq:05d}" (next sequence from RFQ_Log)
    5. Set Submission_Deadline = now() + 7 business days
       (skip Saturday/Sunday in calculation)
    6. Set Evaluation_Criteria = "Tech: 40%, Comm: 60%, Min score: 70"
    7. INSERT RFQ_Log with RFQ_Status = 'Draft'
    8. Generate RFQ document text (use Gemini or template):
       - Header: Company name, RFQ number, date
       - Material details: code, description, specs, qty, UOM, HSN code
       - Commercial terms: delivery date, payment terms, incoterms
       - Evaluation criteria and submission deadline
    9. Save RFQ doc to DMS: f"{DMS_ROOT}/RFQ/RFQ_{rfq_id}.txt"
    10. INSERT DMS_Documents record
    11. UPDATE Consolidated_PRs: RFQ_ID, RFQ_Generated_At, PR_Status='RFQ_Generated'
    12. INSERT Process_Events_Log
    """
```

---

### FILE 3: `agents/rfq_06_compliance_attach.py`

**Process ID:** S2C.RFQ.06
**LangGraph node name:** `compliance_attach`

```python
def compliance_attach(state: S2CState) -> S2CState:
    """
    For each RFQ with RFQ_Status = 'Draft':

    1. Count vendors in Vendor_Shortlist for this RFQ
    2. CTRL-001 pre-check:
       - If count >= 3: log Pass to Compliance_Log, proceed
       - If count < 3:
         a. INSERT SVJ_Log with Approval_Status='Pending'
         b. Email Procurement Head for SVJ approval
         c. UPDATE RFQ_Log.RFQ_Status = 'SVJ_Pending'
         d. Set state["should_stop"] = True for this cluster (wait for SVJ)
         e. Return — do not proceed to approval
    3. Read Material_References for this material (cross-refs, OEM part numbers)
    4. Append references to RFQ document in DMS (read file, append, save)
    5. UPDATE RFQ_Log.RFQ_Status = 'Ready_For_Approval'
    6. INSERT Compliance_Log for CTRL-001
    7. INSERT Process_Events_Log
    """
```

---

### FILE 4: `agents/rfq_07_rfq_approval.py`

**Process ID:** S2C.RFQ.07
**LangGraph node name:** `rfq_approval`

```python
def rfq_approval(state: S2CState) -> S2CState:
    """
    For each RFQ with RFQ_Status = 'Ready_For_Approval':

    1. Get Total_Value from Consolidated_PRs
    2. Query DOP table: find tier where Value_Range_Min <= Total_Value <= Value_Range_Max
    3. For each required tier (could be multiple tiers if value spans):
       a. Look up Designations_Master for Approver_Designation → get email
       b. INSERT Approval_Log with Decision='Pending'
       c. Send approval request email:
          Subject: f"[ACTION REQUIRED] RFQ {rfq_id} Approval — {material_desc}"
          Body: cluster summary, total value, vendor shortlist, evaluation criteria
    4. CTRL-005: Verify the correct DOP tiers are being invoked.
       Log to Compliance_Log.
    5. UPDATE RFQ_Log.RFQ_Status = 'Approval_Pending'

    NOTE: Approval responses come via a webhook (separate handler).
    This agent sends the requests. The webhook handler (rfq_07_webhook.py)
    updates Approval_Log.Decision and triggers rfq_08 when all approved.

    For testing/simulation: include a simulate_approval() function that
    sets all pending approvals to 'Approved' for a given RFQ_ID.
    """
```

---

### FILE 5: `agents/rfq_08_rfq_dispatch.py`

**Process ID:** S2C.RFQ.08
**LangGraph node name:** `rfq_dispatch`

```python
def rfq_dispatch(state: S2CState) -> S2CState:
    """
    For each RFQ with RFQ_Status='Approved' (all Approval_Log entries Approved):

    1. Read Vendor_Shortlist for this RFQ
    2. CTRL-001 final enforcement:
       - Count shortlisted vendors
       - If < 3: check SVJ_Log for this RFQ with Approval_Status='Approved'
         - If SVJ approved: proceed with warning log
         - If no approved SVJ: BLOCK dispatch, log CTRL-001 Fail, stop
    3. For each vendor in shortlist:
       a. Get vendor email from Vendor_Master (construct as vendor_code@vendor.com
          for simulation, or use a contacts table if available)
       b. Read RFQ document from DMS
       c. INSERT RFQ_Dispatch_Log with Dispatched_At=now(), Delivery_Status='Sent'
       d. Send RFQ email to vendor via smtplib
    4. UPDATE RFQ_Log.RFQ_Status = 'Dispatched'
    5. UPDATE Consolidated_PRs: PR_Status='RFQ_Dispatched', RFQ_Dispatched_At=now()
    6. INSERT Compliance_Log for CTRL-001 (Pass)
    7. INSERT Process_Events_Log
    """
```

---

### FILE 6: `agents/rfq_09_offer_collection.py`

**Process ID:** S2C.RFQ.09
**LangGraph node name:** `offer_collection`

```python
def offer_collection(state: S2CState) -> S2CState:
    """
    Scheduled agent (runs daily). Manages submission collection lifecycle.

    1. Query RFQ_Log WHERE RFQ_Status = 'Dispatched'
    2. For each dispatched RFQ:
       a. Count submissions in RFQ_Submissions vs dispatched vendors in RFQ_Dispatch_Log
       b. Calculate days until Submission_Deadline
       c. For vendors who haven't submitted:
          - If deadline > 2 days: send reminder email
          - If deadline passed but < 48hr extension: send extension email
          - If > 48hr extension passed: mark as non-responsive
            (UPDATE Vendor_Shortlist: add note "Non-responsive")
       d. If all vendors responded OR deadline+48hr passed:
          UPDATE RFQ_Log.RFQ_Status = 'Submissions_Closed'
          UPDATE Consolidated_PRs.PR_Status = 'RFQ_Evaluation'

    INCOMING SUBMISSION HANDLER (separate function):
    def record_submission(rfq_id, vendor_code, quoted_price, lead_time_days,
                          file_content=None):
        # Called by email parser or webhook
        # INSERT RFQ_Submissions
        # INSERT DMS_Documents if file_content provided
        # INSERT Process_Events_Log

    For simulation: include a simulate_submissions() function that inserts
    realistic quote data for testing downstream eval agents.
    """
```

---

### FILE 7: `agents/eval_08_tech_evaluation.py`

**Process ID:** S2C.RFQ.10
**LangGraph node name:** `tech_evaluation`

```python
def tech_evaluation(state: S2CState) -> S2CState:
    """
    For each RFQ with RFQ_Status = 'Submissions_Closed':

    1. Read all RFQ_Submissions for this RFQ
    2. Read Long_Text_Specifications from Consolidated_PRs (the benchmark)
    3. Read Material_Master for additional technical context
    4. For each submission, call Gemini:

    Gemini prompt:
    "You are a technical evaluator for procurement at a steel plant.
     Required specifications: {specs}
     Vendor {vendor_code} submitted this quote for {material}:
     Price: {price}/unit, Lead Time: {lead_time} days
     [submission content if available]

     Score the technical compliance on a scale of 0-100:
     - Spec compliance (40 pts): Does it meet dimensions, grade, standards?
     - Material quality (30 pts): Brand, certifications, test reports
     - Documentation (20 pts): Completeness of submission
     - Alternatives offered (10 pts): Acceptable cross-references provided

     Return JSON: {tech_score: N, breakdown: {...}, tech_remarks: '...',
     disqualify: false, disqualify_reason: null}"

    5. INSERT RFQ_Tech_Evaluations for each submission
    6. If any submission disqualified: remove from further evaluation,
       INSERT Compliance_Log note
    7. CTRL-011: Verify all submissions were evaluated → INSERT Compliance_Log
    8. INSERT Process_Events_Log
    """
```

---

### FILE 8: `agents/eval_09_comm_evaluation.py`

**Process ID:** S2C.RFQ.11
**LangGraph node name:** `comm_evaluation`

```python
def comm_evaluation(state: S2CState) -> S2CState:
    """
    For each RFQ after tech evaluation:

    1. Read all RFQ_Submissions with their Quoted_Unit_Price and Lead_Time_Days
    2. Read Material_Master.Last_Purchase_Price (LPP benchmark)
    3. Read Material_Master.Standard_Lead_Time_Days
    4. Read Procurement_Historical_Pricing for price trend context

    PRICE SCORE (0-100):
    - Find lowest quoted price (best_price)
    - Each vendor: Price_Score = (best_price / vendor_price) * 100
    - Cap at 100 for the lowest bidder

    PAYMENT SCORE (0-100):
    - Net 60+ days from GRN: 95
    - Net 45 days from GRN: 85
    - Net 30 days from GRN: 75
    - Net 15 days: 60
    - Advance payment required: 40
    (Payment terms come from RFQ commercial terms or vendor's submitted terms)

    DELIVERY SCORE (0-100):
    - Lead_Time_Days <= Standard_Lead_Time_Days: 100
    - Lead_Time_Days <= Standard * 1.25: 85
    - Lead_Time_Days <= Standard * 1.5: 70
    - Lead_Time_Days > Standard * 1.5: 50

    5. INSERT RFQ_Comm_Evaluations for each submission
    6. INSERT Process_Events_Log
    """
```

---

### FILE 9: `agents/eval_10_overall_ranking.py`

**Process ID:** S2C.RFQ.12
**LangGraph node name:** `overall_ranking`

```python
def overall_ranking(state: S2CState) -> S2CState:
    """
    For each RFQ after comm evaluation:

    1. Read RFQ_Log.Evaluation_Criteria to parse weights
       e.g., "Tech: 40%, Comm: 60%, Min score: 70"
       → tech_weight=0.4, comm_weight=0.6, min_score=70

    2. For each submission, read RFQ_Tech_Evaluations and RFQ_Comm_Evaluations:
       comm_avg = (Price_Score + Payment_Score + Delivery_Score) / 3
       Tech_Weighted = Tech_Score * tech_weight
       Comm_Weighted = comm_avg * comm_weight
       Overall_Score = Tech_Weighted + Comm_Weighted

    3. INSERT RFQ_Overall_Evaluations for each submission

    4. Rank all submissions by Overall_Score DESC
    5. Flag any submission below min_score threshold
    6. Log top-ranked vendor to Process_Events_Log:
       "Evaluation complete: {vendor} ranked 1st with score {score}"

    7. CTRL-011 final: all submissions must have Overall_Evaluation.
       INSERT Compliance_Log.

    8. UPDATE RFQ_Log.RFQ_Status = 'Evaluation_Complete'
       UPDATE Consolidated_PRs.PR_Status = 'RFQ_Evaluation' (already set, confirm)
    """
```

---

### FILE 10: `graphs/phase2_graph.py`

```python
# Wire all Phase 2 nodes into a LangGraph StateGraph
# Entry: vendor_shortlisting (called after buyer_assignment)
# Exit: overall_ranking
# Include conditional routing:
#   - After compliance_attach: if SVJ needed → END (wait), else → rfq_approval
#   - After rfq_approval: transition to rfq_dispatch (webhook handles approval)
#   - After offer_collection: if submissions_closed → tech_evaluation, else END (wait)
#   - After overall_ranking → END (Phase 3 picks up)
```

---

## EXISTING DATA TO TEST AGAINST

**RFQ-2025-00290 (Spherical Rollers — CL-2025-00848-01):**
- Status: 'Under_Evaluation' (has 3 submissions with tech+comm evaluations but no overall)
- Submissions: SUB-005 (SKF 2780), SUB-006 (NTN 2920), SUB-007 (Timken 3050)
- Tech scores: 90, 86, 82. Comm evaluations exist.
- eval_10 should pick this up and complete the overall ranking.

**RFQ-2025-00291 (Contactors — CL-2025-00850-01):**
- Status: 'Dispatched'. 0 submissions received.
- offer_collection should send reminders to V-20048, V-20049, V-20053.

**RFQ-2025-00289 (Bearings — already complete):**
- All evaluations done. SKF ranked 1st (92.60 overall). Do NOT re-process.

---

## OUTPUT INSTRUCTIONS

Generate complete, executable Python files. Each agent function must:
- Have complete SQL (no stubs)
- Handle exceptions → append to `state["errors"]`
- Use `with get_db() as conn:` pattern for all DB access
- Use `genai.GenerativeModel("gemini-2.5-pro")` for AI calls
- Use Python `logging.getLogger(__name__)` for all logging
- Return the updated `state` dict

Generate files in this order:
1. `agents/rfq_04_vendor_shortlisting.py`
2. `agents/rfq_05_rfq_creation.py`
3. `agents/rfq_06_compliance_attach.py`
4. `agents/rfq_07_rfq_approval.py`
5. `agents/rfq_08_rfq_dispatch.py`
6. `agents/rfq_09_offer_collection.py`
7. `agents/eval_08_tech_evaluation.py`
8. `agents/eval_09_comm_evaluation.py`
9. `agents/eval_10_overall_ranking.py`
10. `graphs/phase2_graph.py`
