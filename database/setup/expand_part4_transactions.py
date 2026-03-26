"""
expand_part4_transactions.py
Populates all transactional sub-tables for the 16 pipeline clusters.
Covers: RFQ_Log, Vendor_Shortlist, Approval_Log, RFQ_Dispatch_Log,
RFQ_Submissions, Tech/Comm/Overall Evaluations, Negotiation_Intelligence_Log,
Negotiation_Shortlist_Approval, NFA_Log, NFA_Approval_Log,
PO_Reference, SAP_PO_Data, DMS_Documents, Compliance_Log,
SVJ_Log, Spec_Requests, Process_Events_Log
"""

import sqlite3, shutil, os, json
from datetime import datetime

SRC = '/sessions/vibrant-zealous-mccarthy/s2c_sourcesense.db'
DST = '/sessions/vibrant-zealous-mccarthy/mnt/01. Sourcesense jsons/s2c_sourcesense.db'

conn = sqlite3.connect(SRC)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

def clr(*tables):
    for t in tables:
        cur.execute(f"DELETE FROM {t}")
    conn.commit()

# ─────────────────────────────────────────────────────────────────────────────
# Cluster reference data (from Part 3)
# ─────────────────────────────────────────────────────────────────────────────
clusters = {
    'CL-2025-00847-01': {
        'mat': '1000-10042678', 'grp': 'MRO-BRG', 'desc': 'Bearing 6205-2RS',
        'qty': 240, 'uom': 'NO', 'value': 117600, 'rfq': 'RFQ-2025-00289',
        'stage': 'NFA_Approved', 'buyer': 'ramesh.kumar@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20045','V-20046','V-20047','V-20054'],
        'winner': 'V-20045', 'lpp': 510.0, 'neg_price': 488.0,
        'po_number': '4500098710', 'po_created': True,
    },
    'CL-2025-00862-01': {
        'mat': '1000-10111001', 'grp': 'MRO-RFT', 'desc': 'Alumina Brick 70%',
        'qty': 2000, 'uom': 'NO', 'value': 960000, 'rfq': 'RFQ-2025-00294',
        'stage': 'NFA_Approved', 'buyer': 'karthik.rajan@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20074','V-20075'],
        'winner': 'V-20074', 'lpp': 510.0, 'neg_price': 480.0,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00863-01': {
        'mat': '1000-10113001', 'grp': 'MRO-ELC', 'desc': 'Carbon Electrode 300mm',
        'qty': 30, 'uom': 'NO', 'value': 255000, 'rfq': 'RFQ-2025-00295',
        'stage': 'Under_NFA_Approval', 'buyer': 'karthik.rajan@jswsteel.in',
        'plant': '1020', 'cat': 'Supply',
        'vendors_shortlist': ['V-20076','V-20077'],
        'winner': 'V-20076', 'lpp': 9200.0, 'neg_price': 8500.0,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00848-01': {
        'mat': '1000-10042679', 'grp': 'MRO-BRG', 'desc': 'Spherical Roller 22210 EK',
        'qty': 50, 'uom': 'NO', 'value': 142500, 'rfq': 'RFQ-2025-00290',
        'stage': 'RFQ_Evaluation', 'buyer': 'ramesh.kumar@jswsteel.in',
        'plant': '1020', 'cat': 'Supply',
        'vendors_shortlist': ['V-20045','V-20046','V-20047'],
        'winner': None, 'lpp': 2980.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00864-01': {
        'mat': '1000-10099001', 'grp': 'MRO-FLT', 'desc': 'Oil Filter LF3349',
        'qty': 80, 'uom': 'NO', 'value': 48000, 'rfq': 'RFQ-2025-00296',
        'stage': 'RFQ_Evaluation', 'buyer': 'priya.sharma@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20058','V-20068','V-20057'],
        'winner': None, 'lpp': 650.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00850-01': {
        'mat': '1000-10055001', 'grp': 'MRO-ELE', 'desc': 'Contactor 25A',
        'qty': 150, 'uom': 'NO', 'value': 43500, 'rfq': 'RFQ-2025-00291',
        'stage': 'RFQ_Dispatched', 'buyer': 'priya.sharma@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20048','V-20049','V-20056'],
        'winner': None, 'lpp': 310.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00865-01': {
        'mat': '1000-10103001', 'grp': 'MRO-PPE', 'desc': 'Safety Helmet HDPE Yellow',
        'qty': 400, 'uom': 'NO', 'value': 76000, 'rfq': 'RFQ-2025-00297',
        'stage': 'RFQ_Dispatched', 'buyer': 'deepika.nair@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20061','V-20059','V-20063'],
        'winner': None, 'lpp': 205.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00866-01': {
        'mat': '1000-10093001', 'grp': 'MRO-BLT', 'desc': 'V-Belt B-75',
        'qty': 64, 'uom': 'NO', 'value': 27200, 'rfq': 'RFQ-2025-00298',
        'stage': 'RFQ_Dispatched', 'buyer': 'anita.singh@jswsteel.in',
        'plant': '1030', 'cat': 'Supply',
        'vendors_shortlist': ['V-20064','V-20065'],
        'winner': None, 'lpp': 450.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00860-01': {
        'mat': '1000-10078001', 'grp': 'MRO-LUB', 'desc': 'Hydraulic Oil 68 210L',
        'qty': 5, 'uom': 'DR', 'value': 213000, 'rfq': 'RFQ-2025-00292',
        'stage': 'RFQ_Generated', 'buyer': 'sneha.patil@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20051','V-20088'],
        'winner': None, 'lpp': 44000.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
    'CL-2025-00868-01': {
        'mat': '1000-10107001', 'grp': 'MRO-VLV', 'desc': 'Gate Valve 2in 150#',
        'qty': 24, 'uom': 'NO', 'value': 33600, 'rfq': 'RFQ-2025-00299',
        'stage': 'RFQ_Generated', 'buyer': 'sanjay.verma@jswsteel.in',
        'plant': '1010', 'cat': 'Supply',
        'vendors_shortlist': ['V-20070','V-20071','V-20072'],
        'winner': None, 'lpp': 1500.0, 'neg_price': None,
        'po_number': None, 'po_created': False,
    },
}

# Stages that need only Spec/Process data
specs_only = {
    'CL-2025-00851-01': {'mat': '1000-10055003', 'desc': 'VFD Drive 7.5kW', 'buyer': 'anil.deshmukh@jswsteel.in'},
    'CL-2025-00867-01': {'mat': '1000-10201001', 'desc': 'TEFC Motor 15kW', 'buyer': 'anil.deshmukh@jswsteel.in'},
    'CL-2025-00861-01': {'mat': '1000-10089001', 'desc': 'Welding Rod E6013', 'buyer': 'sneha.patil@jswsteel.in'},
    'CL-2025-00852-01': {'mat': '1000-10067001', 'desc': 'Hydraulic Cylinder 80mm', 'buyer': 'sanjay.verma@jswsteel.in'},
    'CL-2025-00869-01': {'mat': '1000-10117001', 'desc': 'Power Cable 4C 16mm2', 'buyer': 'anil.deshmukh@jswsteel.in'},
    'CL-2025-00870-01': {'mat': '1000-10095001', 'desc': 'HT Bolt M20x80', 'buyer': None},
}

# ─────────────────────────────────────────────────────────────────────────────
print("=== PART 4: Transactional Sub-Tables ===")

# Clear all transactional tables
clr('Process_Events_Log','Spec_Requests','Compliance_Log','SVJ_Log',
    'DMS_Documents','Approval_Log','RFQ_Log','Vendor_Shortlist',
    'RFQ_Dispatch_Log','RFQ_Submissions','RFQ_Tech_Evaluations',
    'RFQ_Comm_Evaluations','RFQ_Overall_Evaluations',
    'Negotiation_Intelligence_Log','Negotiation_Shortlist_Approval',
    'NFA_Log','NFA_Approval_Log','PO_Reference','SAP_PO_Data')

# ─────────────────────────────────────────────────────────────────────────────
# 1. SPEC_REQUESTS — for Specs_Ready and Buyer_Assigned clusters
# ─────────────────────────────────────────────────────────────────────────────
spec_data = [
    ('SPR-001','CL-2025-00852-01','Mechanical Engineering Team','Completed','FILE-SPR-001','2025-11-22 09:00:00'),
    ('SPR-002','CL-2025-00869-01','Electrical Engineering Team','Completed','FILE-SPR-002','2025-11-24 10:00:00'),
    ('SPR-003','CL-2025-00851-01','Electrical Engineering Team','Completed','FILE-SPR-003','2025-11-21 14:00:00'),
    ('SPR-004','CL-2025-00867-01','Electrical Engineering Team','In_Progress','FILE-SPR-004','2025-11-25 11:00:00'),
    ('SPR-005','CL-2025-00861-01','Workshop Supervisor — Rolling Mill','Completed','FILE-SPR-005','2025-11-18 09:00:00'),
]
cur.executemany("INSERT INTO Spec_Requests VALUES(?,?,?,?,?,?)", spec_data)
print(f"  Spec_Requests: {len(spec_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. RFQ_LOG — for all clusters with an RFQ_ID
# ─────────────────────────────────────────────────────────────────────────────
rfq_log_data = []
rfq_meta = {
    'RFQ-2025-00289': ('CL-2025-00847-01','Closed','ramesh.kumar@jswsteel.in','2025-11-18 10:00:00','2025-11-18 10:00:00','2025-12-05'),
    'RFQ-2025-00290': ('CL-2025-00848-01','Open','ramesh.kumar@jswsteel.in','2025-11-20 09:00:00','2025-12-02 14:00:00','2025-12-20'),
    'RFQ-2025-00291': ('CL-2025-00850-01','Dispatched','priya.sharma@jswsteel.in','2025-11-22 11:00:00','2025-11-24 09:00:00','2025-12-15'),
    'RFQ-2025-00292': ('CL-2025-00860-01','Generated','sneha.patil@jswsteel.in','2025-11-26 15:00:00','2025-11-26 15:00:00','2025-12-26'),
    'RFQ-2025-00294': ('CL-2025-00862-01','Closed','karthik.rajan@jswsteel.in','2025-11-20 09:00:00','2025-11-20 09:00:00','2025-12-10'),
    'RFQ-2025-00295': ('CL-2025-00863-01','Open','karthik.rajan@jswsteel.in','2025-11-21 09:00:00','2025-12-01 16:00:00','2025-12-21'),
    'RFQ-2025-00296': ('CL-2025-00864-01','Open','priya.sharma@jswsteel.in','2025-11-24 10:00:00','2025-12-02 11:00:00','2025-12-18'),
    'RFQ-2025-00297': ('CL-2025-00865-01','Dispatched','deepika.nair@jswsteel.in','2025-11-28 09:00:00','2025-11-29 14:00:00','2025-12-22'),
    'RFQ-2025-00298': ('CL-2025-00866-01','Dispatched','anita.singh@jswsteel.in','2025-11-27 14:00:00','2025-11-28 10:00:00','2025-12-20'),
    'RFQ-2025-00299': ('CL-2025-00868-01','Generated','sanjay.verma@jswsteel.in','2025-11-30 11:00:00','2025-11-30 11:00:00','2025-12-28'),
}
eval_criteria = json.dumps({"technical_weight": 0.6, "commercial_weight": 0.4,
                             "criteria": ["spec_compliance","brand_approval","delivery","price","payment"]})
for rfq_id, (cl_id, status, buyer, created, updated, deadline) in rfq_meta.items():
    rfq_log_data.append((rfq_id, cl_id, status, eval_criteria, deadline, buyer, created, updated))
cur.executemany("INSERT INTO RFQ_Log VALUES(?,?,?,?,?,?,?,?)", rfq_log_data)
print(f"  RFQ_Log: {len(rfq_log_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. VENDOR_SHORTLIST — for all RFQ clusters
# ─────────────────────────────────────────────────────────────────────────────
sl_data = []
sl_id = 1
for cl_id, info in clusters.items():
    rfq = info['rfq']
    for rank, vc in enumerate(info['vendors_shortlist']):
        reason = 'Pre-qualified supplier — historical performance ≥3.5/5 | Spec-approved brand'
        score_map = {'V-20045':4.6,'V-20046':4.2,'V-20047':4.4,'V-20054':3.9,
                     'V-20074':4.3,'V-20075':4.0,'V-20076':4.5,'V-20077':3.8,
                     'V-20048':4.5,'V-20049':4.3,'V-20056':4.1,'V-20082':3.9,
                     'V-20058':4.4,'V-20068':4.0,'V-20057':4.2,'V-20051':4.6,
                     'V-20088':4.1,'V-20061':4.2,'V-20059':4.0,'V-20063':3.8,
                     'V-20064':4.5,'V-20065':4.3,'V-20070':4.3,'V-20071':4.1,
                     'V-20072':3.9}
        score = score_map.get(vc, 4.0)
        added = rfq_meta[rfq][3]
        sl_data.append((f'SL-{sl_id:04d}', rfq, vc, reason, score, added))
        sl_id += 1
cur.executemany("INSERT INTO Vendor_Shortlist VALUES(?,?,?,?,?,?)", sl_data)
print(f"  Vendor_Shortlist: {len(sl_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. COMPLIANCE_LOG — CTRL-001 (pre-RFQ checks) for all RFQ clusters
# ─────────────────────────────────────────────────────────────────────────────
comp_data = []
comp_id = 1
for rfq_id, (cl_id, status, buyer, created, updated, deadline) in rfq_meta.items():
    # CTRL-001: 3 vendor minimum check
    vc_count = len(clusters[cl_id]['vendors_shortlist'])
    result = 'Pass' if vc_count >= 3 else 'Fail_Override'
    details = f'{vc_count} vendors shortlisted' + ('' if vc_count >= 3 else ' — SVJ raised for 2-vendor exception')
    comp_data.append((f'COMP-{comp_id:04d}','CTRL-001','RFQ',rfq_id,result,details,created,None,None))
    comp_id += 1
    # CTRL-006: Budget check
    val = clusters[cl_id]['value']
    comp_data.append((f'COMP-{comp_id:04d}','CTRL-006','Cluster',cl_id,'Pass',
                      f'PR value INR {val:,.0f} within approved budget allocation',created,None,None))
    comp_id += 1
print(f"  Compliance_Log (CTRL-001/006): {len(comp_data)} (pre-NFA to be added)")

# ─────────────────────────────────────────────────────────────────────────────
# 5. APPROVAL_LOG — RFQ multi-tier approvals
# ─────────────────────────────────────────────────────────────────────────────
appr_data = []
appr_id = 1

def get_approver(value, cat):
    if cat == 'Capital':
        if value <= 5000000: return ('DES-L1-HOD-CAP','pradeep.kulkarni@jswsteel.in','Tier 1')
        elif value <= 50000000: return ('DES-L2-GM-PROC','rajesh.iyer@jswsteel.in','Tier 2')
        else: return ('DES-L3-VP-SCM','sunil.kapoor@jswsteel.in','Tier 3')
    else:
        if value <= 2500000: return ('DES-L1-HOD-MRO','vikram.singh@jswsteel.in','Tier 1')
        elif value <= 25000000: return ('DES-L2-GM-PROC','rajesh.iyer@jswsteel.in','Tier 2')
        else: return ('DES-L3-VP-SCM','sunil.kapoor@jswsteel.in','Tier 3')

for cl_id, info in clusters.items():
    rfq = info['rfq']
    val = info['value']
    cat = info['cat']
    des_code, email, tier = get_approver(val, cat)
    approved_rfq_stages = ['Closed','Dispatched','Open']  # all have been approved
    rfq_status = rfq_meta[rfq][1]
    if rfq_status in approved_rfq_stages:
        ts = rfq_meta[rfq][3]
        # Advance time by a few hours for approval
        from datetime import datetime, timedelta
        dt = datetime.fromisoformat(ts) + timedelta(hours=4)
        appr_data.append((f'APPR-{appr_id:04d}','RFQ',rfq,email,des_code,
                          'Approved','Vendors shortlisted and evaluated. RFQ criteria set.',
                          dt.strftime('%Y-%m-%d %H:%M:%S')))
        appr_id += 1
cur.executemany("INSERT INTO Approval_Log VALUES(?,?,?,?,?,?,?,?)", appr_data)
print(f"  Approval_Log (RFQ): {len(appr_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. DMS_DOCUMENTS — RFQ documents
# ─────────────────────────────────────────────────────────────────────────────
dms_data = []
dms_id = 1
for rfq_id, (cl_id, status, buyer, created, updated, deadline) in rfq_meta.items():
    dms_data.append((f'FILE-RFQ-{dms_id:04d}','RFQ','RFQ',rfq_id,
                     f'{rfq_id}_RFQ_Document.pdf',
                     f'DMS_Documents/RFQ/{rfq_id}_RFQ_Document.pdf',
                     buyer, created, 248, 1))
    dms_id += 1
print(f"  DMS_Documents (RFQ): {dms_id-1} (more to be added)")

# ─────────────────────────────────────────────────────────────────────────────
# 7. SVJ_LOG — Single/Two-Vendor Justification for 2-vendor clusters
# ─────────────────────────────────────────────────────────────────────────────
svj_data = []
two_vendor_rfqs = [
    ('RFQ-2025-00294','CL-2025-00862-01','karthik.rajan@jswsteel.in','2025-11-20 09:00:00'),
    ('RFQ-2025-00292','CL-2025-00860-01','sneha.patil@jswsteel.in','2025-11-26 15:00:00'),
    ('RFQ-2025-00298','CL-2025-00866-01','anita.singh@jswsteel.in','2025-11-27 14:00:00'),
]
for i, (rfq, cl, buyer, ts) in enumerate(two_vendor_rfqs, 1):
    svj_data.append((f'SVJ-{i:04d}', rfq,
                     'Only 2 pre-qualified vendors available for this material group. Third vendor is under onboarding.',
                     f'FILE-SVJ-{i:04d}','Approved',buyer,ts,
                     'vikram.singh@jswsteel.in',
                     (datetime.fromisoformat(ts)+timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')))
    # Update compliance for these
    comp_data.append((f'COMP-{comp_id:04d}','CTRL-001','RFQ',rfq,
                      'Pass_With_SVJ','SVJ raised and approved for 2-vendor exception',
                      ts,'vikram.singh@jswsteel.in','SVJ approved — ref SVJ log'))
    comp_id += 1
cur.executemany("INSERT INTO SVJ_Log VALUES(?,?,?,?,?,?,?,?,?)", svj_data)
print(f"  SVJ_Log: {len(svj_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. RFQ_DISPATCH_LOG — for Dispatched, Evaluation, and advanced clusters
# ─────────────────────────────────────────────────────────────────────────────
dispatch_data = []
disp_id = 1
dispatched_rfqs = {
    'RFQ-2025-00289': ('CL-2025-00847-01','2025-11-19 08:05:00'),
    'RFQ-2025-00290': ('CL-2025-00848-01','2025-11-22 08:30:00'),
    'RFQ-2025-00291': ('CL-2025-00850-01','2025-11-24 09:00:00'),
    'RFQ-2025-00294': ('CL-2025-00862-01','2025-11-21 07:30:00'),
    'RFQ-2025-00295': ('CL-2025-00863-01','2025-11-22 08:00:00'),
    'RFQ-2025-00296': ('CL-2025-00864-01','2025-11-25 09:00:00'),
    'RFQ-2025-00297': ('CL-2025-00865-01','2025-11-29 14:00:00'),
    'RFQ-2025-00298': ('CL-2025-00866-01','2025-11-28 10:00:00'),
}
for rfq_id, (cl_id, ts) in dispatched_rfqs.items():
    for vc in clusters[cl_id]['vendors_shortlist']:
        status = 'Delivered' if clusters[cl_id]['stage'] in ('NFA_Approved','Under_NFA_Approval','RFQ_Evaluation') else 'Sent'
        dispatch_data.append((f'DISP-{disp_id:04d}',rfq_id,vc,'Email',ts,status))
        disp_id += 1
        # DMS: dispatch confirmation
        dms_data.append((f'FILE-DISP-{disp_id:04d}','RFQ_Dispatch','RFQ',rfq_id,
                         f'{rfq_id}_Dispatch_{vc}.pdf',
                         f'DMS_Documents/RFQ/{rfq_id}_Dispatch_{vc}.pdf',
                         clusters[cl_id]['buyer'],ts, 42, 1))
cur.executemany("INSERT INTO RFQ_Dispatch_Log VALUES(?,?,?,?,?,?)", dispatch_data)
print(f"  RFQ_Dispatch_Log: {len(dispatch_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 9. RFQ_SUBMISSIONS — for RFQ_Evaluation, Under_NFA_Approval, NFA_Approved
# ─────────────────────────────────────────────────────────────────────────────
# Submission pricing per cluster per vendor
submission_pricing = {
    # CL-2025-00847-01: 6205-2RS bearing, LPP=510, winner SKF @ 488
    'RFQ-2025-00289': [
        ('V-20045', 488.0, 14, '2025-11-28 14:00:00'),
        ('V-20046', 505.0, 21, '2025-11-27 10:00:00'),
        ('V-20047', 495.0, 18, '2025-11-28 09:00:00'),
        ('V-20054', 528.0, 30, '2025-11-26 16:00:00'),
    ],
    # CL-2025-00848-01: Spherical roller, LPP=2980
    'RFQ-2025-00290': [
        ('V-20045', 2850.0, 21, '2025-12-04 11:00:00'),
        ('V-20046', 2920.0, 28, '2025-12-03 15:00:00'),
        ('V-20047', 2780.0, 30, '2025-12-05 09:00:00'),
    ],
    # CL-2025-00863-01: Carbon electrode, LPP=9200, winner HEG @ 8500
    'RFQ-2025-00295': [
        ('V-20076', 8500.0, 21, '2025-12-03 14:00:00'),
        ('V-20077', 9100.0, 28, '2025-12-02 10:00:00'),
    ],
    # CL-2025-00862-01: Alumina brick, LPP=510 (per unit), winner IFGL
    'RFQ-2025-00294': [
        ('V-20074', 480.0, 30, '2025-11-30 13:00:00'),
        ('V-20075', 498.0, 35, '2025-11-29 11:00:00'),
    ],
    # CL-2025-00864-01: Oil filter LF3349, LPP=650
    'RFQ-2025-00296': [
        ('V-20058', 590.0, 14, '2025-12-05 14:00:00'),
        ('V-20068', 620.0, 21, '2025-12-04 10:00:00'),
        ('V-20057', 615.0, 18, '2025-12-06 11:00:00'),
    ],
}

sub_data = []
sub_id = 1
sub_id_map = {}  # rfq+vendor -> submission_id

for rfq_id, subs in submission_pricing.items():
    cl_id = rfq_meta[rfq_id][0]
    for (vc, price, lt, ts) in subs:
        sid = f'SUB-{sub_id:04d}'
        sub_id_map[(rfq_id, vc)] = sid
        sub_data.append((sid, rfq_id, vc, price, lt, f'FILE-SUB-{sub_id:04d}', ts))
        sub_id += 1
        # DMS: submission file
        dms_data.append((f'FILE-SUB-{sub_id:04d}','RFQ_Submission','Submission',sid,
                         f'{rfq_id}_{vc}_Quote.pdf',
                         f'DMS_Documents/RFQ/{rfq_id}_{vc}_Quote.pdf',
                         vc, ts, 185, 1))
cur.executemany("INSERT INTO RFQ_Submissions VALUES(?,?,?,?,?,?,?)", sub_data)
print(f"  RFQ_Submissions: {len(sub_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 10. TECHNICAL EVALUATIONS
# ─────────────────────────────────────────────────────────────────────────────
tech_eval_data = []
te_id = 1
# Tech scores: 0-100, based on spec compliance, brand approval, quality certs
tech_scores = {
    'SUB-0001': (92.0, 'SKF — OEM approved brand. Full spec compliance. ISO 9001 cert.'),
    'SUB-0002': (78.0, 'NTN — Approved brand. Minor deviation on C3 clearance spec.'),
    'SUB-0003': (85.0, 'Timken — Approved brand. Full compliance. Good certs.'),
    'SUB-0004': (65.0, 'Precision Bearings — Not OEM approved. Spec compliant but brand not preferred.'),
    'SUB-0005': (88.0, 'SKF — Full spec compliance. OEM approved.'),
    'SUB-0006': (82.0, 'NTN — Spec compliant.'),
    'SUB-0007': (90.0, 'Timken — Full compliance. ISO cert.'),
    'SUB-0008': (88.0, 'HEG — OEM recommended. Full spec compliance.'),
    'SUB-0009': (70.0, 'Tata Steel — Acceptable spec compliance. Non-preferred brand.'),
    'SUB-0010': (86.0, 'IFGL — ISO certified, full spec compliance.'),
    'SUB-0011': (78.0, 'Calderys — Acceptable compliance, minor Al2O3% deviation.'),
    'SUB-0012': (85.0, 'Donaldson — OEM compatible, full spec.'),
    'SUB-0013': (72.0, 'Alfa Laval — Compatible but not OEM recommended.'),
    'SUB-0014': (80.0, 'Parker — Compatible, spec compliant.'),
}
for sid_key, (score, remarks) in tech_scores.items():
    tech_eval_data.append((f'TE-{te_id:04d}', sid_key, score, remarks))
    te_id += 1
cur.executemany("INSERT INTO RFQ_Tech_Evaluations VALUES(?,?,?,?)", tech_eval_data)
print(f"  RFQ_Tech_Evaluations: {len(tech_eval_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 11. COMMERCIAL EVALUATIONS
# Price_Score = (lowest_price / vendor_price) * 100
# Payment_Score: 100=Net30, 85=Net45, 70=Advance
# Delivery_Score: <=14d=100, <=21d=85, <=30d=70, >30d=55
# ─────────────────────────────────────────────────────────────────────────────
comm_eval_data = []
ce_id = 1

def price_score(vendor_price, min_price): return round(min_price / vendor_price * 100, 1)
def payment_score(terms): return 100 if 'Net 30' in terms else (85 if 'Net 45' in terms else 70)
def delivery_score(days):
    if days <= 14: return 100
    elif days <= 21: return 85
    elif days <= 30: return 70
    else: return 55

# Group by RFQ
comm_inputs = {
    'RFQ-2025-00289': [
        ('SUB-0001','V-20045',488.0,14,'Net 45 days from GRN'),
        ('SUB-0002','V-20046',505.0,21,'Net 30 days from GRN'),
        ('SUB-0003','V-20047',495.0,18,'Net 45 days from GRN'),
        ('SUB-0004','V-20054',528.0,30,'Net 30 days from GRN'),
    ],
    'RFQ-2025-00290': [
        ('SUB-0005','V-20045',2850.0,21,'Net 45 days from GRN'),
        ('SUB-0006','V-20046',2920.0,28,'Net 30 days from GRN'),
        ('SUB-0007','V-20047',2780.0,30,'Net 45 days from GRN'),
    ],
    'RFQ-2025-00295': [
        ('SUB-0008','V-20076',8500.0,21,'Net 30 days from GRN'),
        ('SUB-0009','V-20077',9100.0,28,'Net 45 days from GRN'),
    ],
    'RFQ-2025-00294': [
        ('SUB-0010','V-20074',480.0,30,'Net 30 days from GRN'),
        ('SUB-0011','V-20075',498.0,35,'Net 30 days from GRN'),
    ],
    'RFQ-2025-00296': [
        ('SUB-0012','V-20058',590.0,14,'Net 30 days from GRN'),
        ('SUB-0013','V-20068',620.0,21,'Net 30 days from GRN'),
        ('SUB-0014','V-20057',615.0,18,'Net 45 days from GRN'),
    ],
}

for rfq_id, subs_list in comm_inputs.items():
    min_price = min(s[2] for s in subs_list)
    for (sid, vc, price, lt, terms) in subs_list:
        ps = price_score(price, min_price)
        pays = payment_score(terms)
        ds = delivery_score(lt)
        remarks = f'Price: {price:.1f} (min:{min_price:.1f}) | Lead:{lt}d | {terms}'
        comm_eval_data.append((f'CE-{ce_id:04d}', sid, ps, pays, ds, remarks))
        ce_id += 1
cur.executemany("INSERT INTO RFQ_Comm_Evaluations VALUES(?,?,?,?,?,?)", comm_eval_data)
print(f"  RFQ_Comm_Evaluations: {len(comm_eval_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 12. OVERALL EVALUATIONS — Weighted: Tech 60%, Comm 40%
# Comm composite = Price 50% + Payment 25% + Delivery 25%
# ─────────────────────────────────────────────────────────────────────────────
overall_data = []
oe_id = 1
tech_map = {row[1]: (row[0], row[2]) for row in tech_eval_data}   # sid -> (te_id, tech_score)
comm_map = {row[1]: (row[0], row[2], row[3], row[4]) for row in comm_eval_data}  # sid -> (ce_id, price_s, pay_s, del_s)

for sid in tech_map:
    if sid in comm_map:
        _, tech_s = tech_map[sid]
        _, price_s, pay_s, del_s = comm_map[sid]
        comm_composite = price_s * 0.5 + pay_s * 0.25 + del_s * 0.25
        tech_w = round(tech_s * 0.6, 2)
        comm_w = round(comm_composite * 0.4, 2)
        overall = round(tech_w + comm_w, 2)
        overall_data.append((f'OE-{oe_id:04d}', sid, tech_w, comm_w, overall))
        oe_id += 1
cur.executemany("INSERT INTO RFQ_Overall_Evaluations VALUES(?,?,?,?,?)", overall_data)
print(f"  RFQ_Overall_Evaluations: {len(overall_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 13. NEGOTIATION_INTELLIGENCE_LOG — for NFA clusters
# ─────────────────────────────────────────────────────────────────────────────
neg_intel = [
    (
        'NEG-BRIEF-001','RFQ-2025-00289',
        json.dumps({
            "rfq_id": "RFQ-2025-00289",
            "cluster_id": "CL-2025-00847-01",
            "material": "Bearing 6205-2RS",
            "total_submissions": 4,
            "lowest_quote": {"vendor": "V-20045", "price": 488.0},
            "highest_quote": {"vendor": "V-20054", "price": 528.0},
            "lpp": 510.0,
            "best_price_vs_lpp_pct": -4.3,
            "recommended_target": 482.0,
            "negotiation_strategy": "SKF is preferred OEM. Leverage competitor quotes (Timken@495) to push for 1-2% further reduction. SKF has delivered on time 94% historically."
        }),
        json.dumps({
            "market_trend": "Bearing prices stable in Q4-2025. Steel input costs flat.",
            "competitors_in_market": ["SKF","NSK","NTN","Timken"],
            "average_market_price_in_2025": 505.0,
            "recommendation": "Proceed with SKF at 488 or negotiate to 482. LPP savings of 5.5% achievable."
        })
    ),
    (
        'NEG-BRIEF-002','RFQ-2025-00294',
        json.dumps({
            "rfq_id": "RFQ-2025-00294",
            "cluster_id": "CL-2025-00862-01",
            "material": "High Alumina Brick 70%",
            "total_submissions": 2,
            "lowest_quote": {"vendor": "V-20074", "price": 480.0},
            "highest_quote": {"vendor": "V-20075", "price": 498.0},
            "lpp": 510.0,
            "best_price_vs_lpp_pct": -5.9,
            "recommended_target": 475.0,
            "negotiation_strategy": "IFGL is established supplier. Only 2 vendors — limited leverage. SVJ approved. Target 1% further reduction citing volume order of 2000 nos."
        }),
        json.dumps({
            "market_trend": "Refractory prices declined 4% in 2025 due to reduced BF demand nationwide.",
            "recommendation": "IFGL at 480 is already below LPP. Proceed — strong savings case for NFA."
        })
    ),
    (
        'NEG-BRIEF-003','RFQ-2025-00295',
        json.dumps({
            "rfq_id": "RFQ-2025-00295",
            "cluster_id": "CL-2025-00863-01",
            "material": "Carbon Electrode 300mm",
            "total_submissions": 2,
            "lowest_quote": {"vendor": "V-20076", "price": 8500.0},
            "lpp": 9200.0,
            "best_price_vs_lpp_pct": -7.6,
            "recommended_target": 8400.0,
            "negotiation_strategy": "HEG is market leader. 7.6% below LPP already. BAFO pushed for 8400. Only 2 vendors available in India for RP-grade 300mm electrodes."
        }),
        json.dumps({
            "market_trend": "Carbon electrode prices dropped due to global EAF slowdown. HEG aggressive on pricing.",
            "recommendation": "Proceed with HEG at BAFO of 8500 or negotiate to 8400. Exceptional savings vs LPP."
        })
    ),
]
cur.executemany("INSERT INTO Negotiation_Intelligence_Log VALUES(?,?,?,?)", neg_intel)
print(f"  Negotiation_Intelligence_Log: {len(neg_intel)}")

# ─────────────────────────────────────────────────────────────────────────────
# 14. NEGOTIATION_SHORTLIST_APPROVAL
# ─────────────────────────────────────────────────────────────────────────────
neg_appr = [
    ('NEG-APPR-001','RFQ-2025-00289','V-20045',488.0,'Approved',
     'vikram.singh@jswsteel.in','2025-11-30 11:00:00'),
    ('NEG-APPR-002','RFQ-2025-00294','V-20074',480.0,'Approved',
     'vikram.singh@jswsteel.in','2025-12-01 10:00:00'),
    ('NEG-APPR-003','RFQ-2025-00295','V-20076',8500.0,'Pending',
     None, None),
]
cur.executemany("INSERT INTO Negotiation_Shortlist_Approval VALUES(?,?,?,?,?,?,?)", neg_appr)
print(f"  Negotiation_Shortlist_Approval: {len(neg_appr)}")

# ─────────────────────────────────────────────────────────────────────────────
# 15. NFA_LOG
# ─────────────────────────────────────────────────────────────────────────────
nfa_data = [
    ('NFA-2025-00125','CL-2025-00847-01','RFQ-2025-00289',
     'V-20045',488.0,117120.0,'Below_LPP',-4.3,5.4,
     'SKF 6205-2RS at INR 488/No — 4.3% below LPP of INR 510. OEM preferred brand. ISO 9001 certified. 94% OTIF in last 24 months.',
     'Approved','FILE-NFA-001','ramesh.kumar@jswsteel.in','2025-11-30 10:00:00','2025-12-02 14:30:00'),
    ('NFA-2025-00129','CL-2025-00862-01','RFQ-2025-00294',
     'V-20074',480.0,960000.0,'Below_LPP',-5.9,5.9,
     'IFGL Alumina Brick at INR 480/No — 5.9% below LPP. ISO certified. Only 2 qualified vendors in India. SVJ approved.',
     'Approved','FILE-NFA-002','karthik.rajan@jswsteel.in','2025-11-30 15:00:00','2025-11-30 16:00:00'),
    ('NFA-2025-00130','CL-2025-00863-01','RFQ-2025-00295',
     'V-20076',8500.0,255000.0,'Below_LPP',-7.6,7.6,
     'HEG Carbon Electrode at INR 8500/No — 7.6% below LPP. Market leader. Only 2 suppliers in India for RP-grade 300mm.',
     'Draft','FILE-NFA-003','karthik.rajan@jswsteel.in','2025-12-01 11:00:00','2025-12-01 11:00:00'),
]
cur.executemany("INSERT INTO NFA_Log VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", nfa_data)
print(f"  NFA_Log: {len(nfa_data)}")

# CTRL-003: NFA price vs LPP compliance
nfa_comp = [
    (f'COMP-{comp_id:04d}','CTRL-003','NFA','NFA-2025-00125','Pass',
     'NFA price INR 488 is 4.3% below LPP of INR 510. No justification required.','2025-11-30 10:00:00',None,None),
    (f'COMP-{comp_id+1:04d}','CTRL-003','NFA','NFA-2025-00129','Pass',
     'NFA price INR 480 is 5.9% below LPP of INR 510. Strong savings case.','2025-11-30 15:00:00',None,None),
    (f'COMP-{comp_id+2:04d}','CTRL-003','NFA','NFA-2025-00130','Pass',
     'NFA price INR 8500 is 7.6% below LPP of INR 9200.','2025-12-01 11:00:00',None,None),
]
comp_data.extend(nfa_comp)
comp_id += 3

# ─────────────────────────────────────────────────────────────────────────────
# 16. NFA_APPROVAL_LOG
# ─────────────────────────────────────────────────────────────────────────────
nfa_appr_data = [
    # NFA-2025-00125: fully approved (2-tier for value > 25L needs L2; but 117K < 25L, so L1 only)
    ('NFAA-001','NFA-2025-00125',1,'Head of Department — MRO',
     'vikram.singh@jswsteel.in','Approved','Value within DOP L1 limit. SKF preferred vendor. Savings confirmed.','2025-12-01 10:00:00'),
    # NFA-2025-00129: 960K < 25L, L1 approver
    ('NFAA-002','NFA-2025-00129',1,'Head of Department — MRO',
     'vikram.singh@jswsteel.in','Approved','IFGL is established refractory supplier. Price below LPP. SVJ approved.','2025-11-30 16:00:00'),
    # NFA-2025-00130: 255K < 25L, L1 pending
    ('NFAA-003','NFA-2025-00130',1,'Head of Department — MRO',
     'vikram.singh@jswsteel.in','Pending',None,None),
]
cur.executemany("INSERT INTO NFA_Approval_Log VALUES(?,?,?,?,?,?,?,?)", nfa_appr_data)
print(f"  NFA_Approval_Log: {len(nfa_appr_data)}")

# DMS: NFA documents
for i, (nfa_id, _, rfq_id, vc, *rest) in enumerate(nfa_data, 1):
    dms_data.append((f'FILE-NFA-{i:03d}','NFA','NFA',nfa_id,
                     f'{nfa_id}_NFA_Document.pdf',
                     f'DMS_Documents/NFA/{nfa_id}_NFA_Document.pdf',
                     rest[9],'2025-12-01 10:00:00',412,1))

# ─────────────────────────────────────────────────────────────────────────────
# 17. PO_REFERENCE — for NFA_Approved clusters
# ─────────────────────────────────────────────────────────────────────────────
po_ref_data = [
    ('PO-REF-001','NFA-2025-00125','CL-2025-00847-01','4500098710',
     'FILE-PO-001','2025-12-04 15:30:00','Success','ramesh.kumar@jswsteel.in','2025-12-03 10:00:00'),
    ('PO-REF-002','NFA-2025-00129','CL-2025-00862-01',None,
     None,None,'Pending','karthik.rajan@jswsteel.in','2025-12-03 14:00:00'),
]
cur.executemany("INSERT INTO PO_Reference VALUES(?,?,?,?,?,?,?,?,?)", po_ref_data)
print(f"  PO_Reference: {len(po_ref_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 18. SAP_PO_DATA — for PO-REF-001 (CL-2025-00847-01)
# ─────────────────────────────────────────────────────────────────────────────
sap_po_data = [
    ('4500098710','V-20045','1000-10042678','1010',
     488.0, 240,'NO', 117120.0,'2025-12-15',
     'NT45','EXW','ZSTD','Open',
     None,None,'Unpaid',
     '2025-12-03 10:00:00',None,None,None,
     'Auto-created by PO.16 BAPI mimic. CL-2025-00847-01 Bearing cluster.'),
]
cur.executemany("INSERT INTO SAP_PO_Data VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", sap_po_data)
print(f"  SAP_PO_Data: {len(sap_po_data)}")

# DMS: PO document
dms_data.append(('FILE-PO-001','PO','PO','4500098710',
                 'PO_4500098710_SKF_Bearing6205.pdf',
                 'DMS_Documents/PO/PO_4500098710_SKF_Bearing6205.pdf',
                 'ramesh.kumar@jswsteel.in','2025-12-03 10:30:00',198,1))

# ─────────────────────────────────────────────────────────────────────────────
# 19. INSERT ALL DMS_DOCUMENTS + COMPLIANCE_LOG
# ─────────────────────────────────────────────────────────────────────────────
cur.executemany("INSERT INTO DMS_Documents VALUES(?,?,?,?,?,?,?,?,?,?)", dms_data)
print(f"  DMS_Documents: {len(dms_data)}")

cur.executemany("INSERT INTO Compliance_Log VALUES(?,?,?,?,?,?,?,?,?)", comp_data)
print(f"  Compliance_Log: {len(comp_data)}")

# ─────────────────────────────────────────────────────────────────────────────
# 20. PROCESS_EVENTS_LOG — lifecycle events for all 16 clusters
# ─────────────────────────────────────────────────────────────────────────────
ev_data = []
ev_id = 1

event_stages = {
    'CL-2025-00847-01': [
        ('PR_CREATED','PR received from SAP — bearing cluster BF plant','system','2025-11-14 09:00:00'),
        ('SPEC_EXTRACTED','Gemini extracted 6 technical specs from PR long text','pr_02_spec_extraction','2025-11-14 10:30:00'),
        ('BUYER_ASSIGNED','Buyer ramesh.kumar assigned based on MRO-BRG group','pr_03_buyer_assignment','2025-11-14 11:45:00'),
        ('VENDOR_SHORTLISTED','4 vendors shortlisted — SKF, NTN, Timken, Precision','rfq_04_vendor_shortlisting','2025-11-17 14:00:00'),
        ('RFQ_CREATED','RFQ-2025-00289 generated','rfq_05_rfq_creation','2025-11-18 10:00:00'),
        ('RFQ_APPROVED','RFQ approved by HOD Vikram Singh','rfq_07_rfq_approval','2025-11-18 14:00:00'),
        ('RFQ_DISPATCHED','RFQ dispatched to 4 vendors via email','rfq_08_rfq_dispatch','2025-11-19 08:05:00'),
        ('SUBMISSIONS_RECEIVED','4 quotes received before deadline','rfq_09_offer_collection','2025-11-28 14:00:00'),
        ('TECH_EVAL_COMPLETE','Technical evaluation completed — SKF L1 (92/100)','eval_08_tech_evaluation','2025-11-29 10:00:00'),
        ('COMM_EVAL_COMPLETE','Commercial evaluation — SKF lowest price 488','eval_09_comm_evaluation','2025-11-29 12:00:00'),
        ('OVERALL_RANKED','SKF ranked L1 overall (79.6/100)','eval_10_overall_ranking','2025-11-29 14:00:00'),
        ('NEG_BRIEF_CREATED','Negotiation intelligence brief generated by Gemini','neg_11_negotiation_copilot','2025-11-30 09:00:00'),
        ('NEG_APPROVED','Negotiation BAFO accepted — SKF at 488','neg_12_negotiation_approval','2025-11-30 11:00:00'),
        ('NFA_GENERATED','NFA-2025-00125 drafted by Gemini','nfa_13_nfa_generation','2025-11-30 10:00:00'),
        ('NFA_APPROVED','NFA approved by HOD. Savings: 5.4% vs LPP','nfa_14_nfa_approval','2025-12-02 14:30:00'),
        ('PO_REF_CREATED','PO tracking reference PO-REF-001 created','po_15_po_reference_creation','2025-12-03 10:00:00'),
        ('SAP_BAPI_CALLED','SAP BAPI_PO_CREATE1 simulated — PO 4500098710 created','po_16_sap_bapi_call','2025-12-03 10:05:00'),
        ('PO_DOCUMENT_SAVED','PO document generated and saved to DMS','po_17_po_document_attach','2025-12-03 10:30:00'),
        ('PO_DISPATCHED','PO emailed to SKF India — vendor acknowledged','po_18_vendor_dispatch','2025-12-04 15:30:00'),
    ],
    'CL-2025-00862-01': [
        ('PR_CREATED','PR received — alumina brick BF lining','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer karthik.rajan assigned','pr_03_buyer_assignment','2025-11-15 12:00:00'),
        ('VENDOR_SHORTLISTED','2 vendors — IFGL, Calderys. SVJ raised.','rfq_04_vendor_shortlisting','2025-11-18 12:00:00'),
        ('SVJ_APPROVED','SVJ approved by HOD — 2-vendor exception','rfq_06_compliance_attach','2025-11-20 08:00:00'),
        ('RFQ_DISPATCHED','RFQ dispatched to 2 vendors','rfq_08_rfq_dispatch','2025-11-21 07:30:00'),
        ('SUBMISSIONS_RECEIVED','2 quotes received','rfq_09_offer_collection','2025-11-30 13:00:00'),
        ('OVERALL_RANKED','IFGL ranked L1 (480 < Calderys 498)','eval_10_overall_ranking','2025-12-01 09:00:00'),
        ('NFA_GENERATED','NFA-2025-00129 drafted','nfa_13_nfa_generation','2025-11-30 15:00:00'),
        ('NFA_APPROVED','NFA approved — IFGL at 480, 5.9% below LPP','nfa_14_nfa_approval','2025-11-30 16:00:00'),
        ('PO_REF_CREATED','PO-REF-002 created — awaiting SAP PO','po_15_po_reference_creation','2025-12-03 14:00:00'),
    ],
    'CL-2025-00863-01': [
        ('PR_CREATED','PR received — carbon electrode EAF SMS','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer karthik.rajan assigned','pr_03_buyer_assignment','2025-11-16 10:00:00'),
        ('VENDOR_SHORTLISTED','2 vendors — HEG, Tata Steel. SVJ raised.','rfq_04_vendor_shortlisting','2025-11-19 10:00:00'),
        ('RFQ_DISPATCHED','RFQ dispatched to 2 vendors','rfq_08_rfq_dispatch','2025-11-22 08:00:00'),
        ('SUBMISSIONS_RECEIVED','2 quotes received — HEG 8500, Tata 9100','rfq_09_offer_collection','2025-12-03 14:00:00'),
        ('OVERALL_RANKED','HEG ranked L1 overall','eval_10_overall_ranking','2025-12-04 09:00:00'),
        ('NEG_BRIEF_CREATED','Negotiation brief generated','neg_11_negotiation_copilot','2025-12-04 10:00:00'),
        ('NFA_GENERATED','NFA-2025-00130 drafted — HEG at 8500','nfa_13_nfa_generation','2025-12-01 11:00:00'),
        ('NFA_PENDING_APPROVAL','NFA submitted for HOD approval','nfa_14_nfa_approval','2025-12-01 12:00:00'),
    ],
    'CL-2025-00848-01': [
        ('PR_CREATED','PR received — spherical roller SMS caster','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer ramesh.kumar assigned','pr_03_buyer_assignment','2025-11-15 10:00:00'),
        ('RFQ_DISPATCHED','RFQ-2025-00290 dispatched to 3 bearing vendors','rfq_08_rfq_dispatch','2025-11-22 08:30:00'),
        ('SUBMISSIONS_RECEIVED','3 quotes received — Timken 2780 lowest','rfq_09_offer_collection','2025-12-05 09:00:00'),
        ('TECH_EVAL_COMPLETE','Technical evaluation complete','eval_08_tech_evaluation','2025-12-06 10:00:00'),
        ('COMM_EVAL_COMPLETE','Commercial evaluation — Timken price-score highest','eval_09_comm_evaluation','2025-12-06 12:00:00'),
        ('OVERALL_RANKED','Timken ranked L1 — overall eval pending NEG','eval_10_overall_ranking','2025-12-07 09:00:00'),
    ],
    'CL-2025-00864-01': [
        ('PR_CREATED','PR received — oil filter workshop','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer priya.sharma assigned','pr_03_buyer_assignment','2025-11-16 14:00:00'),
        ('RFQ_DISPATCHED','RFQ-2025-00296 dispatched to 3 filter vendors','rfq_08_rfq_dispatch','2025-11-25 09:00:00'),
        ('SUBMISSIONS_RECEIVED','3 quotes received — Donaldson 590 lowest','rfq_09_offer_collection','2025-12-06 14:00:00'),
        ('OVERALL_RANKED','Donaldson ranked L1 — proceeding to NEG','eval_10_overall_ranking','2025-12-07 11:00:00'),
    ],
    'CL-2025-00850-01': [
        ('PR_CREATED','PR received — contactors BF electrical panel','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer priya.sharma assigned','pr_03_buyer_assignment','2025-11-15 11:00:00'),
        ('RFQ_DISPATCHED','RFQ-2025-00291 dispatched to Schneider, ABB, Siemens','rfq_08_rfq_dispatch','2025-11-24 09:00:00'),
        ('FOLLOW_UP_SENT','Offer collection follow-up sent — deadline in 10 days','rfq_09_offer_collection','2025-12-05 09:00:00'),
    ],
    'CL-2025-00865-01': [
        ('PR_CREATED','PR received — safety helmets BF','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer deepika.nair assigned','pr_03_buyer_assignment','2025-11-17 09:00:00'),
        ('RFQ_DISPATCHED','RFQ-2025-00297 dispatched to 3 PPE vendors','rfq_08_rfq_dispatch','2025-11-29 14:00:00'),
    ],
    'CL-2025-00866-01': [
        ('PR_CREATED','PR received — V-belts rolling mill','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer anita.singh assigned','pr_03_buyer_assignment','2025-11-15 15:00:00'),
        ('SVJ_APPROVED','SVJ approved — only 2 belt vendors available','rfq_06_compliance_attach','2025-11-27 11:00:00'),
        ('RFQ_DISPATCHED','RFQ-2025-00298 dispatched to Gates, Fenner','rfq_08_rfq_dispatch','2025-11-28 10:00:00'),
    ],
    'CL-2025-00860-01': [
        ('PR_CREATED','PR received — hydraulic oil BF','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer sneha.patil assigned','pr_03_buyer_assignment','2025-11-16 13:00:00'),
        ('VENDOR_SHORTLISTED','2 vendors shortlisted — IOCL, BASF','rfq_04_vendor_shortlisting','2025-11-25 10:00:00'),
        ('RFQ_CREATED','RFQ-2025-00292 generated — pending approval','rfq_05_rfq_creation','2025-11-26 15:00:00'),
    ],
    'CL-2025-00868-01': [
        ('PR_CREATED','PR received — gate valves BF piping','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer sanjay.verma assigned','pr_03_buyer_assignment','2025-11-17 11:00:00'),
        ('RFQ_CREATED','RFQ-2025-00299 generated — pending dispatch','rfq_05_rfq_creation','2025-11-30 11:00:00'),
    ],
    'CL-2025-00851-01': [
        ('PR_CREATED','PR received — VFD drive SMS rolling mill','system','2025-11-14 09:00:00'),
        ('SPEC_EXTRACTED','Gemini extracted specs — 7.5kW, 3-phase, 415V, IP55','pr_02_spec_extraction','2025-11-15 09:00:00'),
        ('BUYER_ASSIGNED','Buyer anil.deshmukh assigned (Capital goods)','pr_03_buyer_assignment','2025-11-16 14:00:00'),
    ],
    'CL-2025-00867-01': [
        ('PR_CREATED','PR received — TEFC motor SMS conveyor','system','2025-11-14 09:00:00'),
        ('BUYER_ASSIGNED','Buyer anil.deshmukh assigned','pr_03_buyer_assignment','2025-11-17 12:00:00'),
    ],
    'CL-2025-00861-01': [
        ('PR_CREATED','PR received — welding rods rolling mill','system','2025-11-14 09:00:00'),
        ('SPEC_EXTRACTED','Specs extracted — E6013, 3.15mm, AWS A5.1','pr_02_spec_extraction','2025-11-15 11:00:00'),
        ('BUYER_ASSIGNED','Buyer sneha.patil assigned','pr_03_buyer_assignment','2025-11-15 16:00:00'),
    ],
    'CL-2025-00852-01': [
        ('PR_CREATED','PR received — hydraulic cylinder BF charging','system','2025-11-14 09:00:00'),
        ('SPEC_EXTRACTED','Specs extracted — 80mm bore, 500mm stroke, 150bar','pr_02_spec_extraction','2025-11-15 14:00:00'),
        ('BUYER_ASSIGNED','Buyer sanjay.verma assigned','pr_03_buyer_assignment','2025-11-17 10:00:00'),
        ('SPEC_REQUEST_SENT','Technical spec request sent to engineering team','pr_02_spec_extraction','2025-11-22 09:00:00'),
    ],
    'CL-2025-00869-01': [
        ('PR_CREATED','PR received — power cable SMS electrical','system','2025-11-14 09:00:00'),
        ('SPEC_EXTRACTED','Specs extracted — 4C 16mm2, XLPE/SWA, 1.1kV','pr_02_spec_extraction','2025-11-16 09:00:00'),
        ('BUYER_ASSIGNED','Buyer anil.deshmukh assigned (Capital)','pr_03_buyer_assignment','2025-11-18 10:00:00'),
        ('SPEC_REQUEST_SENT','Technical drawings requested from electrical dept','pr_02_spec_extraction','2025-11-24 10:00:00'),
    ],
    'CL-2025-00870-01': [
        ('PR_CREATED','New PR received — HT bolts M20x80 BF maintenance','system','2025-11-14 09:00:00'),
    ],
}

for cl_id, events in event_stages.items():
    for (ev_type, desc, actor, ts) in events:
        ev_data.append((f'EVT-{ev_id:04d}','S2C-PIPELINE','Cluster',cl_id,ev_type,desc,actor,ts))
        ev_id += 1
cur.executemany("INSERT INTO Process_Events_Log VALUES(?,?,?,?,?,?,?,?)", ev_data)
print(f"  Process_Events_Log: {len(ev_data)}")

# ─────────────────────────────────────────────────────────────────────────────
conn.commit()
print()
print("=== FINAL DATABASE VERIFICATION ===")
tables = [
    'Material_Master','Vendor_Master','Buyer_Master','DOP','Designations_Master',
    'Consolidated_PRs','Master_PR_Data','Vendor_Shortlist','RFQ_Log',
    'RFQ_Dispatch_Log','RFQ_Submissions','RFQ_Tech_Evaluations',
    'RFQ_Comm_Evaluations','RFQ_Overall_Evaluations',
    'Negotiation_Intelligence_Log','Negotiation_Shortlist_Approval',
    'NFA_Log','NFA_Approval_Log','PO_Reference','SAP_PO_Data',
    'DMS_Documents','Compliance_Log','SVJ_Log','Spec_Requests','Process_Events_Log',
    'Procurement_Historical_Pricing','Vendor_History'
]
total = 0
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    n = cur.fetchone()[0]
    total += n
    print(f"  {t:<38}: {n:>4}")
print(f"  {'TOTAL ROWS':<38}: {total:>4}")
conn.close()

print()
print("Copying to workspace folder...")
shutil.copy2(SRC, DST)
print(f"✅ Part 4 complete — DB saved to {DST}")
