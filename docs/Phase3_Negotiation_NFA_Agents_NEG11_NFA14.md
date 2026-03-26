# PHASE 3 — NEGOTIATION & NFA AGENTS (NEG.11 → NFA.14)
## Paste into OpenCode-Vertex-Gemini 2.5 Pro

---

## CONTEXT

Continuing to build **Sourcesense** in Python + LangGraph. Phases 1 and 2 files exist. Import from them.

**Generate executable Python files only. No n8n JSON.**

---

## DATABASE SCHEMA (new tables in Phase 3)

### Negotiation_Intelligence_Log (WRITE)
```
Brief_ID (PK), RFQ_ID, Spend_Analysis (TEXT), Market_Research_Summary (TEXT)
```

### Negotiation_Shortlist_Approval (WRITE)
```
Neg_Approval_ID (PK), RFQ_ID, Vendor_Code, Negotiated_Price,
Approval_Status, Approved_By, Approved_At
```

### NFA_Log (WRITE)
```
NFA_ID (PK), Consolidation_Cluster_ID, RFQ_ID, Recommended_Vendor,
Negotiated_Unit_Price, Total_NFA_Value, Price_Vs_LPP_Status (Below_LPP/Above_LPP/First_Purchase),
Price_Deviation_Pct, Savings_Vs_LPP_Pct, Price_Justification,
NFA_Status (Draft/Approved/Rejected), NFA_Document_File_ID,
Created_By, Created_At, Updated_At
```

### NFA_Approval_Log (WRITE)
```
NFA_Approval_ID (PK), NFA_ID, Tier_Level, Approver_Designation,
Approver_Email, Decision, Comments, Decided_At
```

---

## PHASE 3: GENERATE THESE FILES

### FILE 1: `agents/neg_11_negotiation_copilot.py`

**Process ID:** S2C.NEG.13
**LangGraph node name:** `negotiation_copilot`

This is the **core AI agent of the platform**. Give it a full Gemini call.

```python
def negotiation_copilot(state: S2CState) -> S2CState:
    """
    Triggered when overall_ranking is complete (RFQ_Status = 'Evaluation_Complete').

    STEP 1 — Gather intelligence:
    1. Read top-ranked vendor from RFQ_Overall_Evaluations (highest Overall_Score)
    2. Read cluster details: material, quantity, total value
    3. Read Procurement_Historical_Pricing for this material (all history):
       - Calculate price trend: is price going up or down over last 12 months?
       - Calculate average price, min price, max price
    4. Read Vendor_History for top vendor + this material:
       - Total_POs_12M, Last_PO_Price, Avg_Delivery_Days, Quality_Rating
    5. Read Monthly_Performance (last 6 months): quality incidents, OTP
    6. Read Material_Master.Last_Purchase_Price (LPP)
    7. Read all competitor quotes from RFQ_Submissions (for BATNA):
       - 2nd best price = BATNA (Best Alternative To Negotiated Agreement)

    STEP 2 — Call Gemini for negotiation strategy:

    Prompt (use this exact structure):
    '''
    You are a senior procurement negotiator for JSW Steel, a large Indian steel manufacturer.
    Analyze this procurement situation and generate a negotiation strategy.

    MATERIAL: {material_description}
    QUANTITY: {quantity} {uom}
    MATERIAL GROUP: {material_group}

    PRICE INTELLIGENCE:
    - Last Purchase Price (LPP): INR {lpp}/unit
    - Best quote received: INR {best_quote}/unit (from {best_vendor})
    - Second best quote (BATNA): INR {batna_price}/unit (from {batna_vendor})
    - 12-month price trend: {price_trend} (avg INR {avg_price}, min INR {min_price})

    VENDOR INTELLIGENCE (Recommended Vendor: {vendor_name}):
    - Historical POs last 12 months: {total_pos}
    - Last purchase price with this vendor: INR {last_po_price}
    - Quality rating: {quality_rating}/5
    - Avg delivery performance: {delivery_pct}% on-time
    - Quality incidents (last 6 months): {quality_incidents}

    MARKET CONTEXT:
    - Annual spend on {material_group} category: approximately INR {annual_spend}
    - This vendor's share of that spend: approximately {vendor_share}%

    Generate:
    1. Spend Analysis (2-3 sentences for the NFA brief)
    2. Market Research Summary (2-3 sentences: price trends, alternatives)
    3. Negotiation Strategy: AGGRESSIVE / MODERATE / COLLABORATIVE (with reason)
    4. Target Price: the price you would aim to negotiate to (INR/unit)
    5. Walk-away Price: the maximum acceptable price (INR/unit, never > LPP)
    6. Key Negotiation Points: top 3 leverage points to use
    7. Suggested Email to Vendor: draft the negotiation opener email

    Return as JSON with keys: spend_analysis, market_summary, strategy,
    target_price, walkaway_price, leverage_points, vendor_email_draft
    '''

    STEP 3 — Store and act:
    8. INSERT Negotiation_Intelligence_Log (Brief_ID, RFQ_ID, Spend_Analysis, Market_Research_Summary)
    9. INSERT Negotiation_Shortlist_Approval (Approval_Status='Pending')
    10. Send negotiation email to vendor (use Gemini's vendor_email_draft)
    11. Store target_price and walkaway_price in state for NEG.12 to use
    12. INSERT Process_Events_Log
    13. UPDATE RFQ_Log.RFQ_Status = 'Under_Negotiation'

    SPECIAL — Low Value Auto-Negotiation:
    If Total_Value < 100,000 INR:
      - Skip email, auto-negotiate:
        - If best_quote <= LPP: auto-accept at best_quote
        - If best_quote <= LPP * 1.05: auto-accept with justification
        - If best_quote > LPP * 1.05: flag for manual review (set state flag)
      - UPDATE Negotiation_Shortlist_Approval.Approval_Status = 'Auto_Approved'
      - SET state["negotiated_price"] = auto_accepted_price
      - Go directly to NFA.13
    """
```

---

### FILE 2: `agents/neg_12_negotiation_approval.py`

**Process ID:** S2C.NEG.17 + internal
**LangGraph node name:** `negotiation_approval`

```python
def negotiation_approval(state: S2CState) -> S2CState:
    """
    Handles the vendor's BAFO (Best and Final Offer) response.

    Called via webhook when vendor replies, or via simulate function.

    INPUTS (from state or webhook payload):
    - rfq_id: which RFQ this is for
    - vendor_code: the negotiating vendor
    - bafo_price: vendor's final offered price (float, INR/unit)

    STEPS:
    1. Read RFQ_Submissions for the vendor to get their original quoted price
    2. Read Material_Master.Last_Purchase_Price
    3. Read Consolidated_PRs for quantity
    4. Calculate:
       total_negotiated_value = bafo_price * quantity
       savings_vs_lpp = (lpp - bafo_price) / lpp * 100 (positive = below LPP)
       savings_vs_quote = (original_quote - bafo_price) / original_quote * 100
    5. UPDATE Negotiation_Shortlist_Approval.Negotiated_Price = bafo_price

    ROUTING — DOP-based internal approval:
    6. Query DOP for tier matching total_negotiated_value
    7. For each tier:
       a. Get approver email from Designations_Master
       b. INSERT Approval_Log with Decision='Pending'
       c. Send approval request email with negotiation summary:
          "Vendor offered INR {bafo_price}/unit (was {original_quote}).
           Savings vs LPP: {savings_vs_lpp:.2f}%. Total: INR {total:,.0f}
           Please approve or reject."
    8. Mark state as waiting for approval
       (Webhook handler updates Approval_Log.Decision)

    APPROVED path (simulate_negotiation_approval() for testing):
    9. UPDATE Negotiation_Shortlist_Approval.Approval_Status = 'Approved'
    10. SET state["negotiated_price"] = bafo_price
    11. UPDATE Consolidated_PRs.PR_Status = 'Negotiation_Approved'
    12. Trigger NEG.13 (NFA generation)

    REJECTED path:
    13. UPDATE Negotiation_Shortlist_Approval.Approval_Status = 'Rejected'
    14. Check if there's a second-ranked vendor (from RFQ_Overall_Evaluations rank 2)
        If yes: restart negotiation with second vendor
        If no: escalate to buyer with notification
    15. INSERT Process_Events_Log
    """
```

---

### FILE 3: `agents/nfa_13_nfa_generation.py`

**Process ID:** S2C.NEG.13 (NFA creation)
**LangGraph node name:** `nfa_generation`

```python
def nfa_generation(state: S2CState) -> S2CState:
    """
    Generates the NFA document after negotiation is approved.

    1. Read negotiated_price from state (set by NEG.12)
    2. Read Consolidated_PRs: cluster, material, quantity, plant, delivery date
    3. Read RFQ_Log and RFQ_Overall_Evaluations (full evaluation summary)
    4. Read Negotiation_Intelligence_Log.Brief_ID for this RFQ
    5. Read Vendor_Master for recommended vendor details
    6. Read Material_Master.Last_Purchase_Price (LPP)

    CTRL-003 — NFA Price vs LPP:
    7. Compare negotiated_price vs LPP:
       - negotiated < LPP:
           Price_Vs_LPP_Status = 'Below_LPP'
           Savings_Vs_LPP_Pct = (lpp - negotiated) / lpp * 100
           Price_Deviation_Pct = None
           Price_Justification = None (not required)
       - negotiated > LPP:
           Price_Vs_LPP_Status = 'Above_LPP'
           Price_Deviation_Pct = (negotiated - lpp) / lpp * 100
           Price_Justification = REQUIRED (prompt buyer if not in state)
           → Also flag for CFO approval in NFA.14
       - LPP is NULL (first purchase):
           Price_Vs_LPP_Status = 'First_Purchase'
           → exempt from deviation check
    8. INSERT Compliance_Log for CTRL-003

    9. Call Gemini to generate NFA document text:

    Prompt:
    '''
    Generate a formal Note for Approval (NFA) document for procurement at JSW Steel.

    PROCUREMENT DETAILS:
    Material: {material_description} ({material_code})
    HSN Code: {hsn_code}
    Quantity: {quantity} {uom}
    Plant: {plant}
    Required By: {delivery_date}

    SOURCING SUMMARY:
    RFQ: {rfq_id} | Vendors Invited: {vendors_invited} | Submissions Received: {submissions}
    Technical Evaluation: {tech_eval_summary}
    Commercial Evaluation: {comm_eval_summary}

    RECOMMENDED VENDOR: {vendor_name} (Code: {vendor_code})
    GSTIN: {gstin} | MSME: {msme_status}

    PRICING:
    Negotiated Price: INR {negotiated_price}/unit
    Total Value: INR {total_value:,.2f}
    Last Purchase Price: INR {lpp}/unit
    Price Status: {price_vs_lpp_status}
    Savings: {savings_pct:.2f}% below LPP  [OR]  Deviation: {deviation_pct:.2f}% above LPP

    COMMERCIAL TERMS:
    Payment: {payment_terms}
    Incoterms: DDP
    Delivery: {delivery_date}
    LD Clause: 0.5% per week delay, max 5%
    Warranty: 12 months from date of commissioning

    COMPLIANCE:
    - CTRL-001: {ctrl_001_status} (vendor count)
    - CTRL-003: {ctrl_003_status} (price vs LPP)
    - CTRL-007: {ctrl_007_status} (blacklist check)
    - CTRL-008: {ctrl_008_status} (KYC check)

    Generate a formal, professional NFA document in plain text suitable for
    management approval. Include: Background, Sourcing Process, Evaluation Summary,
    Recommendation, Commercial Terms, Compliance Sign-off, Approval Required.
    '''

    10. Generate NFA_ID = f"NFA-{year}-{seq:05d}"
    11. Save NFA document to DMS: f"{DMS_ROOT}/NFA/NFA_{nfa_id}.txt"
    12. INSERT DMS_Documents record
    13. INSERT NFA_Log with NFA_Status = 'Draft'
    14. CTRL-015: Verify all required NFA_Log fields are populated → INSERT Compliance_Log
    15. UPDATE Consolidated_PRs.NFA_Status = 'Draft'
    16. INSERT Process_Events_Log
    """
```

---

### FILE 4: `agents/nfa_14_nfa_approval.py`

**Process ID:** S2C.NFA.15
**LangGraph node name:** `nfa_approval`

```python
def nfa_approval(state: S2CState) -> S2CState:
    """
    Routes NFA through multi-tier approval chain.

    1. Read NFA_Log WHERE NFA_Status = 'Draft'
    2. Read Consolidated_PRs for Total_NFA_Value
    3. Build approval chain:
       a. Query DOP for all tiers required based on Total_NFA_Value
          (e.g., value=106,800 → only Tier 1 required)
       b. If Price_Vs_LPP_Status = 'Above_LPP':
          → Add CFO tier (DES-CFO) regardless of value
       c. Order tiers from lowest to highest (sequential)
    4. For Tier 1:
       a. INSERT NFA_Approval_Log (Tier_Level=1, Decision='Pending')
       b. INSERT Approval_Log
       c. Send approval email with:
          - NFA document attached (read from DMS)
          - Summary: vendor, price, savings/deviation, total value
          - Approve/Reject buttons (webhook URLs)
    5. Set state["nfa_approved"] = False (waiting)

    WEBHOOK HANDLER — nfa_approval_response(nfa_id, tier, decision, comments, approver_email):
    6. UPDATE NFA_Approval_Log: Decision, Comments, Decided_At
    7. If Decision = 'Rejected':
       UPDATE NFA_Log.NFA_Status = 'Rejected'
       UPDATE Consolidated_PRs.NFA_Status = 'Rejected'
       Send rejection email to buyer
       INSERT Process_Events_Log
       STOP
    8. If Decision = 'Approved' and more tiers pending:
       → Send approval email to next tier (same as step 4 above)
    9. If Decision = 'Approved' and this was the LAST tier:
       UPDATE NFA_Log.NFA_Status = 'Approved'
       UPDATE Consolidated_PRs.NFA_Status = 'Approved'
       UPDATE Consolidated_PRs.NFA_Approved_At = now()
       SET state["nfa_approved"] = True
       UPDATE Material_Master.Last_Purchase_Price (to negotiated price — PREVIEW)
       INSERT Process_Events_Log with Event_Type = 'NFA_Approved'
       → Trigger Phase 4 (PO creation)

    ESCALATION:
    10. If a tier hasn't responded in 48 hours: send reminder
    11. If no response in 72 hours: notify next tier and buyer

    SIMULATION:
    Include simulate_nfa_approval(nfa_id) function for testing:
    - Auto-approves all pending tiers sequentially
    """
```

---

### FILE 5: `graphs/phase3_graph.py`

```python
# Wire Phase 3 nodes:
# Entry: negotiation_copilot (after Phase 2 overall_ranking)
# Nodes: negotiation_copilot → negotiation_approval → nfa_generation → nfa_approval
# Routing:
#   - After negotiation_copilot: if low-value auto-approved → nfa_generation
#                                else → END (wait for vendor BAFO via webhook)
#   - After negotiation_approval: if approved → nfa_generation
#                                 else → END (escalate or retry)
#   - After nfa_generation → nfa_approval
#   - After nfa_approval: if nfa_approved → END (Phase 4 picks up)
#                         else → END (wait for webhook)
```

---

## EXISTING SAMPLE DATA

**CL-2025-00847-01 (Bearings — fully complete):**
- NFA-2025-00312: Approved. SKF @ INR 445/unit. Savings 3.68% vs LPP 462.
- 2-tier approval: Vikram Singh (T1, Approved 2025-12-01), Anjali Mehta (T2, Approved 2025-12-02)
- Total value: INR 106,800 — within Tier 1 DOP. No CFO required (below LPP).
- Do NOT re-process this cluster.

**CL-2025-00848-01 (Spherical Rollers — evaluation complete after eval_10 runs):**
- 3 submissions evaluated. SKF expected to rank 1st (~89 overall score).
- No negotiation started yet — NEG.11 should pick this up after eval_10.

**BRIEF-2025-00289 (Intelligence log for bearings):**
- "Annual spend on MRO-BRG: INR 42.5L. SKF 58% share."
- Already exists — don't duplicate.

---

## OUTPUT INSTRUCTIONS

Generate complete, executable Python files. All Gemini prompts must be the full prompt text (not placeholders). All SQL must be complete. Include:
- `simulate_negotiation_approval(rfq_id, vendor_code, bafo_price)` in neg_12
- `simulate_nfa_approval(nfa_id)` in nfa_14

Generate in this order:
1. `agents/neg_11_negotiation_copilot.py`
2. `agents/neg_12_negotiation_approval.py`
3. `agents/nfa_13_nfa_generation.py`
4. `agents/nfa_14_nfa_approval.py`
5. `graphs/phase3_graph.py`
