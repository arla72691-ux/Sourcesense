# S2C Sourcesense — Complete Build Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              SOURCESENSE S2C PLATFORM                   │
│                                                         │
│  Python + LangGraph (agent framework)                   │
│  SQLite (SAP-mimic database — s2c_sourcesense.db)       │
│  Gemini 2.5 Pro (AI decisions, NFA drafting, scoring)   │
│  LangSmith (free tracing UI — visual graph output)      │
│  Local DMS folder (document storage)                    │
│  smtplib (email — built into Python)                    │
└─────────────────────────────────────────────────────────┘
```

**No n8n required.** Everything runs as Python files you execute locally.

---

## What's In This Folder

| File | Type | Purpose |
|------|------|---------|
| `s2c_sourcesense.db` | SQLite DB | All 27 tables, pre-populated with 227 rows of master + pipeline data |
| `DMS_Documents/` | Folder | Document storage (RFQ, NFA, PO, Specs, SVJ, Onboarding...) |
| `Phase1_PR_Agents_PR01_PR03.md` | Gemini Prompt | Generates Python files for PR agents |
| `Phase2_RFQ_Eval_Agents_RFQ04_EVAL10.md` | Gemini Prompt | Generates Python files for RFQ + Evaluation agents |
| `Phase3_Negotiation_NFA_Agents_NEG11_NFA14.md` | Gemini Prompt | Generates Python files for Negotiation + NFA agents |
| `Phase4_PO_Agents_PO15_PO19.md` | Gemini Prompt | Generates Python files for PO agents + master runner |

---

## What Gemini 2.5 Pro Will Generate (Python Files)

After pasting all 4 prompts, you will have:

```
sourcesense/
├── state.py                          ← Shared LangGraph state (TypedDict)
├── db.py                             ← SQLite connection manager
├── config.py                         ← Environment config (API keys, paths)
├── run.py                            ← Main entry point (CLI runner)
├── requirements.txt                  ← pip install this
├── .env.example                      ← Copy to .env, fill in keys
├── README.md
├── agents/
│   ├── pr_01_consolidation.py        ← PR.01: Cluster raw PRs from SAP
│   ├── pr_02_spec_extraction.py      ← PR.02: Extract tech specs (Gemini)
│   ├── pr_03_buyer_assignment.py     ← PR.03: Match buyer, DOP routing
│   ├── rfq_04_vendor_shortlisting.py ← RFQ.04: Score + shortlist vendors (Gemini)
│   ├── rfq_05_rfq_creation.py        ← RFQ.05: Generate RFQ document
│   ├── rfq_06_compliance_attach.py   ← RFQ.06: CTRL-001 pre-check, SVJ
│   ├── rfq_07_rfq_approval.py        ← RFQ.07: Multi-tier DOP approval
│   ├── rfq_08_rfq_dispatch.py        ← RFQ.08: Dispatch to vendors, CTRL-001 final
│   ├── rfq_09_offer_collection.py    ← RFQ.09: Follow up, collect quotes
│   ├── eval_08_tech_evaluation.py    ← EVAL: Score submissions vs specs (Gemini)
│   ├── eval_09_comm_evaluation.py    ← EVAL: Price/payment/delivery scoring
│   ├── eval_10_overall_ranking.py    ← EVAL: Weighted overall rank
│   ├── neg_11_negotiation_copilot.py ← NEG: AI intelligence brief + initiate (Gemini)
│   ├── neg_12_negotiation_approval.py← NEG: BAFO intake + internal approval
│   ├── nfa_13_nfa_generation.py      ← NFA: Generate NFA document (Gemini)
│   ├── nfa_14_nfa_approval.py        ← NFA: Sequential multi-tier approval
│   ├── po_15_po_reference_creation.py← PO: Create STM tracking record
│   ├── po_16_sap_bapi_call.py        ← PO: Simulate SAP BAPI_PO_CREATE1
│   ├── po_17_po_document_attach.py   ← PO: Generate + save PO document
│   ├── po_18_vendor_dispatch.py      ← PO: Email PO to vendor, SLA monitoring
│   └── po_19_status_update.py        ← PO: Close lifecycle, update LPP
└── graphs/
    ├── phase1_graph.py               ← LangGraph wiring for PR agents
    ├── phase2_graph.py               ← LangGraph wiring for RFQ+Eval agents
    ├── phase3_graph.py               ← LangGraph wiring for Neg+NFA agents
    ├── phase4_graph.py               ← LangGraph wiring for PO agents
    └── master_graph.py               ← Master graph: full 19-agent pipeline
```

---

## Step-by-Step Build Process

### Step 1: Prerequisites You Install (one-time)

```bash
pip install langgraph langchain langchain-google-vertexai google-generativeai langsmith schedule python-dotenv
```

That's the only installation needed. SQLite and email are built into Python.

### Step 2: Copy database to your project folder

Copy `s2c_sourcesense.db` into your project root.

### Step 3: Paste Phase prompts into OpenCode-Vertex-Gemini 2.5 Pro

| Paste | File | Output |
|-------|------|--------|
| 1st | `Phase1_PR_Agents_PR01_PR03.md` | `state.py`, `db.py`, `config.py`, `agents/pr_01-03`, `graphs/phase1_graph.py` |
| 2nd | `Phase2_RFQ_Eval_Agents_RFQ04_EVAL10.md` | `agents/rfq_04-09`, `agents/eval_08-10`, `graphs/phase2_graph.py` |
| 3rd | `Phase3_Negotiation_NFA_Agents_NEG11_NFA14.md` | `agents/neg_11-12`, `agents/nfa_13-14`, `graphs/phase3_graph.py` |
| 4th | `Phase4_PO_Agents_PO15_PO19.md` | `agents/po_15-19`, `graphs/phase4_graph.py`, `graphs/master_graph.py`, `run.py`, `requirements.txt`, `.env.example`, `README.md` |

### Step 4: Configure environment

```bash
cp .env.example .env
# Fill in: GEMINI_API_KEY, LANGCHAIN_API_KEY, SMTP credentials
```

### Step 5: Run the pipeline

```bash
python run.py --phase 1          # Test PR agents (processes 7 open PRs)
python run.py --phase 4          # Test PO agents (CL-2025-00847-01 is ready)
python run.py --phase all        # Full pipeline
python run.py --simulate po      # Quick simulate PO for the bearing cluster
```

### Step 6: View agent traces in LangSmith

Open https://smith.langchain.com → Project "sourcesense-s2c"
You'll see: agent node → inputs → outputs → Gemini calls → timing → errors

### Step 7: View the agent graph as a diagram

```bash
python -c "
from graphs.master_graph import build_master_graph
app = build_master_graph()
print(app.get_graph().draw_mermaid())
"
```
Paste the Mermaid output into https://mermaid.live — you get a visual flowchart of all 19 agents.

---

## Why LangGraph? (vs n8n)

| | n8n | LangGraph |
|--|-----|-----------|
| Runtime | Server required 24/7 | Pure Python, runs anywhere |
| Agent logic | JSON nodes (opaque) | Plain Python (readable, debuggable) |
| AI integration | HTTP Request node | Native Gemini SDK |
| Visual output | n8n canvas (design time) | LangSmith traces (runtime) + Mermaid graph |
| Cost | Community edition limits | Free and open source |
| Gemini output | Need to convert JSON → n8n | Generates Python directly |
| State between agents | Variables/expressions | TypedDict — strongly typed |
| Error handling | Limited | Full Python try/except + state flags |

---

## 19-Agent Pipeline Map

| Agent | File | Trigger | Key Input | Key Output |
|-------|------|---------|-----------|------------|
| PR.01 | pr_01_consolidation | Scheduled / on-demand | Master_PR_Data (Open) | Consolidated_PRs (New) |
| PR.02 | pr_02_spec_extraction | After PR.01 | Consolidated_PRs (New) | Specs extracted |
| PR.03 | pr_03_buyer_assignment | After PR.02 | Buyer_Master | Buyer assigned |
| RFQ.04 | rfq_04_vendor_shortlisting | After PR.03 | Vendor_Master, Supplier_Master | Vendor_Shortlist |
| RFQ.05 | rfq_05_rfq_creation | After RFQ.04 | Consolidated_PRs | RFQ_Log (Draft) |
| RFQ.06 | rfq_06_compliance_attach | After RFQ.05 | Vendor_Shortlist | CTRL-001 check |
| RFQ.07 | rfq_07_rfq_approval | After RFQ.06 | DOP, Designations_Master | Approval_Log |
| RFQ.08 | rfq_08_rfq_dispatch | After approval | Vendor_Shortlist | RFQ_Dispatch_Log |
| RFQ.09 | rfq_09_offer_collection | Scheduled daily | RFQ_Dispatch_Log | RFQ_Submissions |
| EVAL.08 | eval_08_tech_evaluation | After submissions close | RFQ_Submissions | RFQ_Tech_Evaluations |
| EVAL.09 | eval_09_comm_evaluation | After EVAL.08 | RFQ_Submissions | RFQ_Comm_Evaluations |
| EVAL.10 | eval_10_overall_ranking | After EVAL.09 | Tech+Comm evals | RFQ_Overall_Evaluations |
| NEG.11 | neg_11_negotiation_copilot | After EVAL.10 | Pricing history | Negotiation_Intelligence_Log |
| NEG.12 | neg_12_negotiation_approval | Webhook (vendor BAFO) | BAFO price | Negotiation_Shortlist_Approval |
| NFA.13 | nfa_13_nfa_generation | After NEG.12 | All evaluations | NFA_Log, NFA document |
| NFA.14 | nfa_14_nfa_approval | After NFA.13 | DOP, Designations | NFA_Approval_Log |
| PO.15 | po_15_po_reference_creation | After NFA.14 | NFA_Log (Approved) | PO_Reference |
| PO.16 | po_16_sap_bapi_call | After PO.15 | PO_Reference | SAP_PO_Data |
| PO.17 | po_17_po_document_attach | After PO.16 | SAP_PO_Data | DMS PO document |
| PO.18 | po_18_vendor_dispatch | After PO.17 | PO document | Vendor email + ACK |
| PO.19 | po_19_status_update | After PO.18 | PO_Reference | Cluster closed, LPP updated |

---

## Database Statistics (Fully Expanded)

| Category | Count |
|----------|-------|
| Material groups | 26 |
| Material codes (Material_Master) | 232 |
| Active vendors (Vendor_Master) | 44 + 1 blacklisted |
| Buyers (Buyer_Master) | 10 |
| DOP approval tiers | 4 levels × 2 tracks (Supply + Capital) |
| Pipeline clusters (Consolidated_PRs) | 16 |
| Raw open PRs for PR.01 to process | 10 |
| RFQ logs | 10 |
| Vendor shortlists | 27 |
| Dispatch records | 22 |
| Vendor submissions | 14 |
| Tech / Comm / Overall evaluations | 14 each |
| NFA records | 3 (2 Approved, 1 Under Approval) |
| SAP PO records | 1 (4500098710 — bearing cluster) |
| DMS documents | 50 |
| Compliance checks | 26 |
| Process events | 85 |
| **Total rows** | **688** |

---

## Test Data In Database

| Cluster | Material | Stage | Test Target |
|---------|----------|-------|-------------|
| CL-2025-00847-01 | Bearings 6205-2RS | NFA_Approved | PO 4500098710 exists — run PO.18/19 to dispatch + close |
| CL-2025-00862-01 | Alumina Brick 70% | NFA_Approved | **Start PO flow: PO.16 → PO.19** |
| CL-2025-00863-01 | Carbon Electrode 300mm | Under_NFA_Approval | Run NFA.14 (approve) → PO.15+ |
| CL-2025-00848-01 | Spherical Roller 22210 | RFQ_Evaluation | Eval complete — run NEG.11 → NFA chain |
| CL-2025-00864-01 | Oil Filter LF3349 | RFQ_Evaluation | Eval complete — run NEG.11 → NFA chain |
| CL-2025-00850-01 | Contactor 25A | RFQ_Dispatched | Run RFQ.09 (offer collection) |
| CL-2025-00865-01 | Safety Helmet HDPE | RFQ_Dispatched | Run RFQ.09 (offer collection) |
| CL-2025-00866-01 | V-Belt B-75 | RFQ_Dispatched | Run RFQ.09 (offer collection) |
| CL-2025-00860-01 | Hydraulic Oil 210L | RFQ_Generated | Run RFQ.07 (approve) → RFQ.08 (dispatch) |
| CL-2025-00868-01 | Gate Valve 2in | RFQ_Generated | Run RFQ.07 → RFQ.08 dispatch |
| CL-2025-00851-01 | VFD Drive 7.5kW | Buyer_Assigned | Run RFQ.04 (shortlist) → full chain |
| CL-2025-00867-01 | TEFC Motor 15kW | Buyer_Assigned | Run RFQ.04 → full chain |
| CL-2025-00861-01 | Welding Rod E6013 | Buyer_Assigned | Run RFQ.04 → full chain |
| CL-2025-00852-01 | Hydraulic Cylinder 80mm | Specs_Ready | Run RFQ.04+ |
| CL-2025-00869-01 | Power Cable 4C 16mm2 | Specs_Ready | Run RFQ.04+ |
| CL-2025-00870-01 | HT Bolt M20x80 | New | Run PR.02 (specs) → full chain |
| PR-2025-00859 to 00868 | 10 open raw PRs | Open | Run PR.01 (consolidation) |
