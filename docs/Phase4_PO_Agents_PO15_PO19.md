# PHASE 4 — PO CREATION AGENTS (PO.15 → PO.19)
## Paste into OpenCode-Vertex-Gemini 2.5 Pro

---

## CONTEXT

Final phase of **Sourcesense** in Python + LangGraph. All Phase 1-3 files exist. Import from them.

**Generate executable Python files only. No n8n JSON.**

---

## DATABASE SCHEMA (new tables in Phase 4)

### PO_Reference (WRITE — STM, S2C-owned)
```
PO_Ref_ID (PK), NFA_ID, Consolidation_Cluster_ID, SAP_PO_Number,
PO_Document_File_ID, Vendor_Acknowledged_At, API_Call_Status (Pending/Success/Failed),
Created_By, Created_At
```

### SAP_PO_Data (WRITE — ERP-mimic, BAPI simulation)
```
SAP_PO_Number (PK), Vendor_Code, Material_Code, Plant,
Unit_Price, Quantity, UOM, PO_Net_Value, Delivery_Date,
Payment_Terms, Incoterms, PO_Type (default: 'NB'),
PO_Status (Open/Partially Delivered/Closed),
GRN_Number, Invoice_Number, Payment_Status (Not_Initiated/Approved/Paid),
SAP_Created_At, Goods_Receipt_Date, Invoice_Date, Payment_Date, Remarks
```

**Architecture note:** SAP_PO_Data is the ERP system of record.
S2C writes to it ONCE via BAPI simulation (PO.16). After that, S2C only reads it.
All PO status updates (GRN, Invoice, Payment) come from the ERP side.

---

## PAYMENT TERMS MAPPING (for BAPI simulation)

| Human Readable | SAP Code |
|---|---|
| Net 30 days from GRN | Z030 |
| Net 45 days from GRN | Z045 |
| Net 60 days from GRN | Z060 |
| 100% Advance | Z000 |
| 50% Advance + 50% on Delivery | Z050 |

Map using a dict — add unknown terms to a Remarks field rather than failing.

---

## PHASE 4: GENERATE THESE FILES

### FILE 1: `agents/po_15_po_reference_creation.py`

**Process ID:** S2C.PO.19 (step 1)
**LangGraph node name:** `po_reference_creation`

```python
def po_reference_creation(state: S2CState) -> S2CState:
    """
    Creates the STM-side PO tracking record after NFA is fully approved.

    1. Query NFA_Log WHERE NFA_Status = 'Approved' AND NFA_ID NOT IN
       (SELECT NFA_ID FROM PO_Reference) -- avoid duplicates
    2. For each approved NFA without a PO_Reference:
       a. Read NFA_Approval_Log: verify ALL required tiers have Decision='Approved'
          (count approved tiers vs tiers created for this NFA)
       b. If not all tiers approved: skip (webhook hasn't fired yet), log warning
       c. If fully approved:
          - Generate PO_Ref_ID = f"POREF-{year}-{seq:05d}"
          - INSERT PO_Reference:
              NFA_ID = nfa.NFA_ID
              Consolidation_Cluster_ID = nfa.Consolidation_Cluster_ID
              SAP_PO_Number = NULL (not yet created)
              PO_Document_File_ID = NULL
              Vendor_Acknowledged_At = NULL
              API_Call_Status = 'Pending'
              Created_By = consolidated_pr.Assigned_Buyer
              Created_At = now()
    3. UPDATE state["po_ref_id"] with the new PO_Ref_ID
    4. INSERT Process_Events_Log with Event_Type = 'PO_Reference_Created'
    """
```

---

### FILE 2: `agents/po_16_sap_bapi_call.py`

**Process ID:** S2C.PO.19 (step 2 — core BAPI simulation)
**LangGraph node name:** `sap_bapi_call`

```python
def sap_bapi_call(state: S2CState) -> S2CState:
    """
    Simulates BAPI_PO_CREATE1 — creates the PO record in the SAP mimic table.

    This is the most critical agent. It writes to SAP_PO_Data (ERP system of record).

    1. Read PO_Reference WHERE API_Call_Status = 'Pending'
    2. For each pending PO_Reference:
       a. Read NFA_Log: get Recommended_Vendor, Negotiated_Unit_Price
       b. Read Consolidated_PRs: Material_Code, Quantity, UOM, Plant,
          Delivery_Date, Payment_Terms, Total_Value
       c. Read Vendor_Master: Vendor_Code, Vendor_Name, GSTIN
       d. Read Material_Master: Material_Code, HSN_SAC_Code

    BUILD PO HEADER + LINE ITEM:
    3. Generate SAP_PO_Number:
       - Query SAP_PO_Data for MAX(SAP_PO_Number)
       - If none exists: start at '4500087234'
       - Else: increment by 1 (as string: 4500087235, 4500087236, ...)
    4. Map Payment_Terms to SAP code (use dict, fallback to 'Z030')
    5. Calculate PO_Net_Value = Negotiated_Unit_Price × Quantity

    BAPI CALL SIMULATION (with retry logic):
    6. Try (max 3 attempts):
       INSERT SAP_PO_Data (
           SAP_PO_Number, Vendor_Code, Material_Code, Plant,
           Unit_Price (= Negotiated_Unit_Price),
           Quantity, UOM, PO_Net_Value, Delivery_Date,
           Payment_Terms (SAP code), Incoterms='DDP',
           PO_Type='NB', PO_Status='Open',
           GRN_Number=NULL, Invoice_Number=NULL,
           Payment_Status='Not_Initiated',
           SAP_Created_At=now()
       )
    7. On success:
       UPDATE PO_Reference:
         SAP_PO_Number = generated number
         API_Call_Status = 'Success'
       SET state["sap_po_number"] = generated_po_number
       SET state["po_created"] = True
       INSERT Process_Events_Log with Event_Type='PO_Created',
         Event_Description=f"SAP PO {sap_po_number} created for NFA {nfa_id}"
    8. On failure after 3 retries:
       UPDATE PO_Reference.API_Call_Status = 'Failed_Permanent'
       Append error to state["errors"]
       Send alert email to buyer and system admin
       SET state["should_stop"] = True
    """
```

---

### FILE 3: `agents/po_17_po_document_attach.py`

**Process ID:** S2C.PO.19 (step 3)
**LangGraph node name:** `po_document_attach`

```python
def po_document_attach(state: S2CState) -> S2CState:
    """
    Generates and saves the PO document after BAPI success.

    1. Read PO_Reference WHERE API_Call_Status='Success' AND PO_Document_File_ID IS NULL
    2. For each, read SAP_PO_Data, Vendor_Master, Material_Master, Consolidated_PRs

    GENERATE PO DOCUMENT (via Gemini):
    3. Call Gemini to generate formatted PO document:

    Prompt:
    '''
    Generate a formal Purchase Order document for JSW Steel Limited.

    PURCHASE ORDER: {sap_po_number}
    Date: {today_date}
    Type: Standard PO (NB)

    BUYER:
    JSW Steel Limited
    Plant: {plant_name} ({plant_code})
    GST: 27AABCJ5712M1ZT

    VENDOR:
    {vendor_name}
    GSTIN: {vendor_gstin}
    MSME Registration: {msme_number or 'Not Applicable'}

    LINE ITEM 1:
    Material Code: {material_code}
    Description: {material_description}
    HSN Code: {hsn_code}
    Quantity: {quantity} {uom}
    Unit Price: INR {unit_price:,.2f}
    Total Value: INR {po_net_value:,.2f}

    DELIVERY:
    Required Delivery Date: {delivery_date}
    Delivery Location: JSW Steel Plant {plant_code}, [Address]
    Incoterms: DDP (Delivered Duty Paid)

    COMMERCIAL TERMS:
    Payment Terms: {payment_terms}
    LD Clause: 0.5% of PO value per week of delay, maximum 5%
    Warranty: 12 months from date of commissioning/installation
    Quality: Material must conform to IS/DIN/ISO standards as specified

    APPROVAL REFERENCE:
    NFA: {nfa_id} | Approved: {nfa_approved_at}
    RFQ: {rfq_id}

    Generate a professional, complete Purchase Order document in plain text.
    Include all the above details in a well-formatted document.
    '''

    4. Save PO document:
       file_path = f"{DMS_ROOT}/PO/PO_{sap_po_number}.txt"
       Write Gemini output to file
    5. INSERT DMS_Documents:
       Document_ID = f"DOC-PO-{sap_po_number}"
       Document_Type = 'PO_Document'
       Entity_Type = 'PO_Reference'
       Entity_ID = po_ref_id
       File_Name = f"PO_{sap_po_number}.txt"
       File_Path = file_path
    6. UPDATE PO_Reference.PO_Document_File_ID = 'DOC-PO-{sap_po_number}'
    7. INSERT Compliance_Log (CTRL audit stamp — all controls passed, PO issued)
    8. INSERT Process_Events_Log
    """
```

---

### FILE 4: `agents/po_18_vendor_dispatch.py`

**Process ID:** S2C.PO.19 (step 4)
**LangGraph node name:** `vendor_dispatch`

```python
def vendor_dispatch(state: S2CState) -> S2CState:
    """
    Emails PO to vendor and manages acknowledgment SLA.

    1. Read PO_Reference WHERE PO_Document_File_ID IS NOT NULL
       AND Vendor_Acknowledged_At IS NULL
    2. Read SAP_PO_Data, Vendor_Master, Consolidated_PRs (for buyer email)
    3. Read PO document from DMS file path

    SEND EMAIL:
    4. Send PO email via smtplib:
       To: {vendor_email}  (use Vendor_Code@vendor.com for simulation)
       CC: {buyer_email}, {manager_email}
       Subject: f"Purchase Order {sap_po_number} — {material_description}"
       Body:
         "Dear {vendor_name},
          Please find attached Purchase Order {sap_po_number}.
          Delivery required by: {delivery_date}
          Total Value: INR {po_net_value:,.2f}
          Please acknowledge receipt within 48 hours.
          [PO document content pasted here for simulation]"

    SLA MONITORING (run daily as a scheduled check):
    5. def check_acknowledgment_sla():
       Read PO_Reference WHERE PO_Document_File_ID IS NOT NULL
         AND Vendor_Acknowledged_At IS NULL
         AND Created_At < now() - 48 hours:
       → Send reminder email to vendor
       If Created_At < now() - 72 hours:
       → Escalate email to buyer: "Vendor has not acknowledged PO. Please call."

    ACKNOWLEDGMENT HANDLER (webhook or email reply):
    6. def record_acknowledgment(po_ref_id):
       UPDATE PO_Reference.Vendor_Acknowledged_At = now()
       INSERT Process_Events_Log with Event_Type = 'Vendor_Acknowledged'

    SIMULATION:
    7. Include simulate_vendor_acknowledgment(po_ref_id) for testing.
    """
```

---

### FILE 5: `agents/po_19_status_update.py`

**Process ID:** S2C.PO.19 (step 5 — closes the procurement lifecycle)
**LangGraph node name:** `status_update`

```python
def status_update(state: S2CState) -> S2CState:
    """
    Closes the cluster lifecycle and updates master data with negotiated price.

    1. Read PO_Reference WHERE API_Call_Status = 'Success'
    2. Read Consolidated_PRs for the cluster
    3. Read SAP_PO_Data for PO details

    UPDATE CLUSTER STATUS:
    4. UPDATE Consolidated_PRs:
       PR_Status = 'PO_Created'
       PO_Created_At = SAP_PO_Data.SAP_Created_At

    CLOSE LIFECYCLE (if vendor acknowledged):
    5. If PO_Reference.Vendor_Acknowledged_At IS NOT NULL:
       UPDATE Consolidated_PRs:
         PR_Status = 'Closed'
         Closed_At = now()
       INSERT Process_Events_Log with Event_Type = 'Cluster_Closed',
         Event_Description = f"Procurement complete. PO {sap_po_number} acknowledged by vendor."

    UPDATE MASTER DATA (close the feedback loop):
    6. UPDATE Material_Master:
       Last_Purchase_Price = SAP_PO_Data.Unit_Price
       LPP_Currency = 'INR'
       LPP_Date = SAP_PO_Data.SAP_Created_At (date portion)
       LPP_Vendor_Code = SAP_PO_Data.Vendor_Code
       Updated_At = now()
       → This ensures future procurements of this material use the new LPP as benchmark.

    RELEASE BUYER:
    7. Get buyer email from Consolidated_PRs.Assigned_Buyer
    8. UPDATE Buyer_Master.Current_Workload -= 1
       WHERE Buyer_Email = assigned_buyer
       (cap at 0 — never go negative)

    NOTIFY:
    9. Send completion email to buyer and requisitioner:
       "Purchase Order {sap_po_number} has been issued to {vendor_name}.
        Total Value: INR {po_net_value:,.2f}
        Expected Delivery: {delivery_date}
        Savings vs LPP: {savings_pct:.2f}%"
    10. INSERT Process_Events_Log (final event for cluster)
    """
```

---

### FILE 6: `graphs/phase4_graph.py`

```python
# Wire Phase 4 nodes:
# po_reference_creation → sap_bapi_call → po_document_attach → vendor_dispatch → status_update → END
# Error routing: if should_stop at any node → END
# Include retry logic in sap_bapi_call (3 attempts before marking Failed_Permanent)
```

---

### FILE 7: `graphs/master_graph.py`

Wire ALL 4 phases into one master LangGraph that can run the full pipeline:

```python
# master_graph.py
from langgraph.graph import StateGraph, END
from state import S2CState

# Import all phase graphs
from graphs.phase1_graph import build_phase1_graph
from graphs.phase2_graph import build_phase2_graph
from graphs.phase3_graph import build_phase3_graph
from graphs.phase4_graph import build_phase4_graph

def build_master_graph():
    """
    Master graph wiring all 19 agents.
    Phases run sequentially. Each phase graph is compiled and
    invoked as a subgraph node in the master.
    """
    graph = StateGraph(S2CState)

    # Add each phase as a compiled subgraph node
    graph.add_node("phase1_pr", build_phase1_graph())
    graph.add_node("phase2_rfq", build_phase2_graph())
    graph.add_node("phase3_neg", build_phase3_graph())
    graph.add_node("phase4_po", build_phase4_graph())

    graph.set_entry_point("phase1_pr")

    def route_phase1(state):
        if state.get("should_stop"): return END
        if state.get("buyer_assigned"): return "phase2_rfq"
        return END

    def route_phase2(state):
        if state.get("should_stop"): return END
        if state.get("evaluations_complete"): return "phase3_neg"
        return END

    def route_phase3(state):
        if state.get("should_stop"): return END
        if state.get("nfa_approved"): return "phase4_po"
        return END

    graph.add_conditional_edges("phase1_pr", route_phase1)
    graph.add_conditional_edges("phase2_rfq", route_phase2)
    graph.add_conditional_edges("phase3_neg", route_phase3)
    graph.add_edge("phase4_po", END)

    return graph.compile()

if __name__ == "__main__":
    app = build_master_graph()
    initial_state = S2CState(
        cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
        current_agent="phase1_pr", next_agent=None, pr_status=None,
        consolidated_clusters=[], specs_extracted=False, buyer_assigned=None,
        vendors_shortlisted=[], rfq_created=False, evaluations_complete=False,
        negotiated_price=None, nfa_approved=False, po_created=False,
        sap_po_number=None, errors=[], compliance_results={}, should_stop=False,
        db_path="s2c_sourcesense.db", dms_root="DMS_Documents"
    )
    result = app.invoke(initial_state)
    print("Full pipeline complete.")
    if result.get("errors"):
        print("Errors encountered:", result["errors"])
```

---

## EXISTING DATA TO TEST

**CL-2025-00847-01 (Bearings — ready for Phase 4 right now):**
- NFA-2025-00312: Approved
- PO_Reference table: currently EMPTY — PO.15 will create the first record
- SAP_PO_Data table: currently EMPTY — PO.16 will create the first SAP PO
- Expected SAP_PO_Number: `4500087234`
- Expected Total: 240 units × INR 445 = INR 106,800
- Payment Terms: "Net 45 days from GRN" → SAP code `Z045`

---

## FINAL DELIVERABLE — ALSO GENERATE:

### `requirements.txt`
```
langgraph>=0.2.0
langchain>=0.3.0
langchain-google-vertexai>=2.0.0
google-generativeai>=0.8.0
langsmith>=0.1.0
schedule>=1.2.0
python-dotenv>=1.0.0
```

### `.env.example`
```
GEMINI_API_KEY=your-key-here
GOOGLE_PROJECT_ID=your-project-id
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=sourcesense-s2c
DB_PATH=s2c_sourcesense.db
DMS_ROOT=DMS_Documents
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### `run.py` (entry point)
```python
#!/usr/bin/env python3
"""
Sourcesense S2C Platform — Main entry point.
Usage:
  python run.py --phase all          # Run full pipeline
  python run.py --phase 1            # Run only Phase 1 (PR)
  python run.py --phase 2            # Run only Phase 2 (RFQ+Eval)
  python run.py --phase 3            # Run only Phase 3 (Neg+NFA)
  python run.py --phase 4            # Run only Phase 4 (PO)
  python run.py --agent pr_01        # Run a specific agent
  python run.py --simulate po        # Simulate PO creation for CL-2025-00847-01
  python run.py --schedule           # Start scheduler (runs agents on their triggers)
"""
```

### `README.md`
```
# Sourcesense S2C Platform

## Setup
1. pip install -r requirements.txt
2. Copy .env.example to .env and fill in your keys
3. Ensure s2c_sourcesense.db is in the same directory as run.py
4. python run.py --phase all

## LangSmith Tracing
Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env.
Open https://smith.langchain.com to see full agent execution traces,
state transitions, Gemini calls, and timing.

## Agent Graph Visualization
python -c "from graphs.master_graph import build_master_graph; \
           app = build_master_graph(); \
           print(app.get_graph().draw_mermaid())"
Paste the Mermaid output into https://mermaid.live to see the full agent graph.
```

---

## OUTPUT INSTRUCTIONS

Generate all files listed above as complete, executable Python. Generate in this order:
1. `agents/po_15_po_reference_creation.py`
2. `agents/po_16_sap_bapi_call.py`
3. `agents/po_17_po_document_attach.py`
4. `agents/po_18_vendor_dispatch.py`
5. `agents/po_19_status_update.py`
6. `graphs/phase4_graph.py`
7. `graphs/master_graph.py`
8. `run.py`
9. `requirements.txt`
10. `.env.example`
11. `README.md`
