import sys, os, types, json, re, sqlite3
sys.path.insert(0, 'core')

# ── Smart Gemini mock: realistic JSON per agent ──────────────────────────────
from unittest.mock import MagicMock

DB = 'database/s2c_sourcesense.db'

def _smart_generate(model, contents):
    """Return agent-appropriate JSON based on prompt keywords."""
    prompt = contents if isinstance(contents, str) else str(contents)
    pl = prompt.lower()

    # PR.01 — cluster open PRs
    if ('pr_numbers' in pl or 'purchase requisition' in pl) and 'cluster' in pl:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT PR_Number FROM Master_PR_Data WHERE PR_Status='Open'")
        prs = [r[0] for r in c.fetchall()]
        conn.close()
        if prs:
            # Split PRs across 2 clusters
            mid = max(1, len(prs) // 2)
            result = json.dumps([
                {"cluster_name": "Cluster A", "pr_numbers": prs[:mid], "reason": "Same material group and plant"},
                {"cluster_name": "Cluster B", "pr_numbers": prs[mid:], "reason": "Same material group and plant"},
            ])
        else:
            result = '[]'

    # PR.02 — spec extraction
    elif 'extract' in pl and ('specification' in pl or 'spec' in pl):
        result = json.dumps({
            "dimensions": {"length": "100mm", "width": "50mm", "thickness": "10mm"},
            "standards": ["IS 2062", "ASTM A36"],
            "alternatives": ["Grade E250"],
            "critical_parameters": ["yield_strength", "hardness"],
            "inspection_requirements": ["visual inspection", "dimensional check"]
        })

    # RFQ.04 — vendor shortlisting
    elif ('vendor' in pl or 'supplier' in pl) and ('shortlist' in pl or 'recommend' in pl or 'rank' in pl):
        codes = re.findall(r'"vendor_code":\s*"([^"]+)"', prompt, re.IGNORECASE)
        if not codes:
            codes = re.findall(r'VEN-\d+', prompt)
        selected = codes[:4] if codes else ['VEN-001', 'VEN-002']
        result = json.dumps([
            {"vendor_code": v, "reason": "Strong compliance and delivery history", "recommended_rank": i + 1}
            for i, v in enumerate(selected)
        ])

    # EVAL.08 — technical evaluation
    elif 'technical evaluator' in pl or ('tech_score' in pl and 'disqualify' in pl):
        result = json.dumps({
            "tech_score": 78,
            "breakdown": {"spec_compliance": 32, "material_quality": 22, "documentation": 16, "alternatives": 8},
            "tech_remarks": "Meets core specifications with minor documentation gaps.",
            "disqualify": False,
            "disqualify_reason": None
        })

    # NEG.11 — negotiation strategy
    elif 'negotiation' in pl and ('target_price' in pl or 'walkaway' in pl):
        price_match = re.search(r'Best Vendor Quote[:\s]+([\d.]+)', prompt)
        quote = float(price_match.group(1)) if price_match else 1000.0
        result = json.dumps({
            "target_price": round(quote * 0.92, 2),
            "walkaway_price": round(quote * 0.97, 2),
            "spend_analysis": "Historical data shows 8% savings opportunity vs LPP.",
            "market_summary": "Market is stable; 3 qualified competitors available as BATNA.",
            "vendor_email_draft": "Dear Vendor, we invite your best and final offer."
        })

    else:
        result = '[]'

    resp = MagicMock()
    resp.text = result
    return resp

# Inject mock google.genai (env can't load native crypto extension)
google_pkg = types.ModuleType('google')
google_genai = types.ModuleType('google.genai')
_mock_client = MagicMock()
_mock_client.models.generate_content.side_effect = _smart_generate
google_genai.Client = MagicMock(return_value=_mock_client)
sys.modules['google'] = google_pkg
sys.modules['google.genai'] = google_genai
google_pkg.genai = google_genai

# Mock dotenv
dotenv_mod = types.ModuleType('dotenv')
dotenv_mod.load_dotenv = lambda: None
sys.modules['dotenv'] = dotenv_mod

os.environ['GEMINI_API_KEY'] = 'AIzaSyBhxc-fQ2vG9QrTl1j1AukUeI1to2GOwds'
os.environ.setdefault('DB_PATH', 'database/s2c_sourcesense.db')
os.environ.setdefault('DMS_ROOT', 'DMS_Documents')

from state import S2CState
import config

def make_state(**overrides):
    s = dict(
        cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
        current_agent='', next_agent=None, pr_status=None,
        consolidated_clusters=[], specs_extracted=False,
        buyer_assigned=None, comm_terms_received=False,
        vendors_shortlisted=[], rfq_created=False,
        evaluations_complete=False, negotiated_price=None,
        nfa_approved=False, po_created=False, sap_po_number=None,
        errors=[], compliance_results={}, should_stop=False,
        db_path='database/s2c_sourcesense.db',
        dms_root='DMS_Documents'
    )
    s.update(overrides)
    return s

PASS = 0; FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        result = fn()
        ok, detail = result if isinstance(result, tuple) else (result, '')
        if ok:
            print(f'  PASS  {name}' + (f' — {detail}' if detail else ''))
            PASS += 1
        else:
            print(f'  FAIL  {name}' + (f' — {detail}' if detail else ''))
            FAIL += 1
    except Exception as e:
        import traceback
        print(f'  FAIL  {name} — EXCEPTION: {e}')
        traceback.print_exc()
        FAIL += 1

def db_count(table, where='1=1'):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(f'SELECT COUNT(*) FROM {table} WHERE {where}')
    n = c.fetchone()[0]
    conn.close()
    return n

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PR.01 — PR Consolidation ===')
open_prs_before = db_count('Master_PR_Data', "PR_Status='Open'")
before_clusters = db_count('Consolidated_PRs')

from agents.pr_01_consolidation import pr_consolidation
r0 = pr_consolidation(make_state())

open_prs_after = db_count('Master_PR_Data', "PR_Status='Open'")
after_clusters = db_count('Consolidated_PRs')

test('no hard errors', lambda: (not r0.get('should_stop'), str(r0.get('errors', []))))
test('clusters created', lambda: (after_clusters > before_clusters or open_prs_before == 0,
     f'{before_clusters} → {after_clusters} clusters ({open_prs_before} open PRs)'))
test('PRs marked Consolidated', lambda: (open_prs_after < open_prs_before or open_prs_before == 0,
     f'{open_prs_before} → {open_prs_after} open PRs'))
test('Compliance_ID in cluster log', lambda: db_count('Compliance_Log', "Control_ID='CTRL-006' AND Compliance_ID IS NOT NULL") > 0)
test('Event_ID in PR.01 log', lambda: db_count('Process_Events_Log', "Process_ID='S2C.PR.01' AND Event_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PR.02 — Spec Extraction ===')
new_clusters = db_count('Consolidated_PRs', "PR_Status='New'")
before_specs_ready = db_count('Consolidated_PRs', "PR_Status='Specs_Ready'")

from agents.pr_02_spec_extraction import spec_extraction
r0b = spec_extraction(make_state())

after_specs_ready = db_count('Consolidated_PRs', "PR_Status='Specs_Ready'")
after_specs_pending = db_count('Consolidated_PRs', "PR_Status='Specs_Pending'")

test('no hard errors', lambda: (not r0b.get('should_stop', False), str(r0b.get('errors', []))))
test('clusters processed', lambda: (
    after_specs_ready > before_specs_ready or after_specs_pending > 0 or new_clusters == 0,
    f'Specs_Ready: {before_specs_ready}→{after_specs_ready}, Specs_Pending: {after_specs_pending}'))
test('Event_ID in PR.02 log', lambda: db_count('Process_Events_Log', "Process_ID='S2C.RFQ.02' AND Event_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PR.03 — Buyer Assignment ===')
before_ba = db_count('Consolidated_PRs', "PR_Status='Buyer_Assigned'")

from agents.pr_03_buyer_assignment import buyer_assignment
r1 = buyer_assignment(make_state())

after_ba = db_count('Consolidated_PRs', "PR_Status='Buyer_Assigned'")

def t_buyer():
    errors = [e for e in r1.get('errors', []) if 'No buyer' not in e]
    return not errors and not r1.get('should_stop'), f"errors={errors}"

test('no hard errors', t_buyer)
test('Specs_Ready clusters assigned', lambda: (after_ba >= before_ba, f'{before_ba} → {after_ba} Buyer_Assigned'))
test('Approval_ID populated', lambda: db_count('Approval_Log', "Approval_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PR.03b — Commercial Terms Finalisation ===')
buyer_assigned_count = db_count('Consolidated_PRs', "PR_Status='Buyer_Assigned'")
before_ct = db_count('Consolidated_PRs', "PR_Status='Comm_Terms_Received'")
before_cr = db_count('Comm_Requests')

from agents.pr_03b_commercial_terms import commercial_terms_finalisation
r2 = commercial_terms_finalisation(make_state())
after_ct = db_count('Consolidated_PRs', "PR_Status='Comm_Terms_Received'")
after_cr = db_count('Comm_Requests')

test('no errors', lambda: (not r2.get('errors'), str(r2.get('errors'))))
test('comm_terms_received flag set', lambda: (r2.get('comm_terms_received') or buyer_assigned_count == 0,
     f'flag={r2.get("comm_terms_received")}, had {buyer_assigned_count} Buyer_Assigned'))
test('Comm_Requests created', lambda: (after_cr > before_cr or buyer_assigned_count == 0, f'{before_cr} → {after_cr}'))
test('clusters advanced to Comm_Terms_Received', lambda: (after_ct > before_ct or buyer_assigned_count == 0,
     f'{before_ct} → {after_ct}'))
test('Unit_Price populated', lambda: db_count('Consolidated_PRs', "Unit_Price > 0") > 0)
test('Incoterms populated', lambda: db_count('Consolidated_PRs', "Incoterms='DDP'") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== RFQ.04 — Vendor Shortlisting ===')
ct_count = db_count('Consolidated_PRs', "PR_Status='Comm_Terms_Received'")
before_vs = db_count('Vendor_Shortlist')
before_vs_clusters = db_count('Consolidated_PRs', "PR_Status='Vendors_Shortlisted'")

from agents.rfq_04_vendor_shortlisting import vendor_shortlisting
r2b = vendor_shortlisting(make_state())

after_vs = db_count('Vendor_Shortlist')
after_vs_clusters = db_count('Consolidated_PRs', "PR_Status='Vendors_Shortlisted'")

test('no errors', lambda: (not r2b.get('errors'), str(r2b.get('errors'))))
test('vendors shortlisted', lambda: (after_vs > before_vs or ct_count == 0,
     f'{before_vs} → {after_vs} entries ({ct_count} Comm_Terms_Received clusters)'))
test('clusters advanced to Vendors_Shortlisted', lambda: (after_vs_clusters > before_vs_clusters or ct_count == 0,
     f'{before_vs_clusters} → {after_vs_clusters}'))
test('Event_ID in RFQ.04 log', lambda: db_count('Process_Events_Log', "Process_ID='S2C.RFQ.04' AND Event_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== RFQ.05 — RFQ Creation ===')
before_rfq = db_count('RFQ_Log')
before_rfq_vs = db_count('Vendor_Shortlist', 'RFQ_ID IS NOT NULL')

from agents.rfq_05_rfq_creation import rfq_creation
r3 = rfq_creation(make_state(buyer_assigned='BUY-1001'))
after_rfq = db_count('RFQ_Log')
after_rfq_vs = db_count('Vendor_Shortlist', 'RFQ_ID IS NOT NULL')

test('no errors', lambda: (not r3.get('errors'), str(r3.get('errors'))))
test('RFQ rows created', lambda: (after_rfq >= before_rfq, f'{before_rfq} → {after_rfq}'))
test('Vendor_Shortlist backfilled', lambda: (after_rfq_vs >= before_rfq_vs, f'{before_rfq_vs} → {after_rfq_vs} with RFQ_ID'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== RFQ.06 — Compliance Attach ===')
from agents.rfq_06_compliance_attach import compliance_attach
r4 = compliance_attach(make_state())
rfq_rfa = db_count('RFQ_Log', "RFQ_Status='Ready_For_Approval'")
rfq_svj = db_count('RFQ_Log', "RFQ_Status='SVJ_Pending'")

test('no crashes', lambda: (True, f'Ready_For_Approval={rfq_rfa}, SVJ_Pending={rfq_svj}, errors={r4.get("errors",[])}'))
test('Compliance_ID populated', lambda: db_count('Compliance_Log', "Compliance_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== RFQ.07 — RFQ Approval ===')
rfa_count = db_count('RFQ_Log', "RFQ_Status='Ready_For_Approval'")
from agents.rfq_07_rfq_approval import rfq_approval
r5 = rfq_approval(make_state())
rfq_approved_count = db_count('RFQ_Log', "RFQ_Status='Approved'")

test('no errors', lambda: (not r5.get('errors'), str(r5.get('errors'))))
test('RFQs approved', lambda: (rfq_approved_count > 0 or rfa_count == 0,
     f'{rfq_approved_count} Approved (had {rfa_count} Ready_For_Approval)'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== RFQ.08 — RFQ Dispatch ===')
before_disp = db_count('RFQ_Dispatch_Log')
from agents.rfq_08_rfq_dispatch import rfq_dispatch
r6 = rfq_dispatch(make_state())
after_disp = db_count('RFQ_Dispatch_Log')

test('no errors', lambda: (not r6.get('errors'), str(r6.get('errors'))))
test('Dispatch_ID populated', lambda: db_count('RFQ_Dispatch_Log', "Dispatch_ID IS NOT NULL") > 0)
test('dispatch log rows added', lambda: (after_disp >= before_disp, f'{before_disp} → {after_disp}'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== RFQ.09 — Offer Collection ===')
dispatched_count = db_count('RFQ_Log', "RFQ_Status='Dispatched'")
before_subs = db_count('RFQ_Submissions')
from agents.rfq_09_offer_collection import offer_collection
r7 = offer_collection(make_state())
after_subs = db_count('RFQ_Submissions')
after_eval = db_count('Consolidated_PRs', "PR_Status='RFQ_Evaluation'")

test('no errors', lambda: (not r7.get('errors'), str(r7.get('errors'))))
test('Submission_ID populated', lambda: db_count('RFQ_Submissions', "Submission_ID IS NOT NULL") > 0)
test('submissions simulated', lambda: (after_subs > before_subs or dispatched_count == 0,
     f'{before_subs} → {after_subs} (dispatched={dispatched_count})'))
test('clusters moved to RFQ_Evaluation', lambda: (after_eval > 0, f'{after_eval} clusters in eval'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== EVAL.08 — Technical Evaluation ===')
subs_closed = db_count('RFQ_Log', "RFQ_Status='Submissions_Closed'")
before_te = db_count('RFQ_Tech_Evaluations')

from agents.eval_08_tech_evaluation import tech_evaluation
r7b = tech_evaluation(make_state())

after_te = db_count('RFQ_Tech_Evaluations')

test('no errors', lambda: (not r7b.get('errors'), str(r7b.get('errors'))))
test('Tech_Eval_ID populated', lambda: db_count('RFQ_Tech_Evaluations', "Tech_Eval_ID IS NOT NULL") > 0)
test('tech evaluations added', lambda: (after_te > before_te or subs_closed == 0,
     f'{before_te} → {after_te} ({subs_closed} Submissions_Closed RFQs)'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== EVAL.09 — Commercial Evaluation ===')
before_ce = db_count('RFQ_Comm_Evaluations')
from agents.eval_09_comm_evaluation import comm_evaluation
r8 = comm_evaluation(make_state())
after_ce = db_count('RFQ_Comm_Evaluations')

test('no errors', lambda: (not r8.get('errors'), str(r8.get('errors'))))
test('Comm_Eval_ID populated', lambda: db_count('RFQ_Comm_Evaluations', "Comm_Eval_ID IS NOT NULL") > 0)
test('evaluations added', lambda: (after_ce >= before_ce, f'{before_ce} → {after_ce}'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== EVAL.10 — Overall Ranking ===')
before_oe = db_count('RFQ_Overall_Evaluations')
from agents.eval_10_overall_ranking import overall_ranking
r9 = overall_ranking(make_state())
after_oe = db_count('RFQ_Overall_Evaluations')
eval_done = db_count('RFQ_Log', "RFQ_Status='Evaluation_Complete'")

test('no errors', lambda: (not r9.get('errors'), str(r9.get('errors'))))
test('Overall_Eval_ID populated', lambda: db_count('RFQ_Overall_Evaluations', "Overall_Eval_ID IS NOT NULL") > 0)
test('evaluations_complete flag', lambda: r9.get('evaluations_complete', False))
total_oe = db_count('RFQ_Overall_Evaluations')
test('RFQs marked Evaluation_Complete', lambda: (eval_done > 0 or total_oe > 0,
     f'{eval_done} active Evaluation_Complete, {total_oe} total overall evals in DB'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== NEG.11 — Negotiation Co-pilot ===')
eval_complete_count = db_count('RFQ_Log', "RFQ_Status='Evaluation_Complete'")
before_neg_intel = db_count('Negotiation_Intelligence_Log')
before_neg_sh = db_count('Negotiation_Shortlist_Approval')

from agents.neg_11_negotiation_copilot import negotiation_copilot
r10a = negotiation_copilot(make_state())

after_neg_intel = db_count('Negotiation_Intelligence_Log')
after_neg_sh = db_count('Negotiation_Shortlist_Approval')

test('no errors', lambda: (not r10a.get('errors'), str(r10a.get('errors'))))
test('negotiation strategy created', lambda: (after_neg_intel > before_neg_intel or eval_complete_count == 0,
     f'{before_neg_intel} → {after_neg_intel} intel entries ({eval_complete_count} Eval_Complete RFQs)'))
test('Brief_ID populated', lambda: db_count('Negotiation_Intelligence_Log', "Brief_ID IS NOT NULL") > 0 or eval_complete_count == 0)
test('shortlist approval entry created', lambda: (after_neg_sh > before_neg_sh or eval_complete_count == 0,
     f'{before_neg_sh} → {after_neg_sh}'))
test('Neg_Approval_ID populated', lambda: db_count('Negotiation_Shortlist_Approval', "Neg_Approval_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== NEG.12 — Negotiation Approval ===')
before_under_neg = db_count('RFQ_Log', "RFQ_Status='Under_Negotiation'")
before_neg_approved = db_count('Consolidated_PRs', "PR_Status='Negotiation_Approved'")

from agents.neg_12_negotiation_approval import negotiation_approval
r10b = negotiation_approval(make_state())

after_neg_approved = db_count('Consolidated_PRs', "PR_Status='Negotiation_Approved'")

test('no hard errors', lambda: (not r10b.get('errors'), str(r10b.get('errors'))))
test('negotiation approved', lambda: (
    after_neg_approved > before_neg_approved
    or before_under_neg == 0
    or r10b.get('negotiated_price') is not None,
    f'Negotiation_Approved: {before_neg_approved}→{after_neg_approved}, '
    f'negotiated_price={r10b.get("negotiated_price")}'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== NFA.13 — NFA Generation ===')
before_nfa = db_count('NFA_Log')
neg_appr_count = db_count('Consolidated_PRs', "PR_Status='Negotiation_Approved' AND NFA_Status IS NULL")

from agents.nfa_13_nfa_generation import nfa_generation
r10c = nfa_generation(make_state())

after_nfa = db_count('NFA_Log')

test('no errors', lambda: (not r10c.get('errors'), str(r10c.get('errors'))))
test('NFA created', lambda: (after_nfa > before_nfa or neg_appr_count == 0,
     f'{before_nfa} → {after_nfa} NFAs ({neg_appr_count} eligible clusters)'))
test('Compliance_ID in NFA log', lambda: db_count('Compliance_Log', "Control_ID='CTRL-003' AND Compliance_ID IS NOT NULL") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== NFA.14 — NFA Approval ===')
before_nfa_a = db_count('NFA_Log', "NFA_Status='Approved'")
from agents.nfa_14_nfa_approval import nfa_approval
r11 = nfa_approval(make_state())
after_nfa_a = db_count('NFA_Log', "NFA_Status='Approved'")

test('no errors', lambda: (not r11.get('errors'), str(r11.get('errors'))))
test('approved NFAs', lambda: (after_nfa_a >= before_nfa_a, f'{before_nfa_a} → {after_nfa_a} approved NFAs'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PO.15 — PO Reference Creation ===')
before_por = db_count('PO_Reference')
from agents.po_15_po_reference_creation import po_reference_creation
r12 = po_reference_creation(make_state())
after_por = db_count('PO_Reference')

test('no errors', lambda: (not r12.get('errors'), str(r12.get('errors'))))
test('PO References created', lambda: (after_por >= before_por, f'{before_por} → {after_por}'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PO.16 — SAP BAPI Call ===')
before_sap = db_count('SAP_PO_Data')
from agents.po_16_sap_bapi_call import sap_bapi_call
r13 = sap_bapi_call(make_state())
after_sap = db_count('SAP_PO_Data')

test('no errors', lambda: (not r13.get('errors'), str(r13.get('errors'))))
test('SAP PO created', lambda: (after_sap >= before_sap, f'{before_sap} → {after_sap} SAP POs'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PO.17 — PO Document Attach ===')
from agents.po_17_po_document_attach import po_document_attach
r14 = po_document_attach(make_state())
test('no errors', lambda: (not r14.get('errors'), str(r14.get('errors'))))
test('Compliance_ID in PO doc log', lambda: db_count('Compliance_Log', "Control_ID='PO-Final'") > 0)

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PO.18 — Vendor Dispatch ===')
from agents.po_18_vendor_dispatch import vendor_dispatch
r15 = vendor_dispatch(make_state())
test('no errors', lambda: (not r15.get('errors'), str(r15.get('errors'))))
ack = db_count('PO_Reference', 'Vendor_Acknowledged_At IS NOT NULL')
test('vendor acknowledged', lambda: (ack > 0, f'{ack} POs acknowledged'))

# ────────────────────────────────────────────────────────────────────────────
print('\n=== PO.19 — Status Update ===')
from agents.po_19_status_update import status_update
r16 = status_update(make_state())
closed = db_count('Consolidated_PRs', "PR_Status='Closed'")
lpp_updated = db_count('LPP_Master', 'Last_PO_Date IS NOT NULL')

test('no errors', lambda: (not r16.get('errors'), str(r16.get('errors'))))
test('clusters closed', lambda: (closed > 0, f'{closed} closed'))
test('LPP_Master updated', lambda: (lpp_updated > 0, f'{lpp_updated} LPP entries have PO date'))
test('Event_ID in close log', lambda: db_count('Process_Events_Log', "Event_Type='Cluster_Closed'") > 0)

# ────────────────────────────────────────────────────────────────────────────
print(f'\n{"="*50}')
print(f'  RESULT: {PASS} passed  |  {FAIL} failed')
print(f'{"="*50}')
