# Sourcesense S2C — Project Journal & Conversation Summary

> This document records everything built, every decision made, and every lesson learned across the full design and build session for the Sourcesense S2C Procurement Intelligence Platform. Use it as a handoff document when continuing work on a new machine, iPad, or cloud environment.

---

## 1. What Was Built

The **Sourcesense S2C (Source-to-Contract) Procurement Intelligence Platform** is an AI-agent pipeline for a large steel manufacturing company (modelled on JSW Steel). It automates the full procurement lifecycle — from receiving a Purchase Requisition out of SAP, all the way through to PO creation — using 19 Gemini-powered AI agents orchestrated via LangGraph.

**No external workflow tool** (n8n, Zapier, etc.) is needed. The entire system is pure Python.

---

## 2. Architecture Decisions

### Why LangGraph (not n8n)?
n8n was originally used as a visual design aid during the early concept phase. It was replaced entirely because:
- LangGraph is directly executable Python — no server, no UI, no extra install
- Gemini 2.5 Pro outputs Python natively, making agent generation seamless
- LangSmith (free tier) provides a visual trace UI that replaces n8n's canvas for debugging
- The entire pipeline becomes a single `python run.py --phase all` command

### Why SQLite (not PostgreSQL/MySQL)?
- Zero-install, zero-config — runs as a file
- Perfectly mimics SAP tables in structure without requiring SAP
- `sqlite3` is in Python's standard library
- Can be replaced with Postgres later by changing only `db.py`

### Why Gemini 2.5 Pro (not GPT-4)?
- Google's Vertex AI was already in the tech stack
- `google-generativeai` SDK is simple and well-documented
- Gemini 2.5 Pro handles complex JSON output reliably
- **Important:** `google.generativeai` package is now deprecated — migration to `google.genai` is planned

### Why google.generativeai (not Vertex AI SDK)?
- Simpler authentication: just an API key from Google AI Studio
- No GCP project setup required for initial development
- The API key approach works identically in cloud or local environments

---

## 3. The 19-Agent Pipeline

| Agent | File | Trigger | What It Does |
|-------|------|---------|--------------|
| PR.01 | pr_01_consolidation.py | Open PRs in Master_PR_Data | Gemini clusters PRs by material group, plant, delivery date |
| PR.02 | pr_02_spec_extraction.py | New clusters | Extracts structured technical specs from PR long text |
| PR.03 | pr_03_buyer_assignment.py | Specs extracted | Assigns buyer based on material group and workload |
| RFQ.04 | rfq_04_vendor_shortlisting.py | Buyer_Assigned | Scores and shortlists 3-5 vendors using performance data |
| RFQ.05 | rfq_05_rfq_creation.py | Vendors shortlisted | Generates formal RFQ document |
| RFQ.06 | rfq_06_compliance_attach.py | RFQ created | Runs CTRL checks — SVJ if <3 vendors |
| RFQ.07 | rfq_07_rfq_approval.py | Compliance passed | Routes for DOP-based approval |
| RFQ.08 | rfq_08_rfq_dispatch.py | RFQ approved | Emails RFQ to shortlisted vendors |
| RFQ.09 | rfq_09_offer_collection.py | RFQ dispatched | Collects and logs vendor submissions |
| EVAL.08 | eval_08_tech_evaluation.py | Submissions received | Scores technical compliance 0-100 |
| EVAL.09 | eval_09_comm_evaluation.py | Tech eval done | Calculates price/payment/delivery scores |
| EVAL.10 | eval_10_overall_ranking.py | Comm eval done | Weighted final ranking (Tech 60%, Comm 40%) |
| NEG.11 | neg_11_negotiation_copilot.py | Ranking done | Gemini generates negotiation intelligence brief |
| NEG.12 | neg_12_negotiation_approval.py | Brief ready | Simulates BAFO negotiation approval |
| NFA.13 | nfa_13_nfa_generation.py | Negotiation approved | Gemini drafts full NFA document |
| NFA.14 | nfa_14_nfa_approval.py | NFA drafted | DOP-based NFA routing and approval |
| PO.15 | po_15_po_reference_creation.py | NFA approved | Creates PO tracking reference |
| PO.16 | po_16_sap_bapi_call.py | PO ref created | Simulates SAP BAPI_PO_CREATE1 (SQLite INSERT) |
| PO.17 | po_17_po_document_attach.py | SAP PO created | Generates and attaches PO document to DMS |
| PO.18 | po_18_vendor_dispatch.py | Doc attached | Emails PO to winning vendor |
| PO.19 | po_19_status_update.py | PO dispatched | Marks cluster Closed, updates all statuses |

---

## 4. Database Architecture

**File:** `database/s2c_sourcesense.db`
**Size:** ~384KB | **Tables:** 33 | **Rows:** 688 | **FK violations:** 0

### Four System Types

| Type | Purpose | Key Tables |
|------|---------|-----------|
| MDM (Master Data) | Reference data | Material_Master, Vendor_Master, Buyer_Master, DOP, Designations_Master |
| ERP (SAP mimic) | Transactional core | Master_PR_Data, Consolidated_PRs, SAP_PO_Data |
| STM (S2C Tracking) | Process state | RFQ_Log, NFA_Log, PO_Reference, all Eval tables |
| DMS (Documents) | File metadata | DMS_Documents |
| Compliance | Audit trail | Compliance_Log, Approval_Log, Process_Events_Log |

### Key Synthetic Data Volumes

| Table | Rows | Notes |
|-------|------|-------|
| Material_Master | 232 | 26 material groups (MRO-BRG, MRO-ELE, CAP-MOT, SRV-MNT, etc.) |
| Vendor_Master | 45 | 44 active + 1 blacklisted (for CTRL-007 testing) |
| Buyer_Master | 10 | With material group assignments and workload limits |
| DOP | 8 | 4 levels × 2 tracks (Supply: ≤25L/25L-2.5Cr/2.5Cr-25Cr/>25Cr; Capital: similar) |
| Consolidated_PRs | 16 | At 8 different pipeline stages — every agent has pre-existing data |
| Master_PR_Data | 26 | 10 open raw PRs for PR.01 + 16 consolidated |
| RFQ_Log | 10 | RFQs across all stages |
| RFQ_Submissions | 14 | Vendor quotes with realistic pricing |
| RFQ_Tech_Evaluations | 14 | Tech scores per submission |
| RFQ_Comm_Evaluations | 14 | Price/payment/delivery scores |
| RFQ_Overall_Evaluations | 14 | Weighted final scores |
| NFA_Log | 3 | 2 approved, 1 under approval |
| SAP_PO_Data | 1 | PO 4500098710 — bearing cluster, already created |
| Process_Events_Log | 85 | Full audit trail for all 16 clusters |

### DOP Hierarchy

```
Supply Track:
  L1: ≤ INR 25 Lakhs     → Head of Department (HOD-MRO)
  L2: 25L – 2.5 Crore    → General Manager - Procurement
  L3: 2.5Cr – 25 Crore   → VP - Supply Chain Management
  L4: > 25 Crore         → CFO

Capital Track:
  L1: ≤ INR 50 Lakhs     → Head of Department (HOD-Capital)
  L2: 50L – 5 Crore      → General Manager - Procurement
  L3: 5Cr – 50 Crore     → VP - Supply Chain Management
  L4: > 50 Crore         → CFO
```

### 18 Compliance Controls

| Control | Description |
|---------|-------------|
| CTRL-001 | Minimum 3 vendors in RFQ (SVJ for exceptions) |
| CTRL-003 | NFA price must be justified if above LPP |
| CTRL-006 | PR value within approved budget |
| CTRL-007 | Blacklisted vendors excluded automatically |
| CTRL-008 | Vendor must be onboarded and approved before shortlisting |
| CTRL-017 | Repeat/emergency purchase flag within 30 days |

---

## 5. Folder Structure

```
Sourcesense_S2C_Platform/
│
├── README.md                        ← Start here on a new machine
├── CONVERSATION_SUMMARY.md          ← This file
│
├── core/                            ← Shared infrastructure
│   ├── state.py                     ← S2CState TypedDict (passed between all agents)
│   ├── config.py                    ← Env vars loader (GEMINI_API_KEY, DB_PATH, etc.)
│   ├── db.py                        ← get_db() context manager
│   ├── run.py                       ← Entry point: python run.py --phase all
│   ├── requirements.txt             ← pip install -r requirements.txt
│   └── .env.example                 ← Template for your .env file
│
├── agents/                          ← 21 agent files (PR.01 through PO.19)
│   ├── pr_01_consolidation.py
│   ├── pr_02_spec_extraction.py
│   ├── pr_03_buyer_assignment.py
│   ├── rfq_04_vendor_shortlisting.py   ← PATCHED: MSME_Status→MSME_Category, PO_Number→Total_POs_12M
│   ├── rfq_05_rfq_creation.py
│   ├── rfq_06_compliance_attach.py
│   ├── rfq_07_rfq_approval.py
│   ├── rfq_08_rfq_dispatch.py
│   ├── rfq_09_offer_collection.py
│   ├── eval_08_tech_evaluation.py
│   ├── eval_09_comm_evaluation.py
│   ├── eval_10_overall_ranking.py
│   ├── neg_11_negotiation_copilot.py
│   ├── neg_12_negotiation_approval.py
│   ├── nfa_13_nfa_generation.py
│   ├── nfa_14_nfa_approval.py
│   ├── po_15_po_reference_creation.py
│   ├── po_16_sap_bapi_call.py
│   ├── po_17_po_document_attach.py
│   ├── po_18_vendor_dispatch.py
│   └── po_19_status_update.py
│
├── graphs/                          ← LangGraph wiring
│   ├── phase1_graph.py              ← PR.01 → PR.02 → PR.03
│   ├── phase2_graph.py              ← RFQ.04 → ... → EVAL.10
│   ├── phase3_graph.py              ← NEG.11 → NEG.12 → NFA.13 → NFA.14
│   ├── phase4_graph.py              ← PO.15 → ... → PO.19
│   └── master_graph.py              ← Wires all 4 phases as subgraph nodes
│
├── database/
│   ├── s2c_sourcesense.db           ← 688 rows, 33 tables, FK-verified
│   └── setup/                       ← Scripts that built the DB (for reference/rebuild)
│       ├── build_s2c_database.py    ← Creates all 33 tables + base data
│       ├── expand_part1_materials.py← 232 materials × 26 groups
│       ├── expand_part2_masters.py  ← Vendors, buyers, DOP, designations
│       ├── expand_part3_pipeline.py ← 16 clusters at 8 pipeline stages
│       └── expand_part4_transactions.py ← RFQ/eval/NFA/PO transactional data
│
├── docs/
│   ├── BUILD_GUIDE_v2.md            ← Agent map, n8n vs LangGraph, DB stats
│   ├── FIRST_RUN_GUIDE.md           ← Step-by-step: .env → install → first run
│   ├── Phase1_PR_Agents_PR01_PR03.md← Gemini prompt to regenerate Phase 1 agents
│   ├── Phase2_RFQ_Eval_Agents_RFQ04_EVAL10.md
│   ├── Phase3_Negotiation_NFA_Agents_NEG11_NFA14.md
│   ├── Phase4_PO_Agents_PO15_PO19.md
│   ├── S2C_Agent_Flow_Map.md        ← Visual flow of all 19 agents
│   ├── S2C_ER_Diagram.html          ← Interactive ER diagram (open in browser)
│   └── S2C_ER_Simplified.png        ← Static ER diagram image
│
├── tests/
│   └── test_preflight.py            ← Run before first agent run — checks DB + schema
│
└── DMS_Documents/                   ← Document storage (populated by agents at runtime)
    ├── RFQ/
    ├── NFA/
    ├── PO/
    ├── Specs/
    ├── SVJ/
    ├── Onboarding/
    └── Compliance/
```

---

## 6. How to Run (Quick Reference)

### Prerequisites
1. Python 3.10+
2. `pip install -r core/requirements.txt`
3. Create `core/.env` with your `GEMINI_API_KEY`

### .env file (create manually)
```
GEMINI_API_KEY=AIza...your-key-here
DB_PATH=../database/s2c_sourcesense.db
DMS_ROOT=../DMS_Documents

# Optional — LangSmith visual tracing (free at smith.langchain.com)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=sourcesense-s2c

# Optional — only needed for email dispatch (RFQ.08, PO.18)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Run sequence
```bash
# 1. Preflight check (no API key needed)
python tests/test_preflight.py

# 2. Phase 1 only (safest first test — uses 10 open PRs)
python graphs/phase1_graph.py

# 3. Individual phases
python graphs/phase2_graph.py   # processes Buyer_Assigned clusters
python graphs/phase3_graph.py   # processes RFQ_Evaluation clusters
python graphs/phase4_graph.py   # processes NFA_Approved clusters

# 4. Full pipeline
python run.py --phase all
```

### Best clusters to test first (already in DB)

| Cluster | Stage | Best Test For |
|---------|-------|--------------|
| CL-2025-00862-01 | NFA_Approved | Run PO.15 → PO.19 end-to-end |
| CL-2025-00848-01 | RFQ_Evaluation | Run NEG.11 → NFA.14 → PO chain |
| CL-2025-00851-01 | Buyer_Assigned | Run full Phase 2 from scratch |
| (any open PR) | Open | Run full pipeline from PR.01 |

---

## 7. Key Bugs Found and Fixed

### Bug 1 — rfq_04_vendor_shortlisting.py: Wrong column name
- **What:** `vm.MSME_Status` referenced in SQL but actual column is `vm.MSME_Category`
- **Impact:** Agent would crash at runtime with `OperationalError: no such column: MSME_Status`
- **Fix:** Changed to `vm.MSME_Category` in the SELECT clause

### Bug 2 — rfq_04_vendor_shortlisting.py: Wrong subquery column
- **What:** Vendor_History subquery used `COUNT(PO_Number)` but `PO_Number` doesn't exist — table has `Total_POs_12M` directly
- **Impact:** Agent would crash with `OperationalError: no such column: PO_Number`
- **Fix:** Changed to `SUM(Total_POs_12M)` which aggregates the pre-computed value

### Bug 3 — rfq_04_vendor_shortlisting.py: Vendor_Shortlist missing columns
- **What:** INSERT only specified 4 of 6 columns; also incorrectly used `cluster_id` as `RFQ_ID`
- **Impact:** Semantic error — shortlist records would reference wrong ID; `Historical_Score` always NULL
- **Fix:** Added `Historical_Score` from the scoring calculation; set `RFQ_ID = NULL` at shortlisting stage (gets backfilled by RFQ.05 when the actual RFQ is generated)

### Known Warning (non-blocking)
- `google.generativeai` package is deprecated — all 19 agents import it. It works today but Google has ended support. Migration path: `from google import genai; client = genai.Client(api_key=...)`

---

## 8. Lessons Learned

### On database design
- **Always build in `/tmp` or a local path first, then copy to network/mount** — SQLite throws `disk I/O error` if the WAL journal can't be created on certain mounted filesystems. The fix: `shutil.copy2(local_build_path, mounted_path)` after build.
- **Pre-populate data in 4 separate passes** (tables → master data → pipeline clusters → transactional detail) rather than one monolithic script. Each pass is independently re-runnable.
- Synthetic test data should cover **every pipeline stage** so any single agent can be tested in isolation without needing to run the full chain first.

### On LangGraph design
- **TypedDict state is the contract** between agents — if an agent needs data from a previous step, it must be in `S2CState`. Add fields before you need them.
- **Conditional edges** (`add_conditional_edges`) are how you handle "nothing to process" cleanly — return `END` immediately rather than having agents error on empty results.
- **Phase-by-phase subgraph composition** (each phase compiled, then added as a node to the master graph) makes individual phase testing trivial.

### On Gemini API usage
- Always strip code fences from Gemini JSON responses: `.replace('```json', '').replace('```', '')`
- Catch `json.JSONDecodeError` separately from general exceptions — a bad JSON response shouldn't set `should_stop = True` without logging the raw response for debugging
- `gemini-2.5-pro` is the right model for structured JSON output tasks; use it consistently across all agents

### On agent architecture
- `get_db()` as a context manager (in `db.py`) is the right pattern — it handles commit/rollback/close automatically and prevents connection leaks
- **Every agent should write to `Process_Events_Log`** — this creates a full audit trail that doubles as debugging output
- **Every compliance check should write to `Compliance_Log`** — even `Pass` results, not just failures

### On n8n vs Python
- n8n is useful as a **visual design tool** but is the wrong execution environment for LLM-driven pipelines:
  - Can't run Python natively
  - Requires a running server
  - LangSmith free tier gives you equally good visual tracing with zero infrastructure
  - The LangGraph Mermaid export (`app.get_graph().draw_mermaid()`) gives a static diagram of the full graph

---

## 9. Pending Work / Next Steps

### Immediate (before first live run)
- [ ] Create `.env` file with your actual `GEMINI_API_KEY`
- [ ] Run `python tests/test_preflight.py` to confirm everything is green
- [ ] Run `python graphs/phase1_graph.py` as first live test
- [ ] Review LangSmith traces at smith.langchain.com

### Short-term (after first successful run)
- [ ] Read and test remaining agent files (eval through PO) for similar schema bugs
- [ ] Fix `google.generativeai` deprecation — migrate all 19 agents to `google.genai`
- [ ] Add Onboarding_Tracker GSTIN coverage — currently only 8 of 45 vendors are mapped; CTRL-008 will reject unmapped vendors
- [ ] Populate `Monthly_Performance` with more recent data (currently dates may be stale for the 3-month window query in RFQ.04)

### Medium-term
- [ ] Add email integration for RFQ.08 and PO.18 (SMTP config in .env)
- [ ] Build a simple CLI dashboard to view pipeline status without opening DB
- [ ] Add retry logic for Gemini API timeouts
- [ ] Write unit tests for the scoring algorithms in EVAL.08/09/10

### Architecture evolution
- [ ] Move from SQLite to PostgreSQL when moving to cloud (only `db.py` changes)
- [ ] Set up GitHub repo for version control before cloud deployment
- [ ] Consider GitHub Codespaces for iPad-based development (full Python environment in browser)
- [ ] LangSmith project dashboard already configured — review after first runs

---

## 10. Technology Stack Summary

| Component | Technology | Version/Notes |
|-----------|-----------|--------------|
| AI Brain | Gemini 2.5 Pro | via google-generativeai (deprecated — migrate to google.genai) |
| Agent Framework | LangGraph | StateGraph with TypedDict state |
| Visual Tracing | LangSmith | Free tier — project: sourcesense-s2c |
| Database | SQLite | s2c_sourcesense.db — replace with Postgres for production |
| Language | Python | 3.10+ |
| Email | smtplib / schedule | For RFQ dispatch and PO notification |
| Graph diagram | Mermaid | `app.get_graph().draw_mermaid()` |
| Environment | python-dotenv | .env file at project root |

---

## 11. People / Personas in the System

| Role | Email | Responsibility |
|------|-------|---------------|
| Ramesh Kumar (Senior Buyer) | ramesh.kumar@jswsteel.in | MRO-BRG, MRO-ELE, MRO-HYD |
| Priya Sharma (Buyer) | priya.sharma@jswsteel.in | MRO-ELE, MRO-FLT, MRO-INS |
| Anil Deshmukh (Senior Buyer) | anil.deshmukh@jswsteel.in | Capital goods |
| Sneha Patil (Junior Buyer) | sneha.patil@jswsteel.in | MRO-LUB, MRO-WLD, MRO-ELC |
| Karthik Rajan (Senior Buyer) | karthik.rajan@jswsteel.in | MRO-RFT, MRO-CHM, MRO-PLT |
| Sanjay Verma (Senior Buyer) | sanjay.verma@jswsteel.in | MRO-PMP, MRO-VLV, MRO-HYD |
| Vikram Singh (HOD-MRO) | vikram.singh@jswsteel.in | L1 approver — Supply ≤25L |
| Rajesh Iyer (GM-Procurement) | rajesh.iyer@jswsteel.in | L2 approver — 25L–2.5Cr |
| Sunil Kapoor (VP-SCM) | sunil.kapoor@jswsteel.in | L3 approver — 2.5Cr–25Cr |
| Meena Reddy (CFO) | meena.reddy@jswsteel.in | L4 approver — >25Cr |

---

## 12. Cloud / iPad Continuation Guide

When continuing this project from an iPad or new machine:

**Option A — GitHub + Codespaces (recommended)**
1. Create a private GitHub repo
2. Upload this entire `Sourcesense_S2C_Platform/` folder
3. Open GitHub Codespaces in Safari on iPad
4. You get a full Linux environment with Python — run agents directly
5. Use claude.ai alongside for code generation and debugging

**Option B — OneDrive + Replit**
1. Upload to OneDrive for file backup
2. Import project to Replit for execution
3. Use claude.ai in browser for agent development

**Key thing to remember:** The database `s2c_sourcesense.db` is your entire application state. Back it up before every test run so you can reset to a known state.

```bash
# Backup before testing
cp database/s2c_sourcesense.db database/s2c_sourcesense_backup_$(date +%Y%m%d).db
```

---

*Document generated: March 2026*
*Platform: Sourcesense S2C Procurement Intelligence*
*Built with: Claude (Anthropic) + Gemini 2.5 Pro (Google) + LangGraph*
