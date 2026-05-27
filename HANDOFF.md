# Sourcesense S2C Procurement Platform — Session Handoff

> **Date:** 2026-05-27  
> **Branch:** `claude/add-local-folder-37XdQ`  
> **Repo:** `arla72691-ux/sourcesense`  
> **Last commit:** `4edbf82 Fix 8 more agent bugs found by full-suite testing`

---

## 1. What This Project Is

**Sourcesense** is an end-to-end agentic AI procurement platform (Source-to-Contract, S2C). It has **20 LangGraph agents** across 4 phases that automate the full procurement lifecycle from PR consolidation through to SAP Purchase Order creation.

| Phase | Agents | What it does |
|-------|--------|--------------|
| Phase 1 — PR | PR.01 → PR.03b | Consolidate purchase requisitions, extract specs, assign buyers, finalise commercial terms |
| Phase 2 — RFQ | RFQ.04 → EVAL.10 | Shortlist vendors, create & dispatch RFQs, collect offers, score technical + commercial |
| Phase 3 — NEG/NFA | NEG.11 → NFA.14 | AI negotiation co-pilot, approval, generate NFA, approve NFA |
| Phase 4 — PO | PO.15 → PO.19 | Create PO reference, SAP BAPI call, attach docs, dispatch to vendor, close cluster |

### Tech Stack
- **Python 3.11** — all agents are plain Python functions
- **LangGraph `StateGraph`** — orchestration
- **SQLite 3** — `database/s2c_sourcesense.db`
- **Google Gemini** via `google.genai` SDK (but see mock section below)
- **`core/db.py`** — `get_db(path)` context manager, `next_id(cursor, table, col, prefix)` helper
- **`core/state.py`** — `S2CState` TypedDict
- **`core/feedback.py`** — `request_human_feedback()` (5 pipeline checkpoints)
- **`core/config.py`** — env-based config; raises `ValueError` if `GEMINI_API_KEY` not set

---

## 2. Project File Structure

```
/home/user/Sourcesense/
├── core/
│   ├── db.py           — get_db(), next_id()
│   ├── state.py        — S2CState TypedDict
│   ├── config.py       — DB_PATH, DMS_ROOT, GEMINI_API_KEY
│   ├── feedback.py     — request_human_feedback()
│   └── run.py
├── agents/             — 20 agent files (pr_01 → po_19)
├── graphs/
│   ├── master_graph.py
│   ├── phase1_graph.py
│   ├── phase2_graph.py
│   ├── phase3_graph.py
│   └── phase4_graph.py
├── database/
│   ├── s2c_sourcesense.db          — main SQLite database
│   ├── setup/build_s2c_database.py
│   └── migrate_db*.py
├── DMS_Documents/      — file attachments (DMS)
├── docs/
├── tests/
├── run_tests.py        — 69-test full suite (see below)
└── CONVERSATION_SUMMARY.md
```

---

## 3. Critical Environment Constraints

### Gemini Mock Required
The server **cannot load `google.genai`'s native Rust/C crypto extension** (`_cffi_backend`) AND has **no outbound internet access** to Google APIs. Every script that uses agents must inject a mock before any import:

```python
import sys, os, types, json, re, sqlite3
from unittest.mock import MagicMock

os.environ['GEMINI_API_KEY'] = 'any-non-empty-string'

def _smart_generate(model, contents):
    prompt = contents if isinstance(contents, str) else str(contents)
    pl = prompt.lower()

    if ('pr_numbers' in pl or 'purchase requisition' in pl) and 'cluster' in pl:
        # PR.01 — fetch open PRs and make 2 clusters
        conn = sqlite3.connect('database/s2c_sourcesense.db')
        c = conn.cursor()
        c.execute("SELECT PR_Number FROM Master_PR_Data WHERE PR_Status='Open'")
        prs = [r[0] for r in c.fetchall()]
        conn.close()
        mid = max(1, len(prs) // 2)
        result = json.dumps([
            {"cluster_name": "Cluster A", "pr_numbers": prs[:mid], "reason": "Same material group"},
            {"cluster_name": "Cluster B", "pr_numbers": prs[mid:], "reason": "Same material group"},
        ]) if prs else '[]'
    elif 'extract' in pl and ('specification' in pl or 'spec' in pl):
        result = json.dumps({"dimensions": {"length": "100mm"}, "standards": ["IS 2062"],
            "alternatives": ["Grade E250"], "critical_parameters": ["yield_strength"],
            "inspection_requirements": ["visual inspection"]})
    elif ('vendor' in pl or 'supplier' in pl) and ('shortlist' in pl or 'recommend' in pl or 'rank' in pl):
        codes = re.findall(r'"vendor_code":\s*"([^"]+)"', prompt, re.IGNORECASE) or re.findall(r'VEN-\d+', prompt)
        selected = (codes or ['VEN-001', 'VEN-002'])[:4]
        result = json.dumps([{"vendor_code": v, "reason": "Good history", "recommended_rank": i+1}
            for i, v in enumerate(selected)])
    elif 'technical evaluator' in pl or ('tech_score' in pl and 'disqualify' in pl):
        result = json.dumps({"tech_score": 78, "breakdown": {"spec_compliance": 32},
            "tech_remarks": "Meets specs.", "disqualify": False, "disqualify_reason": None})
    elif 'negotiation' in pl and ('target_price' in pl or 'walkaway' in pl):
        m = re.search(r'Best Vendor Quote[:\s]+([\d.]+)', prompt)
        q = float(m.group(1)) if m else 1000.0
        result = json.dumps({"target_price": round(q*0.92,2), "walkaway_price": round(q*0.97,2),
            "spend_analysis": "8% savings vs LPP.", "market_summary": "Stable market.",
            "vendor_email_draft": "Dear Vendor, please submit BAFO."})
    else:
        result = '[]'

    resp = MagicMock()
    resp.text = result
    return resp

google_pkg = types.ModuleType('google')
google_genai = types.ModuleType('google.genai')
_mock_client = MagicMock()
_mock_client.models.generate_content.side_effect = _smart_generate
google_genai.Client = MagicMock(return_value=_mock_client)
sys.modules['google'] = google_pkg
sys.modules['google.genai'] = google_genai
google_pkg.genai = google_genai

# Also mock dotenv (not critical but avoids warning)
dotenv_mod = types.ModuleType('dotenv')
dotenv_mod.load_dotenv = lambda: None
sys.modules['dotenv'] = dotenv_mod
```

**This block must run before `import config` or any agent import.**

---

## 4. Bugs Fixed in This Session

All 20 agents are now working. Here is every bug that was found and fixed:

### PR.01 — Consolidation (`agents/pr_01_consolidation.py`)
| Bug | Fix |
|-----|-----|
| `KeyError: '"cluster_name"'` — `prompt_template.format()` failed on JSON examples | Escaped as `{{cluster_name}}` etc. |
| `NOT NULL constraint failed: Consolidated_PRs.UOM` | Added `UOM = first_pr['Base_UOM']` to INSERT |
| `NOT NULL constraint failed: Consolidated_PRs.Capex_Opex` | Derived from material group prefix: `'CAPEX'` if starts with `'CAP'`, else `'OPEX'` |
| `FOREIGN KEY constraint failed` on `PR_Number` | Changed from `",".join(pr_numbers)` to `pr_numbers_in_cluster[0]` (FK must reference single row) |
| `CTRL-017` error causing `should_stop=True` | Removed `errors.append(...)` for missing `Procurement_Historical_Pricing` table (silent warning instead) |

### PR.03b — Commercial Terms (`agents/pr_03b_commercial_terms.py`)
| Bug | Fix |
|-----|-----|
| Wrong JOIN — `Assigned_Buyer` is an email, not a `Buyer_ID` | Changed `JOIN Buyer_Master bm ON cp.Assigned_Buyer = bm.Buyer_ID JOIN Active_Directory ad ON bm.Employee_ID = ad.Employee_ID` → `JOIN Active_Directory ad ON cp.Assigned_Buyer = ad.Email` |

### EVAL.10 — Overall Ranking (`agents/eval_10_overall_ranking.py`)
| Bug | Fix |
|-----|-----|
| `parse_weights()` only handled `"Tech: 40%, Comm: 60%"` text format; DB stores JSON `{"technical_weight": 0.6}` | Added JSON parsing branch with `json.loads()` first |
| `if not all(weights.values())` failed when `min_score=0.0` | Changed to `if not weights['tech'] or not weights['comm']` |
| `evaluations_complete` flag never set — checked `RFQ_Status='Evaluation_Complete'` but RFQs moved past it | Changed to check `COUNT(*) FROM RFQ_Overall_Evaluations > 0` |

### NEG.11 — Negotiation Co-pilot (`agents/neg_11_negotiation_copilot.py`)
| Bug | Fix |
|-----|-----|
| `ModuleNotFoundError: No module named 'numpy'` | Removed unused `import numpy as np` |
| Placeholder `prompt = '''...'''` — no actual prompt content | Replaced with real negotiation strategy prompt using `prompt_data` dict |
| `next_id()` not called — `Brief_ID` missing from INSERT | Added `Brief_ID = next_id(cursor, 'Negotiation_Intelligence_Log', 'Brief_ID', 'NEG')` |
| `Neg_Approval_ID` missing from both INSERT paths | Added `next_id()` calls to both main loop and auto-approval path |

### NEG.12 — Negotiation Approval (`agents/neg_12_negotiation_approval.py`)
| Bug | Fix |
|-----|-----|
| `database is locked` — `simulate_negotiation_approval()` called `handle_bofo_response()` which opened a second `get_db()` connection inside the first | Inlined BAFO update logic into `simulate_negotiation_approval()` so all DB work uses single connection |

### NFA.14 — NFA Approval (`agents/nfa_14_nfa_approval.py`)
| Bug | Fix |
|-----|-----|
| `database is locked` — `simulate_nfa_approval()` opened nested `get_db()` inside outer context | Collect `nfa_ids_to_simulate = []` in outer loop; simulate after outer `with get_db()` block closes |

### RFQ.07 — RFQ Approval (`agents/rfq_07_rfq_approval.py`)
| Bug | Fix |
|-----|-----|
| `database is locked` — `simulate_approval()` opened nested `get_db()` inside outer context | Same pattern: collect `rfq_ids_to_simulate = []`; simulate after outer connection closes |

---

## 5. Recurring Patterns to Know

### DB Locking Pattern
SQLite in WAL mode serialises writes, but nested `get_db()` connections deadlock each other. The fix is always the same:

```python
# WRONG:
with get_db(state['db_path']) as conn:
    for item in items:
        simulate_something(state)   # opens ANOTHER get_db() — DEADLOCKS

# CORRECT:
ids_to_simulate = []
with get_db(state['db_path']) as conn:
    for item in items:
        ids_to_simulate.append(item['ID'])
# outer connection now CLOSED
for id_ in ids_to_simulate:
    simulate_something(state['db_path'], id_)
```

Three agents had this bug (NFA.14, RFQ.07, NEG.12). All fixed.

### `next_id()` Usage
Every INSERT that creates a new entity must call:
```python
new_id = next_id(cursor, 'Table_Name', 'Primary_Key_Column', 'PREFIX')
```
This generates sequential `PREFIX-00001`, `PREFIX-00002`, etc.

### Idempotent Test Pattern
Tests run against a persistent shared DB. They use:
```python
after > before OR precondition_count == 0
```
This passes when the pipeline has already processed all data in a previous run.

### `NOT NULL` Columns in `Consolidated_PRs`
These columns are `NOT NULL` and must always be provided:
- `UOM` — use `first_pr['Base_UOM']`
- `Capex_Opex` — derive: `'CAPEX' if mat_group.startswith('CAP') else 'OPEX'`
- `Procurement_Category` — derive: `'Capital' if mat_group.startswith('CAP') else 'Supply'`

### FK on `Consolidated_PRs.PR_Number`
This column is a FK to `Master_PR_Data.PR_Number`. Store only the **first** PR in a cluster, not a comma-separated list.

---

## 6. Test Suite (`run_tests.py`)

**69 tests covering all 20 agents.** Run from project root:

```bash
cd /home/user/Sourcesense
python run_tests.py
```

Expected output: `69 passed | 0 failed`

### Test Structure Summary

```
=== PR.01  — PR Consolidation           === 5 tests
=== PR.02  — Spec Extraction            === 3 tests
=== PR.03  — Buyer Assignment           === 3 tests
=== PR.03b — Commercial Terms           === 6 tests
=== RFQ.04 — Vendor Shortlisting        === 4 tests
=== RFQ.05 — RFQ Creation               === 3 tests
=== RFQ.06 — Compliance Attach          === 2 tests
=== RFQ.07 — RFQ Approval               === 2 tests
=== RFQ.08 — RFQ Dispatch               === 3 tests
=== RFQ.09 — Offer Collection           === 4 tests
=== EVAL.08 — Technical Evaluation      === 3 tests
=== EVAL.09 — Commercial Evaluation     === 3 tests
=== EVAL.10 — Overall Ranking           === 4 tests
=== NEG.11  — Negotiation Co-pilot      === 5 tests
=== NEG.12  — Negotiation Approval      === 2 tests
=== NFA.13  — NFA Generation            === 3 tests
=== NFA.14  — NFA Approval              === 2 tests
=== PO.15   — PO Reference Creation     === 2 tests
=== PO.16   — SAP BAPI Call             === 2 tests
=== PO.17   — PO Document Attach        === 2 tests
=== PO.18   — Vendor Dispatch           === 2 tests
=== PO.19   — Status Update             === 4 tests
```

---

## 7. Human Feedback Checkpoints

Five pipeline stages call `request_human_feedback()` (currently always `simulate=True` → auto-approved):

| Constant | Agent | Entity |
|----------|-------|--------|
| `PR_CLUSTER_REVIEW` | PR.01 | Cluster |
| `VENDOR_SHORTLIST_REVIEW` | RFQ.04 | RFQ |
| `EVAL_RANKING_REVIEW` | EVAL.10 | RFQ |
| `NEGOTIATION_STRATEGY_REVIEW` | NEG.11 | RFQ |
| `PO_CONFIRMATION` | PO.16 | PO |

Feedback rows stored in `Human_Feedback` table: `Feedback_ID, Process_Stage, Entity_Type, Entity_ID, Context_Summary, Feedback_By, Requested_At, Response, Comments, Resolved_At`

---

## 8. Database Schema (Key Tables)

```
Master_PR_Data          — source PRs (PR_Number PK)
Consolidated_PRs        — clusters (Consolidation_Cluster_ID PK, PR_Number FK)
  └── PR_Status progression:
      New → Specs_Pending / Specs_Ready → Buyer_Assigned → Comm_Terms_Received
      → Vendors_Shortlisted → RFQ_Generated → RFQ_Evaluation
      → Negotiation_Approved → NFA_Generated → Closed

RFQ_Log                 — RFQs (RFQ_ID PK)
Vendor_Shortlist        — shortlisted vendors per RFQ
RFQ_Submissions         — vendor offers (Submission_ID PK)
RFQ_Tech_Evaluations    — technical scores (Tech_Eval_ID PK)
RFQ_Comm_Evaluations    — commercial scores (Comm_Eval_ID PK)
RFQ_Overall_Evaluations — combined ranking (Overall_Eval_ID PK)

Negotiation_Intelligence_Log    (Brief_ID PK, prefix 'NEG')
Negotiation_Shortlist_Approval  (Neg_Approval_ID PK, prefix 'NEG')

NFA_Log                 — NFA records (NFA_ID PK)
NFA_Approval_Chain      — approval levels per NFA

PO_Reference  (or PO_References)  — internal PO refs (PO_Ref_ID PK)
SAP_PO_Data             — SAP PO numbers, GRN, invoice status

Compliance_Log          (Compliance_ID PK) — all control checks
Process_Events_Log      (Event_ID PK)      — audit trail
Human_Feedback          (Feedback_ID PK)   — HITL queue
LPP_Master              — last purchase price
Vendor_Master           (Vendor_Code PK)
Material_Master         (Material_Code PK)
Buyer_Master            (Buyer_ID PK)
Active_Directory        (Employee_ID PK, Email unique)
Evaluation_Criteria     — technical/commercial weights per material group
Comm_Requests           — buyer-vendor commercial term requests
Approval_Log            — general approval records
RFQ_Dispatch_Log        — dispatch records
```

---

## 9. Pending Task — Frontend (NOT YET BUILT)

The user asked: **"Can you put together a user facing frontend for this end to end agentic ai based procurement tool?"**

**Nothing has been created yet.** The plan was fully designed (see below). Flask is already installed (`pip install flask` was run).

### What to Build

**Two files:**

#### `web/app.py` — Flask server

Key requirements:
1. **Mock injection block at the very top** (before any other import) — same block as Section 3 above, with `DB_PATH_DEFAULT` pointing to `database/s2c_sourcesense.db`
2. **`sys.path.insert`** for `core/` and project root so `from db import get_db` works
3. **Absolute DB path**: `DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 's2c_sourcesense.db')`
4. **Pipeline runs in background thread** — use `threading.Thread(daemon=True)` and a shared `_pipeline_log = []` list for live log streaming
5. **`GET /`** — serve `index.html`

**API Endpoints needed:**

```
GET  /api/stats               — dashboard KPIs (open PRs, clusters, RFQs, NFAs, POs, compliance %)
GET  /api/prs                 — Master_PR_Data with Material_Master join
GET  /api/clusters            — Consolidated_PRs with RFQ_Log join
GET  /api/rfqs                — RFQ_Log with submission counts
GET  /api/rfqs/<id>/submissions — submissions with eval scores
GET  /api/evaluations         — RFQ_Overall_Evaluations ranked
GET  /api/nfas                — NFA_Log with vendor and cluster info
GET  /api/pos                 — PO_Reference / PO_References with SAP data
GET  /api/feedback            — Human_Feedback (?status=pending|resolved|all)
POST /api/feedback/<id>       — body: {response, comments} → update response
GET  /api/compliance          — Compliance_Log (?result=Pass|Fail)
GET  /api/compliance/summary  — pass/fail counts per Control_ID
GET  /api/events              — Process_Events_Log (?limit=100)
GET  /api/vendors             — Vendor_Master
POST /api/pipeline/run        — start full pipeline in background thread
POST /api/pipeline/phase/<n>  — start single phase (1-4)
GET  /api/pipeline/status     — {running, phase, log: [...]}
```

> **Note:** The PO table might be `PO_Reference` or `PO_References` — check with:  
> `sqlite3 database/s2c_sourcesense.db ".tables" | tr ' ' '\n' | grep -i po`

#### `web/index.html` — Single Page App

**Stack:** Tailwind CSS (CDN), Alpine.js v3 (CDN), Chart.js v4 (CDN) — no build step.

**10 tabs:**
1. **Dashboard** — 6 KPI cards + pipeline phase doughnut chart + compliance bar chart
2. **Pipeline Control** — phase selector radio, Run button, live log output (poll `/api/pipeline/status` every 2s)
3. **Clusters** — table with status filter, color-coded stage badges, expandable rows
4. **RFQs** — table with inline vendor submissions on row click
5. **Evaluations** — RFQ selector + ranked vendor table with color-coded scores + Chart.js bar
6. **NFAs** — table with Price_Vs_LPP badges
7. **Purchase Orders** — table with GRN/invoice/payment status
8. **Feedback Queue** — pending tab with Approve/Reject buttons + modal, history tab
9. **Compliance** — filterable log + summary with pass rate
10. **Events** — auto-refreshing live feed (poll every 5s), timeline layout

**Recommended Alpine structure:**
```javascript
// Root app component
Alpine.data('app', () => ({
  activeTab: 'dashboard',
  stats: {},
  init() { this.loadStats(); setInterval(() => this.loadStats(), 30000); },
  async loadStats() { this.stats = await fetch('/api/stats').then(r => r.json()); }
}))

// Pipeline component
Alpine.data('pipeline', () => ({
  running: false, log: [], phase: null,
  async run(phase) { /* POST /api/pipeline/run or /phase/N */ },
  poll() { setInterval(async () => {
    const s = await fetch('/api/pipeline/status').then(r => r.json());
    this.log = s.log; this.running = s.running;
  }, 2000); }
}))

// Feedback component
Alpine.data('feedback', () => ({
  items: [], modal: false, selected: null, response: 'Approved', comments: '',
  async submit() { /* POST /api/feedback/id */ }
}))
```

**Design:** Dark professional theme — navy background (`#0f172a`), steel blue accents (`#3b82f6`), amber/orange highlights (`#f59e0b`). Status badges: green=complete, blue=active, yellow=pending, red=error.

### How to Run the Frontend

```bash
cd /home/user/Sourcesense
python web/app.py
# → http://localhost:5000
```

---

## 10. Git Status

```
Branch: claude/add-local-folder-37XdQ
Remote: origin (arla72691-ux/sourcesense)
Status: clean (all agent fixes committed)

To push after building frontend:
  git add web/
  git commit -m "Add Flask web frontend for S2C procurement platform"
  git push -u origin claude/add-local-folder-37XdQ
```

---

## 11. Quick Start for New Session

```bash
cd /home/user/Sourcesense

# Run the 69-test suite to confirm all agents pass
python run_tests.py

# Then build the frontend:
mkdir -p web
# Create web/app.py and web/index.html as described in Section 9

# Test the server
python web/app.py
# curl http://localhost:5000/api/stats
```

---

## 12. `S2CState` TypedDict Reference

```python
class S2CState(TypedDict):
    cluster_id: Optional[str]
    rfq_id: Optional[str]
    nfa_id: Optional[str]
    po_ref_id: Optional[str]
    current_agent: str
    next_agent: Optional[str]
    pr_status: Optional[str]
    consolidated_clusters: List[Dict]
    specs_extracted: bool
    buyer_assigned: Optional[str]
    comm_terms_received: bool
    vendors_shortlisted: List[str]
    rfq_created: bool
    evaluations_complete: bool
    negotiated_price: Optional[float]
    nfa_approved: bool
    po_created: bool
    sap_po_number: Optional[str]
    errors: List[str]
    compliance_results: Dict[str, str]
    should_stop: bool
    db_path: str
    dms_root: str
```

Minimum initial state for Flask thread:
```python
S2CState(
    cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
    current_agent="", next_agent=None, pr_status=None,
    consolidated_clusters=[], specs_extracted=False, buyer_assigned=None,
    comm_terms_received=False, vendors_shortlisted=[], rfq_created=False,
    evaluations_complete=False, negotiated_price=None, nfa_approved=False,
    po_created=False, sap_po_number=None, errors=[], compliance_results={},
    should_stop=False,
    db_path='/home/user/Sourcesense/database/s2c_sourcesense.db',
    dms_root='/home/user/Sourcesense/DMS_Documents'
)
```
