"""Part 3: ERP ref data + 16 pipeline clusters at different stages + vendor history."""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("s2c_sourcesense.db")
conn.execute("PRAGMA foreign_keys = OFF")
c = conn.cursor()

for t in ["Procurement_Historical_Pricing","Vendor_History","Master_PR_Data",
          "Consolidated_PRs","RFQ_Log","Vendor_Shortlist","RFQ_Dispatch_Log",
          "RFQ_Submissions","RFQ_Tech_Evaluations","RFQ_Comm_Evaluations",
          "RFQ_Overall_Evaluations","Negotiation_Intelligence_Log",
          "Negotiation_Shortlist_Approval","NFA_Log","NFA_Approval_Log",
          "Approval_Log","Spec_Requests","DMS_Documents","Compliance_Log",
          "Process_Events_Log","PO_Reference","SAP_PO_Data","SVJ_Log",
          "Material_References"]:
    c.execute(f"DELETE FROM {t}")

# ─── MATERIAL REFERENCES (key materials) ────────────────────────────────────
mat_refs = [
    ("MREF-001","1000-10042678","Cross_Reference","FAG 6205-2RSR / NTN 6205LLU / Timken 6205-2RS"),
    ("MREF-002","1000-10042678","OEM_Part_Number","CONV-DRV-BRG-6205"),
    ("MREF-003","1000-10042679","Cross_Reference","FAG 22210-E1-K / NTN 22210EK"),
    ("MREF-004","1000-10055003","Drawing_Reference","DRG-VFD-7.5KW-REV03"),
    ("MREF-005","1000-10067001","Drawing_Reference","DRG-HYD-CYL-80x500-REV02"),
    ("MREF-006","1000-10111001","OEM_Part_Number","BF-HAB-BRICK-STD"),
    ("MREF-007","1000-10113001","Drawing_Reference","EAF-ELEC-300-RP-REV01"),
    ("MREF-008","1000-10201001","OEM_Part_Number","PUMP-DRV-15KW-1010"),
    ("MREF-009","1000-10042682","Cross_Reference","SKF 7205 BECBY / FAG 7205B-TVP"),
    ("MREF-010","1000-10067003","Cross_Reference","Parker D1VW020CNVWF / Bosch 4WE6"),
]
c.executemany("INSERT INTO Material_References VALUES (?,?,?,?)", mat_refs)

# ─── MASTER_PR_DATA (26 raw PRs — mix of statuses) ──────────────────────────
prs = [
    # Consolidated ones (back-reference for existing clusters)
    ("PR-2025-00847",10,"1000-10042678","1010",240.0,"NO","Suresh Patil","2025-11-10","2025-12-15","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00848",10,"1000-10042679","1020",50.0,"NO","Manoj Gupta","2025-11-10","2025-12-20","BDG-MRO-SMS-2025","Consolidated"),
    ("PR-2025-00850",10,"1000-10055001","1010",30.0,"NO","Suresh Patil","2025-11-11","2025-12-10","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00851",10,"1000-10055003","1020",4.0,"NO","Ravi Kumar","2025-11-12","2026-01-15","BDG-CAPEX-SMS-2025","Consolidated"),
    ("PR-2025-00852",10,"1000-10067001","1010",6.0,"NO","Dinesh Shah","2025-11-12","2026-01-10","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00860",10,"1000-10078001","1010",15.0,"DR","Suresh Patil","2025-11-14","2025-12-01","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00861",10,"1000-10089001","1030",300.0,"KG","Welding Shop","2025-11-14","2025-12-10","BDG-MRO-RM-2025","Consolidated"),
    ("PR-2025-00862",10,"1000-10111001","1010",2000.0,"NO","BF Ops","2025-11-15","2026-01-15","BDG-RFT-BF-2025","Consolidated"),
    ("PR-2025-00863",10,"1000-10113001","1020",30.0,"NO","EAF Ops","2025-11-16","2025-12-30","BDG-ELC-SMS-2025","Consolidated"),
    ("PR-2025-00864",10,"1000-10099001","1010",100.0,"NO","Workshop Maint","2025-11-17","2025-12-15","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00865",10,"1000-10103001","1010",200.0,"NO","Safety Dept","2025-11-17","2025-12-01","BDG-PPE-2025","Consolidated"),
    ("PR-2025-00866",10,"1000-10093001","1030",40.0,"NO","Rolling Mill","2025-11-18","2025-12-10","BDG-MRO-RM-2025","Consolidated"),
    ("PR-2025-00867",10,"1000-10201001","1020",3.0,"NO","SMS Electrical","2025-11-18","2026-02-28","BDG-CAPEX-SMS-2025","Consolidated"),
    ("PR-2025-00868",10,"1000-10107001","1010",8.0,"NO","BF Piping","2025-11-19","2025-12-20","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00869",10,"1000-10117001","1020",500.0,"M","SMS Electrical","2025-11-19","2026-01-31","BDG-CAPEX-SMS-2025","Consolidated"),
    ("PR-2025-00870",10,"1000-10095001","1010",150.0,"KG","BF Maintenance","2025-11-20","2025-12-10","BDG-MRO-BF-2025","Consolidated"),
    # Still open (for PR.01 agent to consolidate)
    ("PR-2025-00853",10,"1000-10067002","1010",100.0,"M","Dinesh Shah","2025-11-13","2025-12-05","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00854",10,"1000-10078003","1010",8.0,"DR","Suresh Patil","2025-11-13","2025-12-01","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00855",10,"1000-10089002","1020",60.0,"KG","Welding SMS","2025-11-15","2025-12-15","BDG-MRO-SMS-2025","Open"),
    ("PR-2025-00856",10,"1000-10055002","1030",20.0,"NO","Amit Joshi","2025-11-14","2025-12-20","BDG-MRO-RM-2025","Open"),
    ("PR-2025-00857",10,"1000-10042678","1020",120.0,"NO","Manoj Gupta","2025-11-15","2025-12-25","BDG-MRO-SMS-2025","Open"),
    ("PR-2025-00858",10,"1000-10042684","1010",25.0,"NO","BF Drive","2025-11-20","2025-12-20","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00871",10,"1000-10097001","1010",12.0,"NO","BF Pneumatics","2025-11-21","2025-12-30","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00872",10,"1000-10091001","1020",50.0,"NO","SMS Piping","2025-11-21","2025-12-25","BDG-MRO-SMS-2025","Open"),
    ("PR-2025-00873",10,"1000-10109001","1010",500.0,"NO","Workshop","2025-11-22","2025-12-10","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00874",10,"1000-10101003","1020",4.0,"NO","Instrumentation","2025-11-22","2026-01-15","BDG-CAPEX-SMS-2025","Open"),
]
c.executemany("INSERT INTO Master_PR_Data VALUES (?,?,?,?,?,?,?,?,?,?,?)", prs)

# ─── PROCUREMENT_HISTORICAL_PRICING ──────────────────────────────────────────
php = [
    ("PHP-001","1000-10042678","V-20045","2025-09-15",462,200,"INR"),
    ("PHP-002","1000-10042678","V-20046","2025-08-10",470,150,"INR"),
    ("PHP-003","1000-10042678","V-20047","2025-07-20",485,100,"INR"),
    ("PHP-004","1000-10042678","V-20045","2025-03-10",475,180,"INR"),
    ("PHP-005","1000-10042679","V-20045","2025-08-20",2850,40,"INR"),
    ("PHP-006","1000-10042679","V-20046","2025-06-01",2950,30,"INR"),
    ("PHP-007","1000-10055001","V-20048","2025-07-10",1450,25,"INR"),
    ("PHP-008","1000-10055003","V-20049","2025-06-20",28500,3,"INR"),
    ("PHP-009","1000-10067001","V-20050","2025-09-01",18500,4,"INR"),
    ("PHP-010","1000-10078001","V-20051","2025-09-25",14200,8,"INR"),
    ("PHP-011","1000-10089001","V-20052","2025-08-15",2100,150,"INR"),
    ("PHP-012","1000-10111001","V-20074","2025-07-01",465,1000,"INR"),
    ("PHP-013","1000-10113001","V-20076","2025-06-15",8200,20,"INR"),
    ("PHP-014","1000-10099001","V-20058","2025-09-01",465,80,"INR"),
    ("PHP-015","1000-10093001","V-20064","2025-08-01",660,30,"INR"),
    ("PHP-016","1000-10107001","V-20071","2025-07-15",4050,5,"INR"),
    ("PHP-017","1000-10117001","V-20078","2025-08-20",27800,400,"INR"),
    ("PHP-018","1000-10201001","V-20080","2025-05-15",60000,2,"INR"),
    ("PHP-019","1000-10042678","V-20053","2025-06-01",490,50,"INR"),
    ("PHP-020","1000-10103001","V-20061","2025-09-10",360,150,"INR"),
]
c.executemany("INSERT INTO Procurement_Historical_Pricing VALUES (?,?,?,?,?,?,?)", php)

# ─── VENDOR_HISTORY ──────────────────────────────────────────────────────────
vh = [
    ("VH-001","V-20045","1000-10042678","2025-09-15",462,8,18.5,4.5),
    ("VH-002","V-20046","1000-10042678","2025-08-10",470,5,20.0,4.2),
    ("VH-003","V-20047","1000-10042678","2025-07-20",485,3,22.0,4.0),
    ("VH-004","V-20053","1000-10042678","2025-06-01",490,2,25.0,3.5),
    ("VH-005","V-20045","1000-10042679","2025-08-20",2850,4,25.0,4.5),
    ("VH-006","V-20046","1000-10042679","2025-06-01",2950,3,22.0,4.2),
    ("VH-007","V-20048","1000-10055001","2025-07-10",1450,6,12.0,4.8),
    ("VH-008","V-20049","1000-10055003","2025-06-20",28500,2,40.0,4.7),
    ("VH-009","V-20050","1000-10067001","2025-09-01",18500,3,32.0,4.3),
    ("VH-010","V-20051","1000-10078001","2025-09-25",14200,6,5.0,3.8),
    ("VH-011","V-20052","1000-10089001","2025-08-15",2100,10,4.0,4.4),
    ("VH-012","V-20074","1000-10111001","2025-07-01",465,12,18.0,4.6),
    ("VH-013","V-20076","1000-10113001","2025-06-15",8200,8,20.0,4.5),
    ("VH-014","V-20058","1000-10099001","2025-09-01",465,4,12.0,4.0),
    ("VH-015","V-20064","1000-10093001","2025-08-01",660,7,7.0,4.3),
    ("VH-016","V-20071","1000-10107001","2025-07-15",4050,4,12.0,4.4),
    ("VH-017","V-20078","1000-10117001","2025-08-20",27800,3,12.0,4.6),
    ("VH-018","V-20080","1000-10201001","2025-05-15",60000,2,45.0,4.7),
    ("VH-019","V-20061","1000-10103001","2025-09-10",360,8,4.0,3.8),
    ("VH-020","V-20067","1000-10097001","2025-08-30",4050,5,12.0,4.5),
    ("VH-021","V-20062","1000-10091001","2025-09-20",1800,4,12.0,4.3),
    ("VH-022","V-20069","1000-10101003","2025-08-01",8300,3,18.0,4.8),
    ("VH-023","V-20077","1000-10115001","2025-09-05",7900,6,5.0,4.2),
    ("VH-024","V-20073","1000-10109001","2025-09-15",265,12,3.0,4.4),
]
c.executemany("INSERT INTO Vendor_History VALUES (?,?,?,?,?,?,?,?)", vh)

# ─── CONSOLIDATED_PRs — 16 clusters at 8 different pipeline stages ────────────
# fmt: (cluster_id, pr_number, mat_code, mat_group, description, specs, qty, uom,
#        uom_base, total_val, currency, plant, cost_center, capex_opex, proc_cat,
#        pr_status, buyer, payment_terms, del_date, rfq_id, nfa_status,
#        repeat_emg, budget_ovr, created_at, buyer_assigned_at,
#        comm_terms_at, rfq_gen_at, rfq_approved_at, rfq_dispatched_at,
#        nfa_approved_at, po_created_at, closed_at)

def cl(cid,pr,mat,grp,desc,specs,qty,uom,val,plant,cc,cx,buyer,pay,dld,rfq_id,
        nfa_st,status,b_at,ct_at,rg_at,ra_at,rd_at,na_at,po_at,cl_at,
        repeat=0,budget=0,created="2025-11-14 09:00:00"):
    return (cid,pr,mat,grp,desc,specs,qty,uom,uom,val,"INR",plant,cc,cx,"Supply",
            status,buyer,pay,dld,rfq_id,nfa_st,repeat,budget,created,
            b_at,ct_at,rg_at,ra_at,rd_at,na_at,po_at,cl_at)

clusters = [
    # ── STAGE 8: CLOSED (PO created + vendor acknowledged) ──
    cl("CL-2025-00847-01","PR-2025-00847","1000-10042678","MRO-BRG",
       "Deep Groove Ball Bearing 6205-2RS — Conveyor Drive BF Plant",
       "SKF/FAG 6205-2RS | ID:25mm OD:52mm Width:15mm | C3 clearance | Grease-lubricated",
       240,"NO",117600,"1010","CC-1010-BF-MAINT","OPEX",
       "ramesh.kumar@jswsteel.in","Net 45 days from GRN","2025-12-15","RFQ-2025-00289",
       "Approved","NFA_Approved",
       "2025-11-14 11:45:00","2025-11-17 16:20:00","2025-11-18 10:00:00",
       "2025-11-18 22:10:00","2025-11-19 08:05:00","2025-12-02 14:30:00",
       "2025-12-03 10:00:00",None),

    # ── STAGE 7: NFA APPROVED (ready for PO) ──
    cl("CL-2025-00862-01","PR-2025-00862","1000-10111001","MRO-RFT",
       "High Alumina Brick 70% Al2O3 — BF Lining Maintenance",
       "IS:8 Type — 70% Al2O3 | Size 230x114x65mm | Cold Crush >50 N/mm2 | FeO<1%",
       2000,"NO",960000,"1010","CC-1010-BF-RFTY","OPEX",
       "karthik.rajan@jswsteel.in","Net 30 days from GRN","2026-01-15","RFQ-2025-00294",
       "Approved","NFA_Approved",
       "2025-11-15 12:00:00","2025-11-18 14:00:00","2025-11-20 09:00:00",
       "2025-11-20 16:00:00","2025-11-21 07:30:00","2025-11-30 16:00:00",
       None,None),

    # ── STAGE 6: NFA UNDER APPROVAL ──
    cl("CL-2025-00863-01","PR-2025-00863","1000-10113001","MRO-ELC",
       "Carbon Electrode 300mm x 1800mm RP Grade — EAF SMS",
       "RP Grade | 300mm dia | 1800mm length | Flex Res <6 μΩm | Apparent Density >1.54",
       30,"NO",255000,"1020","CC-1020-SMS-EAF","OPEX",
       "karthik.rajan@jswsteel.in","Net 30 days from GRN","2025-12-30","RFQ-2025-00295",
       "Draft","Under_NFA_Approval",
       "2025-11-16 10:00:00","2025-11-19 11:00:00","2025-11-20 15:00:00",
       "2025-11-21 09:00:00","2025-11-22 08:00:00","2025-12-01 14:00:00",
       None,None),

    # ── STAGE 5: TECHNO-COMMERCIAL COMPARISON (evaluation complete) ──
    cl("CL-2025-00848-01","PR-2025-00848","1000-10042679","MRO-BRG",
       "Spherical Roller Bearing 22210 EK — SMS Caster Drive",
       "SKF 22210 EK | Bore:50mm OD:90mm Width:23mm | Tapered bore | Dynamic load 65kN",
       50,"NO",142500,"1020","CC-1020-SMS-MAINT","OPEX",
       "ramesh.kumar@jswsteel.in","Net 30 days from GRN","2025-12-20","RFQ-2025-00290",
       None,"RFQ_Evaluation",
       "2025-11-15 14:00:00","2025-11-18 09:00:00","2025-11-19 11:00:00",
       "2025-11-19 18:00:00","2025-11-20 08:00:00",None,None,None),

    cl("CL-2025-00864-01","PR-2025-00864","1000-10099001","MRO-FLT",
       "Oil Filter Element LF3349 — Workshop Maintenance",
       "Fleetguard equiv LF3349 | Micron: 20 | Bypass valve: 3.5 bar | Thread: M27x2",
       100,"NO",48000,"1010","CC-1010-BF-MAINT","OPEX",
       "priya.sharma@jswsteel.in","Net 30 days from GRN","2025-12-15","RFQ-2025-00296",
       None,"RFQ_Evaluation",
       "2025-11-17 13:00:00","2025-11-19 10:00:00","2025-11-20 12:00:00",
       "2025-11-21 17:00:00","2025-11-22 07:30:00",None,None,None),

    # ── STAGE 4: RFQ DISPATCHED (awaiting vendor submissions) ──
    cl("CL-2025-00850-01","PR-2025-00850","1000-10055001","MRO-ELE",
       "Contactor 3-Pole 25A 240V AC — BF Electrical Panel",
       "Schneider LC1D25M7 or equiv | 3P | 25A | 240V AC coil | IP20",
       30,"NO",43500,"1010","CC-1010-BF-ELEC","OPEX",
       "priya.sharma@jswsteel.in","Net 30 days from GRN","2025-12-10","RFQ-2025-00291",
       None,"RFQ_Dispatched",
       "2025-11-16 11:00:00","2025-11-18 14:00:00","2025-11-20 09:00:00",
       "2025-11-20 16:00:00","2025-11-21 08:00:00",None,None,None),

    cl("CL-2025-00865-01","PR-2025-00865","1000-10103001","MRO-PPE",
       "Safety Helmet Type 1 HDPE Yellow — BF Safety",
       "IS 2925 certified | HDPE construction | 6-point suspension | Chin strap",
       200,"NO",76000,"1010","CC-1010-BF-SAFE","OPEX",
       "deepika.nair@jswsteel.in","Net 30 days from GRN","2025-12-01","RFQ-2025-00297",
       None,"RFQ_Dispatched",
       "2025-11-17 14:00:00","2025-11-19 12:00:00","2025-11-21 10:00:00",
       "2025-11-21 18:00:00","2025-11-22 08:00:00",None,None,None),

    cl("CL-2025-00866-01","PR-2025-00866","1000-10093001","MRO-BLT",
       "V-Belt B-75 — Rolling Mill Drive",
       "ISO 4184 B-75 | Pitch: 1905mm | Width: 17mm | Classical V profile",
       40,"NO",27200,"1030","CC-1030-RM-MAINT","OPEX",
       "anita.singh@jswsteel.in","Net 30 days from GRN","2025-12-10","RFQ-2025-00298",
       None,"RFQ_Dispatched",
       "2025-11-18 10:00:00","2025-11-20 11:00:00","2025-11-22 09:00:00",
       "2025-11-22 17:00:00","2025-11-23 07:30:00",None,None,None),

    # ── STAGE 3: RFQ GENERATED / PENDING APPROVAL ──
    cl("CL-2025-00860-01","PR-2025-00860","1000-10078001","MRO-LUB",
       "Servo 68 Hydraulic Oil 210L Drum — BF Hydraulic System",
       "ISO VG 68 | Antiwear type | Viscosity index >95 | Flash point >200°C | 210L MS drum",
       15,"DR",213000,"1010","CC-1010-BF-HYD","OPEX",
       "sneha.patil@jswsteel.in","Net 45 days from GRN","2025-12-01","RFQ-2025-00292",
       None,"RFQ_Generated",
       "2025-11-14 12:00:00","2025-11-17 15:00:00","2025-11-19 14:00:00",
       None,None,None,None,None),

    cl("CL-2025-00868-01","PR-2025-00868","1000-10107001","MRO-VLV",
       "Gate Valve 2in 150# CS — BF Piping",
       "API 600 | 2in | Class 150 | Carbon Steel A216 WCB | RF flanged | Full port",
       8,"NO",33600,"1010","CC-1010-BF-PIPE","OPEX",
       "sanjay.verma@jswsteel.in","Net 30 days from GRN","2025-12-20","RFQ-2025-00299",
       None,"RFQ_Generated",
       "2025-11-19 10:00:00","2025-11-21 14:00:00","2025-11-23 10:00:00",
       None,None,None,None,None),

    # ── STAGE 2: BUYER ASSIGNED / COMM TERMS PENDING ──
    cl("CL-2025-00851-01","PR-2025-00851","1000-10055003","MRO-ELE",
       "VFD Drive 7.5kW 3-Phase 415V — SMS Rolling Mill",
       "ABB ACS580 or Siemens G120 | 7.5kW | 3-Phase 415V | IP55 | Modbus RTU",
       4,"NO",114000,"1020","CC-1020-SMS-ELEC","CAPEX",
       "anil.deshmukh@jswsteel.in",None,"2026-01-15",None,None,"Buyer_Assigned",
       "2025-11-17 14:00:00",None,None,None,None,None,None,None),

    cl("CL-2025-00867-01","PR-2025-00867","1000-10201001","CAP-MOT",
       "TEFC Motor 15kW 4-Pole 415V IE3 — SMS Conveyor",
       "IS 12615 IE3 | 15kW | 4-Pole | 415V 50Hz | Frame D180M | IP55 | F-class insulation",
       3,"NO",186000,"1020","CC-1020-SMS-CONV","CAPEX",
       "anil.deshmukh@jswsteel.in",None,"2026-02-28",None,None,"Buyer_Assigned",
       "2025-11-18 15:00:00",None,None,None,None,None,None,None),

    cl("CL-2025-00861-01","PR-2025-00861","1000-10089001","MRO-WLD",
       "Welding Rod E6013 3.15mm 25kg — Rolling Mill Welding Shop",
       "IS 814 E6013 | Dia 3.15mm | Tensile strength >430 N/mm2 | All position",
       300,"KG",630000,"1030","CC-1030-RM-WLD","OPEX",
       "sneha.patil@jswsteel.in",None,"2025-12-10",None,None,"Buyer_Assigned",
       "2025-11-14 13:00:00",None,None,None,None,None,None,None),

    # ── STAGE 1: SPECS READY / PENDING VENDOR SHORTLISTING ──
    cl("CL-2025-00852-01","PR-2025-00852","1000-10067001","MRO-HYD",
       "Hydraulic Cylinder 80mm Bore 500mm Stroke — BF Charging Machine",
       "Bosch Rexroth CDT3 or equiv | 80mm bore | 500mm stroke | 250 bar | Trunnion mount",
       6,"NO",111000,"1010","CC-1010-BF-HYD","OPEX",
       "sanjay.verma@jswsteel.in",None,"2026-01-10",None,None,"Specs_Ready",
       "2025-11-18 09:00:00",None,None,None,None,None,None,None),

    cl("CL-2025-00869-01","PR-2025-00869","1000-10117001","MRO-CAB",
       "Power Cable 4-Core 16mm2 XLPE/SWA 100m — SMS Electrical",
       "IS 7098 Pt2 | 4Cx16mm2 | 1.1kV | XLPE insulation | SWA | PVC outer sheath",
       500,"M",14250000,"1020","CC-1020-SMS-ELEC","CAPEX",
       "anil.deshmukh@jswsteel.in",None,"2026-01-31",None,None,"Specs_Ready",
       "2025-11-19 11:00:00",None,None,None,None,None,None,None),

    # ── STAGE 0: NEW / JUST CONSOLIDATED ──
    cl("CL-2025-00870-01","PR-2025-00870","1000-10095001","MRO-FAS",
       "HT Bolt M20x80 8.8 Grade — BF General Maintenance",
       "IS 1364 | M20x80 | Grade 8.8 | Hot-dip galvanised | Hex head full thread",
       150,"KG",27000,"1010","CC-1010-BF-MAINT","OPEX",
       None,None,"2025-12-10",None,None,"New",
       None,None,None,None,None,None,None,None),
]
c.executemany("INSERT INTO Consolidated_PRs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", clusters)

conn.commit()
print("=== PART 3 VERIFICATION ===")
for t,lbl in [("Material_References","Material Refs"),("Master_PR_Data","Master PRs"),
              ("Procurement_Historical_Pricing","Historical Pricing"),
              ("Vendor_History","Vendor History"),("Consolidated_PRs","Clusters")]:
    n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {lbl:30s}: {n}")

# stage breakdown
stages = c.execute("SELECT PR_Status, COUNT(*) FROM Consolidated_PRs GROUP BY PR_Status ORDER BY PR_Status").fetchall()
print("\n  Pipeline stage distribution:")
for s,n in stages:
    print(f"    {s:30s}: {n}")

print(f"\n  Open PRs for PR.01 to process: {c.execute('SELECT COUNT(*) FROM Master_PR_Data WHERE PR_Status=?',('Open',)).fetchone()[0]}")
conn.close()
print("✅ Part 3 complete")
