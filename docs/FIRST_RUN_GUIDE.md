# Sourcesense S2C — First Run Guide

## Status After Pre-flight Check
- ✅ DB: 688 rows, 33 tables, zero FK violations
- ✅ Schema fixes applied to rfq_04_vendor_shortlisting.py
- ✅ All Python packages installed
- ⚠️ google.generativeai is deprecated but works — plan to migrate later

---

## Step 1 — Create your .env file

In the project folder (`01. Sourcesense jsons/`), create a file called `.env`:

```
# Required
GEMINI_API_KEY=AIza...your-key-here

# Database (relative path — runs from project root)
DB_PATH=s2c_sourcesense.db
DMS_ROOT=DMS_Documents

# LangSmith tracing (optional but recommended — free tier)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...your-langsmith-key
LANGCHAIN_PROJECT=sourcesense-s2c

# Email (optional — only needed for RFQ.08 dispatch and PO.18)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
```

Get GEMINI_API_KEY: https://aistudio.google.com/app/apikey
Get LangSmith key: https://smith.langchain.com/ (free account)

---

## Step 2 — Install dependencies (one-time)

```bash
cd "C:\Users\lenovo\Desktop\AI stuff\VertexAI\01. Sourcesense jsons"
pip install -r requirements.txt
```

---

## Step 3 — Test Order (recommended sequence)

### START HERE — Phase 1 (PR Consolidation)
Tests the most independent agents. Processes 10 open PRs.

```bash
python graphs/phase1_graph.py
```

Expected:
- PR.01 calls Gemini to cluster 10 open PRs → creates new Consolidated_PRs rows
- PR.02 extracts specs via Gemini → updates Long_Text_Specifications
- PR.03 assigns buyer based on material group → sets Assigned_Buyer

Check result in DB:
```sql
SELECT Consolidation_Cluster_ID, Material_Group, PR_Status, Assigned_Buyer
FROM Consolidated_PRs WHERE PR_Status IN ('New','Specs_Ready','Buyer_Assigned')
ORDER BY Created_At DESC;
```

---

### Phase 2 — RFQ Chain (use existing Buyer_Assigned clusters)
3 clusters already at Buyer_Assigned stage: CL-2025-00851-01, CL-2025-00861-01, CL-2025-00867-01

```bash
python graphs/phase2_graph.py
```

Covers: RFQ.04 (vendor shortlist) → RFQ.05 (generate RFQ) → RFQ.06 (compliance) →
        RFQ.07 (approve) → RFQ.08 (dispatch email) → RFQ.09 (collect offers) →
        EVAL.08 (tech eval) → EVAL.09 (comm eval) → EVAL.10 (overall ranking)

---

### Phase 3 — Negotiation + NFA (use existing RFQ_Evaluation clusters)
2 clusters at RFQ_Evaluation: CL-2025-00848-01, CL-2025-00864-01
1 cluster Under_NFA_Approval: CL-2025-00863-01

```bash
python graphs/phase3_graph.py
```

---

### Phase 4 — PO Creation (use NFA_Approved clusters)
2 clusters at NFA_Approved: CL-2025-00847-01 (PO already exists), CL-2025-00862-01 (needs PO)

```bash
python graphs/phase4_graph.py
```

---

### Full Pipeline (all phases in sequence)
```bash
python run.py --phase all
```

---

## Step 4 — View traces in LangSmith

After adding LANGCHAIN_API_KEY to .env:
1. Go to https://smith.langchain.com/
2. Open project `sourcesense-s2c`
3. Each agent run appears as a traced node — click to see Gemini input/output

---

## Known Warnings (non-blocking)

| Warning | Impact | When to Fix |
|---------|--------|-------------|
| google.generativeai deprecated | Works now, may break in ~6-12 months | Before production deployment |
| Only 2/5 vendor GSTINs in Onboarding_Tracker | Some vendors fail CTRL-008 | Add more vendor GSTIN mappings to Onboarding_Tracker |

---

## Quick DB Check Commands

```python
import sqlite3
conn = sqlite3.connect('s2c_sourcesense.db')
cur = conn.cursor()

# Pipeline snapshot
cur.execute("SELECT PR_Status, COUNT(*) FROM Consolidated_PRs GROUP BY PR_Status")
print(cur.fetchall())

# Latest process events
cur.execute("SELECT Entity_ID, Event_Type, Actor, Created_At FROM Process_Events_Log ORDER BY Created_At DESC LIMIT 10")
print(cur.fetchall())
```
