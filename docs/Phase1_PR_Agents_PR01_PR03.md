# PHASE 1 — PR AGENTS (PR.01 → PR.03)
## Paste into OpenCode-Vertex-Gemini 2.5 Pro

---

## WHAT YOU ARE BUILDING

You are building **Sourcesense** — a procurement intelligence platform for a large steel company (JSW Steel equivalent). It automates 19 Source-to-Contract workflows. The runtime is **Python + LangGraph** with SQLite as the database and Gemini 2.5 Pro as the AI engine.

**Do NOT generate n8n JSON. Generate executable Python files.**

---

## TECH STACK

| Component | Tool | Notes |
|-----------|------|-------|
| Agent Framework | **LangGraph** (`langgraph`) | Each agent = a LangGraph node |
| State Management | `TypedDict` state passed between nodes | Shared across all 19 agents |
| Database | **SQLite** (`sqlite3` built-in) | File: `s2c_sourcesense.db` |
| AI / LLM | **Gemini 2.5 Pro** via `google-generativeai` | Use `genai.GenerativeModel("gemini-2.5-pro")` |
| Email | `smtplib` (built-in) | SMTP config in `config.py` |
| Scheduling | Python `schedule` library | For agents with periodic triggers |
| Tracing | **LangSmith** (`langsmith`) | Set `LANGCHAIN_TRACING_V2=true` in env |
| DMS | Local filesystem | `/DMS_Documents/{RFQ,NFA,PO,Specs,SVJ,...}/` |

---

## SHARED STATE DEFINITION

Every agent in the system shares this state object. Define it once in `state.py` and import it in every agent file.

```python
# state.py
from typing import TypedDict, Optional, List, Dict, Any

class S2CState(TypedDict):
    # Current processing context
    cluster_id: Optional[str]           # Consolidation_Cluster_ID being processed
    rfq_id: Optional[str]               # RFQ_ID being processed
    nfa_id: Optional[str]               # NFA_ID being processed
    po_ref_id: Optional[str]            # PO_Reference ID being processed

    # Pipeline routing
    current_agent: str                   # Which agent is running
    next_agent: Optional[str]           # Which agent to run next (routing)
    pr_status: Optional[str]            # Current PR_Status from DB

    # Results from each agent (passed forward)
    consolidated_clusters: List[Dict]   # Output of PR.01
    specs_extracted: bool               # Output of PR.02
    buyer_assigned: Optional[str]       # Output of PR.03
    vendors_shortlisted: List[str]      # Output of RFQ.04
    rfq_created: bool                   # Output of RFQ.05
    evaluations_complete: bool          # Output of EVAL.08-10
    negotiated_price: Optional[float]   # Output of NEG.11-12
    nfa_approved: bool                  # Output of NFA.14
    po_created: bool                    # Output of PO.16
    sap_po_number: Optional[str]        # Output of PO.16

    # Control flags
    errors: List[str]                   # Accumulated errors
    compliance_results: Dict[str, str]  # Control ID → Pass/Fail
    should_stop: bool                   # Hard stop on critical failure

    # Config
    db_path: str                        # Path to s2c_sourcesense.db
    dms_root: str                       # Path to DMS_Documents folder
```

---

## DATABASE CONNECTION PATTERN

Use this pattern in every agent. Define once in `db.py`:

```python
# db.py
import sqlite3
from contextlib import contextmanager

DB_PATH = "s2c_sourcesense.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## DATABASE SCHEMA (tables used in Phase 1)

### Master_PR_Data (READ)
```
PR_Number (PK), Material_Code, Plant, Quantity, UOM, Requisitioner,
PR_Date, Delivery_Date, Budget_Code, PR_Status
```
Sample: `PR-2025-00852` through `PR-2025-00858` have `PR_Status = 'Open'`

### Material_Master (READ)
```
Material_Code (PK), Material_Description, Material_Group, HSN_SAC_Code,
Base_UOM, Category, Last_Purchase_Price, Standard_Lead_Time_Days,
Spec_Document_File_ID, Updated_At
```

### UOM_Conversion (READ)
```
From_UOM, To_UOM_Base, Conversion_Factor
```
Sample: DZ→NO = 12.0, GR→NO = 144.0

### Buyer_Master (READ/WRITE)
```
Buyer_ID (PK), Buyer_Name, Buyer_Email, Department, Designation,
Material_Group_Codes, Annual_Spend_Limit, Current_Workload, Max_Workload,
Manager_Email, Active_Status
```
Sample buyers: BUY-1001 (Ramesh Kumar, MRO-BRG/ELE/HYD/LUB/WLD, workload 8/15)

### DOP (READ)
```
DOP_ID, Value_Range_Min, Value_Range_Max, Tier_Level, Approver_Designation
```
Tiers: T1 ≤5L, T2 5-20L, T3 20-50L, T4 50L-2Cr, T5 >2Cr

### Designations_Master (READ)
```
Designation_Code, Employee_Name, Employee_Email
```

### Consolidated_PRs (WRITE)
```
Consolidation_Cluster_ID (PK), PR_Number, Material_Code, Material_Group,
Description, Long_Text_Specifications, Quantity, UOM, UOM_Base, Total_Value,
Currency, Plant, Cost_Center, Capex_Opex, Procurement_Category, PR_Status,
Assigned_Buyer, Payment_Terms, Delivery_Date, RFQ_ID, NFA_Status,
Repeat_Emergency_Flag, Budget_Overrun_Flag, Created_At, Buyer_Assigned_At,
Comm_Terms_Received_At, RFQ_Generated_At, RFQ_Approved_At, RFQ_Dispatched_At,
NFA_Approved_At, PO_Created_At, Closed_At
```

### Spec_Requests (WRITE)
```
Spec_Request_ID (PK), Consolidation_Cluster_ID, Requested_From, Status,
File_ID, Created_At
```

### Compliance_Log (WRITE)
```
Compliance_ID (PK), Control_ID, Entity_Type, Entity_ID, Result, Details,
Checked_At, Override_By, Override_Reason
```

### Approval_Log (WRITE)
```
Approval_ID (PK), Entity_Type, Entity_ID, Approver_Email, Approver_Designation,
Decision, Comments, Decided_At
```

### Process_Events_Log (WRITE)
```
Event_ID (PK), Process_ID, Entity_Type, Entity_ID, Event_Type,
Event_Description, Actor, Created_At
```

---

## PHASE 1: GENERATE THESE FILES

### FILE 1: `agents/pr_01_consolidation.py`

**Agent:** PR Consolidator
**Process ID:** S2C.PR.01
**LangGraph node name:** `pr_consolidation`
**Trigger:** Scheduled every 15 minutes, or called directly

```python
# Full implementation required — do not stub or use pass

def pr_consolidation(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.01 — Purchase Requisition Consolidation

    Steps:
    1. Read Master_PR_Data WHERE PR_Status = 'Open'
    2. For each PR, join Material_Master for description, group, LPP, base UOM
    3. Convert UOM using UOM_Conversion table (multiply Quantity × Conversion_Factor)
    4. Call Gemini to cluster PRs: group by Material_Code first, then use AI
       to suggest if any different-material PRs in same Material_Group
       should be combined (same plant, same delivery window)
    5. For each cluster:
       - Generate Consolidation_Cluster_ID = f"CL-{YYYY}-{seq:05d}-01"
       - Sum quantities (in base UOM)
       - Total_Value = quantity × Last_Purchase_Price (or 0 if no LPP)
       - INSERT into Consolidated_PRs with PR_Status = 'New'
    6. UPDATE Master_PR_Data SET PR_Status = 'Consolidated'
    7. CTRL-006: if Total_Value > 10,000,000 INR flag Budget_Overrun_Flag = 1
    8. CTRL-017: check Procurement_Historical_Pricing for same material
       purchased < 30 days ago → set Repeat_Emergency_Flag = 1
    9. INSERT Process_Events_Log for each cluster
    10. INSERT Compliance_Log for CTRL-006 and CTRL-017 results

    Returns updated state with consolidated_clusters list.
    """
```

**Gemini prompt template to use inside the agent:**
```
You are a procurement clustering AI for a steel plant.
Given these open Purchase Requisitions:
{pr_list_json}

Group them into procurement clusters following these rules:
1. Same Material_Code = always same cluster (combine quantities)
2. Different Material_Code but same Material_Group AND same Plant AND
   delivery dates within 14 days = suggest clustering (output reasoning)
3. Never cluster materials from different Material_Groups

Return JSON: [{"cluster_name": "...", "pr_numbers": [...], "reason": "..."}]
```

---

### FILE 2: `agents/pr_02_spec_extraction.py`

**Agent:** Spec Extractor
**Process ID:** S2C.RFQ.02
**LangGraph node name:** `spec_extraction`

```python
def spec_extraction(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.02 — Technical Specification Extraction

    Steps:
    1. Read Consolidated_PRs WHERE PR_Status = 'New'
    2. For each cluster, check Material_Master.Spec_Document_File_ID
    3. If Spec_Document_File_ID exists:
       - Look up DMS_Documents for file_path
       - Read the file content (text extraction from path)
       - Call Gemini to extract structured specs
    4. If no spec doc:
       - INSERT Spec_Requests (Status='Pending', Requested_From=requisitioner)
       - Send email to requisitioner via smtplib
       - Mark cluster PR_Status = 'Specs_Pending' and skip
    5. UPDATE Consolidated_PRs.Long_Text_Specifications with extracted specs
    6. UPDATE Consolidated_PRs.PR_Status = 'Specs_Ready'
    7. INSERT Process_Events_Log

    Gemini spec extraction prompt:
    "Extract structured technical specifications from this document.
     Output JSON: {dimensions: {...}, standards: [...], alternatives: [...],
     critical_parameters: [...], inspection_requirements: [...]}"
    """
```

---

### FILE 3: `agents/pr_03_buyer_assignment.py`

**Agent:** Buyer Assigner
**Process ID:** S2C.RFQ.03
**LangGraph node name:** `buyer_assignment`

```python
def buyer_assignment(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.03 — Buyer Assignment + DOP Routing

    Steps:
    1. Read Consolidated_PRs WHERE PR_Status = 'Specs_Ready'
    2. For each cluster, read Buyer_Master WHERE Active_Status = 'Active'
    3. Match buyer: Material_Group must be in buyer's Material_Group_Codes
    4. Among matching buyers, pick lowest Current_Workload / Max_Workload ratio
    5. Verify buyer's Annual_Spend_Limit >= cluster's Total_Value
    6. If no buyer available: email Manager_Email of any matching buyer
    7. UPDATE Consolidated_PRs: Assigned_Buyer, PR_Status='Buyer_Assigned',
       Buyer_Assigned_At = now()
    8. UPDATE Buyer_Master: Current_Workload += 1
    9. DOP routing: query DOP table for cluster Total_Value range
    10. INSERT Approval_Log with required approver from Designations_Master
    11. INSERT Process_Events_Log
    12. Send email to buyer (cluster summary + approval link)
    """
```

---

### FILE 4: `graphs/phase1_graph.py`

Wire the three nodes into a LangGraph StateGraph:

```python
# graphs/phase1_graph.py
from langgraph.graph import StateGraph, END
from state import S2CState
from agents.pr_01_consolidation import pr_consolidation
from agents.pr_02_spec_extraction import spec_extraction
from agents.pr_03_buyer_assignment import buyer_assignment

def build_phase1_graph():
    graph = StateGraph(S2CState)

    graph.add_node("pr_consolidation", pr_consolidation)
    graph.add_node("spec_extraction", spec_extraction)
    graph.add_node("buyer_assignment", buyer_assignment)

    graph.set_entry_point("pr_consolidation")

    # Routing: after consolidation, check if any clusters were created
    def route_after_consolidation(state):
        if state.get("should_stop"):
            return END
        if state.get("consolidated_clusters"):
            return "spec_extraction"
        return END

    graph.add_conditional_edges("pr_consolidation", route_after_consolidation)

    # After spec extraction, route to buyer assignment or wait for specs
    def route_after_specs(state):
        if state.get("should_stop"):
            return END
        if state.get("specs_extracted"):
            return "buyer_assignment"
        return END  # Some clusters may be waiting for spec docs

    graph.add_conditional_edges("spec_extraction", route_after_specs)
    graph.add_edge("buyer_assignment", END)

    return graph.compile()

# Run it:
if __name__ == "__main__":
    app = build_phase1_graph()
    initial_state = S2CState(
        cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
        current_agent="pr_consolidation", next_agent=None,
        pr_status=None, consolidated_clusters=[], specs_extracted=False,
        buyer_assigned=None, vendors_shortlisted=[], rfq_created=False,
        evaluations_complete=False, negotiated_price=None, nfa_approved=False,
        po_created=False, sap_po_number=None, errors=[], compliance_results={},
        should_stop=False,
        db_path="s2c_sourcesense.db",
        dms_root="DMS_Documents"
    )
    result = app.invoke(initial_state)
    print("Phase 1 complete:", result)
```

---

## EXISTING DATA IN DATABASE

7 open PRs ready for PR.01 to consolidate:
- `PR-2025-00852` → Material `1000-10067001` (Hydraulic Cylinder), Plant 1010, Qty 6
- `PR-2025-00853` → Material `1000-10067002` (Hydraulic Hose), Plant 1010, Qty 100M
- `PR-2025-00854` → Material `1000-10078001` (Servo 68 Oil), Plant 1010, Qty 10 DR
- `PR-2025-00855` → Material `1000-10089001` (Welding Rod), Plant 1010, Qty 200 KG
- `PR-2025-00856` → Material `1000-10055002` (Thermal Relay), Plant 1030, Qty 20
- `PR-2025-00857` → Material `1000-10042678` (Bearing 6205), Plant 1020, Qty 120
- `PR-2025-00858` → Material `1000-10089002` (MIG Wire), Plant 1020, Qty 60 KG

PRs 852+853 are both MRO-HYD at Plant 1010 — Gemini should likely cluster these together.

5 existing clusters at various pipeline stages (do not re-process these):
- `CL-2025-00847-01` → PR_Status='NFA_Approved' (most advanced — ready for PO)
- `CL-2025-00848-01` → PR_Status='RFQ_Evaluation'
- `CL-2025-00850-01` → PR_Status='RFQ_Dispatched'
- `CL-2025-00851-01` → PR_Status='Buyer_Assigned'
- `CL-2025-00852-01` → PR_Status='New'

---

## OUTPUT INSTRUCTIONS

Generate complete, executable Python files — not stubs. Every function must have:
- Full SQL queries (not comments like "# query here")
- Proper error handling with try/except — on error append to `state["errors"]`
- All DB writes committed
- LangSmith-compatible (the StateGraph structure handles tracing automatically)
- Logging via Python `logging` module (INFO level)

Generate files in this order:
1. `state.py`
2. `db.py`
3. `config.py` (DB_PATH, DMS_ROOT, Gemini API key, SMTP config as env vars)
4. `agents/pr_01_consolidation.py`
5. `agents/pr_02_spec_extraction.py`
6. `agents/pr_03_buyer_assignment.py`
7. `graphs/phase1_graph.py`
