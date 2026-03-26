"""
test_preflight.py
Pre-flight check for the S2C platform.
Tests: DB schema vs agent SQL, column name mismatches, import chain, state keys.
Does NOT require a GEMINI_API_KEY.
"""

import sqlite3, re, os, sys, ast, importlib.util
from pathlib import Path

DB_PATH = '/sessions/vibrant-zealous-mccarthy/s2c_sourcesense.db'
AGENTS_DIR = '/sessions/vibrant-zealous-mccarthy/mnt/VertexAI--01. Sourcesense jsons/agents'
GRAPHS_DIR = '/sessions/vibrant-zealous-mccarthy/mnt/VertexAI--01. Sourcesense jsons/graphs'
PROJECT_ROOT = '/sessions/vibrant-zealous-mccarthy/mnt/VertexAI--01. Sourcesense jsons'

PASS = "✅"
WARN = "⚠️ "
FAIL = "❌"

results = {"pass": 0, "warn": 0, "fail": 0}

def check(label, ok, detail="", severity="fail"):
    icon = PASS if ok else (WARN if severity == "warn" else FAIL)
    key = "pass" if ok else severity
    results[key] += 1
    print(f"  {icon} {label}" + (f" — {detail}" if detail else ""))
    return ok

# ─────────────────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════")
print("  SOURCESENSE S2C — PRE-FLIGHT CHECK")
print("══════════════════════════════════════════════════════")

# ─── 1. DATABASE ─────────────────────────────────────────────────────────────
print("\n[1] DATABASE")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all table schemas
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = {r[0] for r in cur.fetchall()}
check("DB connected", True, f"{len(all_tables)} tables found")

required_tables = [
    'Material_Master','Vendor_Master','Buyer_Master','DOP','Designations_Master',
    'Consolidated_PRs','Master_PR_Data','RFQ_Log','Vendor_Shortlist','Supplier_Master',
    'Monthly_Performance','Vendor_History','RFQ_Dispatch_Log','RFQ_Submissions',
    'RFQ_Tech_Evaluations','RFQ_Comm_Evaluations','RFQ_Overall_Evaluations',
    'Negotiation_Intelligence_Log','Negotiation_Shortlist_Approval','NFA_Log',
    'NFA_Approval_Log','PO_Reference','SAP_PO_Data','DMS_Documents','Compliance_Log',
    'Approval_Log','SVJ_Log','Spec_Requests','Process_Events_Log',
    'Procurement_Historical_Pricing','Onboarding_Tracker','UOM_Conversion'
]
missing = [t for t in required_tables if t not in all_tables]
check("All required tables present", len(missing) == 0,
      f"Missing: {missing}" if missing else f"All {len(required_tables)} tables present")

# Get column names per table
table_cols = {}
for t in all_tables:
    cur.execute(f"PRAGMA table_info({t})")
    table_cols[t] = {r['name'] for r in cur.fetchall()}

# Row counts
print()
key_counts = {}
for t in ['Material_Master','Vendor_Master','Buyer_Master','Consolidated_PRs',
          'Master_PR_Data','RFQ_Log','NFA_Log','SAP_PO_Data','Process_Events_Log']:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    n = cur.fetchone()[0]
    key_counts[t] = n
    ok = n > 0
    check(f"  {t} has data", ok, f"{n} rows", severity="warn")

# ─── 2. SCHEMA COMPATIBILITY CHECKS ──────────────────────────────────────────
print("\n[2] SCHEMA COMPATIBILITY (agent SQL vs actual columns)")

schema_issues = []

def check_cols(table, cols_used, source):
    if table not in table_cols:
        schema_issues.append(f"{source}: table '{table}' not found")
        return False
    actual = table_cols[table]
    bad = [c for c in cols_used if c not in actual and c != '*']
    if bad:
        schema_issues.append(f"{source}: column(s) {bad} not in {table} (actual: {sorted(actual)})")
        return False
    return True

# --- PR.01 ---
check_cols('Master_PR_Data',
    ['PR_Number','Material_Code','Plant','Quantity','UOM','Delivery_Date','PR_Status'], 'pr_01')
check_cols('Material_Master',
    ['Material_Description','Material_Group','Base_UOM','Last_Purchase_Price'], 'pr_01')
check_cols('UOM_Conversion',
    ['Conversion_Factor','From_UOM','To_UOM_Base'], 'pr_01')
check_cols('Consolidated_PRs',
    ['Consolidation_Cluster_ID','PR_Number','Material_Code','Material_Group','Description',
     'Quantity','UOM_Base','Total_Value','Plant','PR_Status',
     'Repeat_Emergency_Flag','Budget_Overrun_Flag','Created_At'], 'pr_01')

# --- RFQ.04 ---
check_cols('Vendor_Master',
    ['Vendor_Code','GSTIN','Active_Status','Blacklisted','MSME_Category'], 'rfq_04')
# Critical: agent code says MSME_Status — check if it exists
msme_ok = 'MSME_Status' in table_cols.get('Vendor_Master', set())
msme_cat_ok = 'MSME_Category' in table_cols.get('Vendor_Master', set())
if not msme_ok and msme_cat_ok:
    schema_issues.append("rfq_04: agent uses 'vm.MSME_Status' but column is 'MSME_Category' in Vendor_Master")

check_cols('Supplier_Master', ['Overall_Score','Supplier_Code'], 'rfq_04')
check_cols('Monthly_Performance',
    ['Supplier_Code','Delivery_On_Time_Pct','Quality_Incidents','Month'], 'rfq_04')
check_cols('Vendor_History',
    ['Vendor_Code','Material_Code','Last_PO_Date','PO_Number'], 'rfq_04')
check_cols('Onboarding_Tracker', ['GST_Number','Finance_Decision'], 'rfq_04')
check_cols('Vendor_Shortlist', ['RFQ_ID','Vendor_Code','Shortlist_Reason','Added_At'], 'rfq_04')

# --- General inserts used by many agents ---
check_cols('Compliance_Log',
    ['Control_ID','Entity_Type','Entity_ID','Result','Details','Checked_At'], 'compliance_inserts')
check_cols('Process_Events_Log',
    ['Process_ID','Entity_Type','Entity_ID','Event_Type','Event_Description','Actor','Created_At'], 'process_log_inserts')
check_cols('DMS_Documents',
    ['Document_ID','Document_Type','Entity_Type','Entity_ID','File_Name','File_Path',
     'Uploaded_By','Uploaded_At','File_Size_KB','Version'], 'dms_inserts')

if schema_issues:
    for issue in schema_issues:
        check(f"Schema: {issue}", False, severity="fail")
else:
    check("All schema references verified", True)

# ─── 3. ONBOARDING_TRACKER ────────────────────────────────────────────────────
print("\n[3] ONBOARDING_TRACKER — CTRL-008 dependency")
cur.execute("PRAGMA table_info(Onboarding_Tracker)")
ot_cols = {r['name'] for r in cur.fetchall()}
check("Onboarding_Tracker has GST_Number col",
    'GST_Number' in ot_cols,
    f"Actual cols: {sorted(ot_cols)}", severity="warn")
check("Onboarding_Tracker has Finance_Decision col",
    'Finance_Decision' in ot_cols,
    f"Actual cols: {sorted(ot_cols)}", severity="warn")

cur.execute("SELECT COUNT(*) FROM Onboarding_Tracker WHERE Finance_Decision = 'Approved'")
n = cur.fetchone()[0]
check(f"Onboarding_Tracker has approved vendors", n > 0,
    f"{n} approved vendors (RFQ.04 CTRL-008 needs this)", severity="warn")

# Cross-check: do vendor GST numbers appear in Onboarding_Tracker?
cur.execute("SELECT GSTIN FROM Vendor_Master WHERE Active_Status='Active' AND Blacklisted=0 LIMIT 5")
sample_gstins = [r[0] for r in cur.fetchall()]
cur.execute("SELECT GST_Number FROM Onboarding_Tracker LIMIT 20")
ot_gstins = {r[0] for r in cur.fetchall()}
matched = [g for g in sample_gstins if g in ot_gstins]
check("Vendor GSTINs match Onboarding_Tracker",
    len(matched) > 0,
    f"{len(matched)}/{len(sample_gstins)} sample vendor GSTINs found in Onboarding_Tracker",
    severity="warn")

# ─── 4. SUPPLIER_MASTER ────────────────────────────────────────────────────────
print("\n[4] SUPPLIER_MASTER — join used in RFQ.04")
cur.execute("PRAGMA table_info(Supplier_Master)")
sm_cols = {r['name'] for r in cur.fetchall()}
check("Supplier_Master has Supplier_Code", 'Supplier_Code' in sm_cols, str(sorted(sm_cols)))
check("Supplier_Master has Overall_Score", 'Overall_Score' in sm_cols, str(sorted(sm_cols)))
cur.execute("""
    SELECT COUNT(*) FROM Vendor_Master vm
    JOIN Supplier_Master sm ON vm.Vendor_Code = sm.Supplier_Code
    WHERE vm.Active_Status='Active' AND vm.Blacklisted=0
""")
n = cur.fetchone()[0]
check(f"Vendor_Master ↔ Supplier_Master join produces rows", n > 0, f"{n} joinable vendors")

# ─── 5. OPEN PRs FOR PR.01 ────────────────────────────────────────────────────
print("\n[5] PIPELINE READINESS")
cur.execute("SELECT COUNT(*) FROM Master_PR_Data WHERE PR_Status='Open'")
open_prs = cur.fetchone()[0]
check(f"Open PRs available for PR.01", open_prs > 0, f"{open_prs} open PRs")

cur.execute("SELECT COUNT(*) FROM Consolidated_PRs WHERE PR_Status='Buyer_Assigned'")
ba = cur.fetchone()[0]
check(f"Buyer_Assigned clusters for RFQ.04", ba > 0, f"{ba} clusters")

cur.execute("SELECT COUNT(*) FROM Consolidated_PRs WHERE PR_Status='RFQ_Evaluation'")
ev = cur.fetchone()[0]
check(f"RFQ_Evaluation clusters for EVAL agents", ev > 0, f"{ev} clusters")

cur.execute("SELECT COUNT(*) FROM NFA_Log WHERE NFA_Status='Approved'")
nfa = cur.fetchone()[0]
check(f"NFA_Approved records for PO.15+", nfa > 0, f"{nfa} approved NFAs")

# ─── 6. PYTHON PACKAGE IMPORTS ────────────────────────────────────────────────
print("\n[6] PYTHON PACKAGES")
packages = {
    'langgraph': 'langgraph',
    'langchain': 'langchain',
    'google.generativeai': 'google.generativeai (DEPRECATED — works but should migrate to google.genai)',
    'dotenv': 'python-dotenv',
}
for mod, label in packages.items():
    try:
        import importlib
        m = importlib.import_module(mod)
        ver = getattr(m, '__version__', '?')
        check(f"import {mod}", True, f"v{ver} — {label}" if label != mod else f"v{ver}")
    except ImportError as e:
        check(f"import {mod}", False, str(e))

# ─── 7. KEY IDENTIFIED ISSUES SUMMARY ─────────────────────────────────────────
print("\n[7] ISSUES TO FIX BEFORE FIRST RUN")

issues_to_fix = []

# Check MSME column mismatch
if 'MSME_Status' not in table_cols.get('Vendor_Master', set()):
    issues_to_fix.append({
        "file": "agents/rfq_04_vendor_shortlisting.py",
        "line": "~line 54",
        "issue": "vm.MSME_Status → column does not exist",
        "fix": "Change to vm.MSME_Category"
    })

# Check Onboarding_Tracker GST column
ot_has_gstin = 'GSTIN' in ot_cols
ot_has_gst_number = 'GST_Number' in ot_cols
if not ot_has_gst_number and ot_has_gstin:
    issues_to_fix.append({
        "file": "agents/rfq_04_vendor_shortlisting.py",
        "line": "~line 77",
        "issue": "Onboarding_Tracker lookup uses 'GST_Number' but column is 'GSTIN'",
        "fix": "Change GST_Number → GSTIN in the Onboarding_Tracker SELECT"
    })

# Check Vendor_Shortlist RFQ_ID vs cluster_id
issues_to_fix.append({
    "file": "agents/rfq_04_vendor_shortlisting.py",
    "line": "~line 117",
    "issue": "Vendor_Shortlist INSERT passes cluster_id as RFQ_ID — semantically wrong (RFQ doesn't exist at this stage)",
    "fix": "Use NULL or a placeholder for RFQ_ID at shortlisting stage; RFQ_ID gets set in RFQ.05"
})

# google.generativeai deprecation
issues_to_fix.append({
    "file": "ALL agents (19 files)",
    "line": "top-level import",
    "issue": "google.generativeai is deprecated — 'All support has ended'",
    "fix": "Works NOW but will break eventually. Migrate to: from google import genai; client = genai.Client(api_key=...)"
})

if issues_to_fix:
    for i, issue in enumerate(issues_to_fix, 1):
        sev = FAIL if "column" in issue['issue'].lower() or "not exist" in issue['issue'].lower() else WARN
        print(f"\n  {sev} Issue #{i}")
        print(f"     File  : {issue['file']}")
        print(f"     Where : {issue['line']}")
        print(f"     Issue : {issue['issue']}")
        print(f"     Fix   : {issue['fix']}")
        if "column" in issue['issue'].lower() or "not exist" in issue['issue'].lower():
            results['fail'] += 1
        else:
            results['warn'] += 1
else:
    print(f"  {PASS} No critical issues found")

conn.close()

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════")
print(f"  RESULT: {results['pass']} passed  |  {results['warn']} warnings  |  {results['fail']} failures")
print("══════════════════════════════════════════════════════")
if results['fail'] > 0:
    print("  ⛔  Fix failures before running agents.")
elif results['warn'] > 0:
    print("  ⚠️   OK to run — review warnings before full pipeline.")
else:
    print("  ✅  All clear — ready to run.")
print()
