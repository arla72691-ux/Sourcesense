"""Part 2: Vendors (38), Buyers (10), Designations, DOP 4-level, UOM, Onboarding."""
import sqlite3
from datetime import datetime

conn = sqlite3.connect("s2c_sourcesense.db")
conn.execute("PRAGMA foreign_keys = OFF")
c = conn.cursor()

for t in ["Monthly_Performance","Supplier_Master","Vendor_History",
          "Onboarding_Tracker","Vendor_Shortlist","NFA_Approval_Log",
          "NFA_Log","Negotiation_Shortlist_Approval","Negotiation_Intelligence_Log",
          "Compliance_Log","Approval_Log","RFQ_Overall_Evaluations",
          "RFQ_Comm_Evaluations","RFQ_Tech_Evaluations","RFQ_Submissions",
          "RFQ_Dispatch_Log","Spec_Requests","RFQ_Log",
          "Process_Events_Log","DMS_Documents","PO_Reference","SAP_PO_Data",
          "SVJ_Log","Buyer_Master","Designations_Master","DOP","UOM_Conversion"]:
    c.execute(f"DELETE FROM {t}")

# ─── VENDOR_MASTER (38 vendors) ─────────────────────────────────────────────
vendors = [
    # Bearings
    ("V-20045","SKF India Limited","India","27AABCS1234M1ZV","AABCS1234M",None,None,0,"Active"),
    ("V-20046","NTN Bearing India Pvt Ltd","India","27AABCN5678M1ZV","AABCN5678M",None,None,0,"Active"),
    ("V-20047","Timken India Limited","India","27AABCT9012M1ZV","AABCT9012M",None,None,0,"Active"),
    ("V-20054","Precision Bearings India Pvt Ltd","India","27AABCPB234M1ZV","AABCPB234M","MH20D0005678","Small",0,"Active"),
    ("V-20055","FAG Bearings India Ltd","India","27AABCFAG56M1ZV","AABCFAG56M",None,None,0,"Active"),
    # Electrical
    ("V-20048","Schneider Electric India","India","27AABCSE345M1ZV","AABCSE345M",None,None,0,"Active"),
    ("V-20049","ABB India Limited","India","27AABCAB678M1ZV","AABCAB678M",None,None,0,"Active"),
    ("V-20056","Siemens India Limited","India","27AABCSI890M1ZV","AABCSI890M",None,None,0,"Active"),
    ("V-20082","Rockwell Automation India","India","27AABCRA123M1ZV","AABCRA123M",None,None,0,"Active"),
    # Hydraulics
    ("V-20050","Bosch Rexroth India","India","27AABCBR901M1ZV","AABCBR901M",None,None,0,"Active"),
    ("V-20057","Parker Hannifin India Pvt Ltd","India","27AABCPH234M1ZV","AABCPH234M",None,None,0,"Active"),
    ("V-20058","Donaldson India Filter Systems","India","27AABCD5678M1ZV","AABCD5678M",None,None,0,"Active"),
    # Lubricants
    ("V-20051","Indian Oil Corporation Ltd — Lubes","India","27AABCI1234M1ZV","AABCI1234M",None,None,0,"Active"),
    ("V-20059","3M India Limited — Speciality","India","27AABC3M567M1ZV","AABC3M567M",None,None,0,"Active"),
    # Welding
    ("V-20052","ESAB India Limited","India","27AABCES567M1ZV","AABCES567M",None,None,0,"Active"),
    ("V-20060","INOX Air Products Pvt Ltd","India","27AABCIN890M1ZV","AABCIN890M",None,None,0,"Active"),
    ("V-20061","Mallcom India Ltd (PPE)","India","27AABCML123M1ZV","AABCML123M","MH20D0008901","Small",0,"Active"),
    # Gaskets & Seals
    ("V-20062","Garlock India Pvt Ltd","India","27AABCGL456M1ZV","AABCGL456M",None,None,0,"Active"),
    ("V-20063","ITW India Pvt Ltd","India","27AABCIT789M1ZV","AABCIT789M",None,None,0,"Active"),
    # Belts & Couplings
    ("V-20064","Gates India Pvt Ltd","India","27AABCGI012M1ZV","AABCGI012M",None,None,0,"Active"),
    ("V-20065","Fenner India Pvt Ltd","India","27AABCFE345M1ZV","AABCFE345M","MH20D0012345","Micro",0,"Active"),
    # Fasteners (MSME)
    ("V-20053","Fastenings & MRO Solutions Pvt Ltd","India","27AABCF8901M1ZV","AABCF8901M","MH20D0001234","Micro",0,"Active"),
    ("V-20066","Sundaram Fasteners Limited","India","27AABCSF678M1ZV","AABCSF678M",None,None,0,"Active"),
    # Pneumatics
    ("V-20067","SMC Pneumatics India Pvt Ltd","India","27AABCSMC90M1ZV","AABCSMC90M",None,None,0,"Active"),
    ("V-20068","Alfa Laval India Ltd (filtration)","India","27AABCAL123M1ZV","AABCAL123M",None,None,0,"Active"),
    # Instrumentation
    ("V-20069","Endress+Hauser India Pvt Ltd","India","27AABCEH456M1ZV","AABCEH456M",None,None,0,"Active"),
    # Pumps
    ("V-20070","KSB Pumps Limited","India","27AABCKS789M1ZV","AABCKS789M",None,None,0,"Active"),
    # Valves
    ("V-20071","Forbes Marshall Pvt Ltd","India","27AABCFM012M1ZV","AABCFM012M",None,None,0,"Active"),
    ("V-20072","Duriron India Pvt Ltd","India","27AABCDU345M1ZV","AABCDU345M",None,None,0,"Active"),
    # Abrasives
    ("V-20073","Saint-Gobain Abrasives India","India","27AABCSG678M1ZV","AABCSG678M",None,None,0,"Active"),
    # Refractories
    ("V-20074","IFGL Refractories Ltd","India","27AABCIF901M1ZV","AABCIF901M",None,None,0,"Active"),
    ("V-20075","Calderys India Refractories","India","27AABCCA234M1ZV","AABCCA234M",None,None,0,"Active"),
    # Carbon electrodes
    ("V-20076","HEG Limited (Carbon Electrodes)","India","27AABCHE567M1ZV","AABCHE567M",None,None,0,"Active"),
    # Structural / Steel
    ("V-20077","Tata Steel Processing & Dist","India","27AABCTS890M1ZV","AABCTS890M",None,None,0,"Active"),
    # Cables
    ("V-20078","Polycab India Limited","India","27AABCPO123M1ZV","AABCPO123M",None,None,0,"Active"),
    ("V-20079","Finolex Cables Ltd","India","27AABCFI456M1ZV","AABCFI456M","MH20D0019999","Small",0,"Active"),
    # Motors
    ("V-20080","BHEL India — Motors Division","India","27AABCBH789M1ZV","AABCBH789M",None,None,0,"Active"),
    # Transformers/MCC
    ("V-20081","Voltamp Transformers Ltd","India","27AABCVO012M1ZV","AABCVO012M",None,None,0,"Active"),
    # Compressors
    ("V-20083","Atlas Copco India Pvt Ltd","India","27AABCAC345M1ZV","AABCAC345M",None,None,0,"Active"),
    # Services
    ("V-20084","Reliability Maintenance Services","India","27AABCRM678M1ZV","AABCRM678M","MH20D0023456","Small",0,"Active"),
    ("V-20085","Larsen & Toubro Industrial Svcs","India","27AABCLT901M1ZV","AABCLT901M",None,None,0,"Active"),
    ("V-20086","Gammon India Ltd — Civil","India","27AABCGAM34M1ZV","AABCGAM34M",None,None,0,"Active"),
    ("V-20087","VRL Logistics Limited","India","27AABCVR567M1ZV","AABCVR567M",None,None,0,"Active"),
    # Chemicals
    ("V-20088","BASF India Limited","India","27AABCBA890M1ZV","AABCBA890M",None,None,0,"Active"),
    # One blacklisted for CTRL-007 testing
    ("V-20099","Blacklisted Vendor Test Co","India","27AABCBV111M1ZV","AABCBV111M",None,None,1,"Inactive"),
]
c.executemany("INSERT OR REPLACE INTO Vendor_Master VALUES (?,?,?,?,?,?,?,?,?)", vendors)

# ─── SUPPLIER_MASTER (scores for all 44 vendors) ─────────────────────────────
scores = {
    "V-20045":88.5,"V-20046":83.0,"V-20047":80.5,"V-20054":69.0,"V-20055":85.0,
    "V-20048":91.5,"V-20049":89.0,"V-20056":87.5,"V-20082":82.0,
    "V-20050":85.5,"V-20057":86.0,"V-20058":78.0,
    "V-20051":76.5,"V-20059":74.0,
    "V-20052":84.0,"V-20060":80.0,"V-20061":72.5,
    "V-20062":83.5,"V-20063":70.0,
    "V-20064":86.5,"V-20065":71.0,
    "V-20053":73.5,"V-20066":88.0,
    "V-20067":90.0,"V-20068":77.0,
    "V-20069":92.0,
    "V-20070":85.0,
    "V-20071":84.5,"V-20072":78.5,
    "V-20073":87.0,
    "V-20074":89.5,"V-20075":80.0,
    "V-20076":88.0,
    "V-20077":82.5,
    "V-20078":90.5,"V-20079":73.0,
    "V-20080":86.0,
    "V-20081":84.0,
    "V-20083":91.0,
    "V-20084":75.0,"V-20085":88.5,"V-20086":78.0,"V-20087":81.0,
    "V-20088":85.5,
}
capa = {"V-20054":"2025-11-30","V-20065":"2025-12-15","V-20063":"2026-01-15"}
supplier_rows = [(v,s,"Active","2025-10-31",capa.get(v)) for v,s in scores.items()]
c.executemany("INSERT OR REPLACE INTO Supplier_Master VALUES (?,?,?,?,?)", supplier_rows)

# ─── MONTHLY PERFORMANCE (last 4 months for all vendors) ─────────────────────
perf_base = {
    "V-20045":(0,100.0),"V-20046":(1,97.5),"V-20047":(0,93.0),"V-20054":(2,78.0),
    "V-20055":(0,98.0),"V-20048":(0,100.0),"V-20049":(0,99.0),"V-20056":(0,97.0),
    "V-20050":(1,92.0),"V-20057":(0,95.0),"V-20058":(0,88.0),"V-20051":(1,87.0),
    "V-20059":(0,80.0),"V-20052":(0,96.0),"V-20060":(0,92.0),"V-20061":(1,85.0),
    "V-20062":(0,94.0),"V-20063":(2,72.0),"V-20064":(0,97.0),"V-20065":(1,75.0),
    "V-20053":(1,82.0),"V-20066":(0,95.0),"V-20067":(0,100.0),"V-20068":(0,85.0),
    "V-20069":(0,98.0),"V-20070":(0,91.0),"V-20071":(0,93.0),"V-20072":(1,88.0),
    "V-20073":(0,96.0),"V-20074":(0,98.0),"V-20075":(1,86.0),"V-20076":(0,95.0),
    "V-20077":(0,89.0),"V-20078":(0,99.0),"V-20079":(1,78.0),"V-20080":(0,92.0),
    "V-20081":(0,88.0),"V-20082":(0,90.0),"V-20083":(0,97.0),"V-20084":(1,80.0),
    "V-20085":(0,94.0),"V-20086":(1,82.0),"V-20087":(0,87.0),"V-20088":(0,91.0),
}
mp_rows = []
for v,(qi,otp) in perf_base.items():
    for mo,yr in [(7,2025),(8,2025),(9,2025),(10,2025)]:
        mp_rows.append((v,mo,yr,qi if mo==10 else max(0,qi-1),otp))
c.executemany("INSERT OR REPLACE INTO Monthly_Performance VALUES (?,?,?,?,?)", mp_rows)

# ─── ONBOARDING_TRACKER (all MSME vendors + a few recent ones) ───────────────
onb_rows = [
    ("ONB-2025-00089","27AABCF8901M1ZV",1,1,"Approved","2025-10-10 14:00:00"),
    ("ONB-2025-00090","27AABCPB234M1ZV",1,1,"Approved","2025-10-15 10:00:00"),
    ("ONB-2025-00091","27AABCS1234M1ZV",1,1,"Approved","2022-03-01 09:00:00"),
    ("ONB-2025-00092","27AABCFE345M1ZV",1,1,"Approved","2025-09-20 11:00:00"),
    ("ONB-2025-00093","27AABCML123M1ZV",1,1,"Approved","2025-08-15 14:00:00"),
    ("ONB-2025-00094","27AABCRM678M1ZV",1,1,"Approved","2025-07-01 09:00:00"),
    ("ONB-2025-00095","27AABCFI456M1ZV",1,1,"Approved","2025-09-01 09:00:00"),
    ("ONB-2025-00096","27AABCBV111M1ZV",0,0,"Rejected","2025-01-15 09:00:00"),
]
c.executemany("INSERT OR REPLACE INTO Onboarding_Tracker VALUES (?,?,?,?,?,?)", onb_rows)

# ─── DESIGNATIONS_MASTER (proper 4-level + CFO for above-LPP) ────────────────
des_rows = [
    ("DES-L1-HOD-MRO","Vikram Singh","vikram.singh@jswsteel.in"),
    ("DES-L1-MGR-MRO","Anjali Mehta","anjali.mehta@jswsteel.in"),
    ("DES-L2-GM-PROC","Rajesh Iyer","rajesh.iyer@jswsteel.in"),
    ("DES-L3-VP-SCM","Sunil Kapoor","sunil.kapoor@jswsteel.in"),
    ("DES-L4-CFO","Meena Reddy","meena.reddy@jswsteel.in"),
    ("DES-L4-MD","Arjun Nair","arjun.nair@jswsteel.in"),
    ("DES-L1-HOD-CAP","Pradeep Kulkarni","pradeep.kulkarni@jswsteel.in"),
    ("DES-L1-MGR-CAP","Shalini Rao","shalini.rao@jswsteel.in"),
]
c.executemany("INSERT OR REPLACE INTO Designations_Master VALUES (?,?,?)", des_rows)

# ─── DOP — 4 clear levels ─────────────────────────────────────────────────────
# L1 ≤ 25 Lakhs   → HOD / Manager (day-to-day procurement)
# L2 25L – 2.5Cr  → GM Procurement
# L3 2.5Cr – 25Cr → VP SCM
# L4 > 25Cr       → CFO + MD
c.execute("DELETE FROM DOP")
dop_rows = [
    ("DOP-L1-SUPPLY",       0,    2500000, 1, "DES-L1-HOD-MRO"),
    ("DOP-L2-SUPPLY", 2500001,   25000000, 2, "DES-L2-GM-PROC"),
    ("DOP-L3-SUPPLY",25000001,  250000000, 3, "DES-L3-VP-SCM"),
    ("DOP-L4-SUPPLY",250000001,9999999999, 4, "DES-L4-CFO"),
    # Capital goods get separate DOP with lower thresholds for faster approval
    ("DOP-L1-CAPITAL",       0,   5000000, 1, "DES-L1-HOD-CAP"),
    ("DOP-L2-CAPITAL", 5000001,  50000000, 2, "DES-L2-GM-PROC"),
    ("DOP-L3-CAPITAL",50000001, 500000000, 3, "DES-L3-VP-SCM"),
    ("DOP-L4-CAPITAL",500000001,9999999999,4, "DES-L4-CFO"),
]
c.executemany("INSERT OR REPLACE INTO DOP VALUES (?,?,?,?,?)", dop_rows)

# ─── BUYER_MASTER (10 buyers) ─────────────────────────────────────────────────
buyers = [
    ("BUY-1001","JSW-EMP-04521","Ramesh Kumar","ramesh.kumar@jswsteel.in","+91-9876543210",
     "Procurement — MRO","Senior Buyer",
     "MRO-BRG,MRO-ELE,MRO-HYD,MRO-LUB,MRO-WLD","Supply",5000000,8,15,
     "vikram.singh@jswsteel.in","Active","2023-04-01 09:00:00","2025-11-14 11:45:00"),
    ("BUY-1002","JSW-EMP-04522","Priya Sharma","priya.sharma@jswsteel.in","+91-9876543211",
     "Procurement — MRO","Buyer",
     "MRO-BRG,MRO-ELE,MRO-FLT,MRO-INS","Supply",2000000,6,15,
     "ramesh.kumar@jswsteel.in","Active","2023-06-15 09:00:00","2025-11-10 14:00:00"),
    ("BUY-1003","JSW-EMP-04523","Anil Deshmukh","anil.deshmukh@jswsteel.in","+91-9876543212",
     "Procurement — Capital","Senior Buyer",
     "CAP-MOT,CAP-TRF,CAP-PMP,MRO-ELE","Capital",20000000,5,12,
     "vikram.singh@jswsteel.in","Active","2022-01-10 09:00:00","2025-10-30 09:00:00"),
    ("BUY-1004","JSW-EMP-04524","Sneha Patil","sneha.patil@jswsteel.in","+91-9876543213",
     "Procurement — MRO","Junior Buyer",
     "MRO-LUB,MRO-WLD,MRO-GRD,MRO-ELC","Supply",1000000,4,15,
     "ramesh.kumar@jswsteel.in","Active","2024-08-01 09:00:00","2025-11-12 16:00:00"),
    ("BUY-1005","JSW-EMP-04525","Karthik Rajan","karthik.rajan@jswsteel.in","+91-9876543214",
     "Procurement — Refractories","Senior Buyer",
     "MRO-RFT,MRO-CHM,MRO-PLT","Supply",8000000,6,12,
     "vikram.singh@jswsteel.in","Active","2021-09-01 09:00:00","2025-11-01 09:00:00"),
    ("BUY-1006","JSW-EMP-04526","Meghna Joshi","meghna.joshi@jswsteel.in","+91-9876543215",
     "Procurement — MRO","Buyer",
     "MRO-FAS,MRO-GAK,MRO-PNM","Supply",2000000,5,15,
     "ramesh.kumar@jswsteel.in","Active","2023-09-15 09:00:00","2025-11-05 11:00:00"),
    ("BUY-1007","JSW-EMP-04527","Sanjay Verma","sanjay.verma@jswsteel.in","+91-9876543216",
     "Procurement — MRO","Senior Buyer",
     "MRO-PMP,MRO-VLV,MRO-HYD","Supply",6000000,7,12,
     "vikram.singh@jswsteel.in","Active","2022-06-01 09:00:00","2025-11-08 14:00:00"),
    ("BUY-1008","JSW-EMP-04528","Deepika Nair","deepika.nair@jswsteel.in","+91-9876543217",
     "Procurement — MRO","Buyer",
     "MRO-PPE,MRO-CAB,SRV-MNT","Supply",3000000,4,15,
     "ramesh.kumar@jswsteel.in","Active","2024-01-15 09:00:00","2025-11-10 09:00:00"),
    ("BUY-1009","JSW-EMP-04529","Rohit Gupta","rohit.gupta@jswsteel.in","+91-9876543218",
     "Procurement — Capital & Services","Senior Buyer",
     "CAP-PMP,CAP-TRF,SRV-CIV,SRV-TRN","Capital",15000000,3,10,
     "pradeep.kulkarni@jswsteel.in","Active","2022-11-01 09:00:00","2025-10-20 10:00:00"),
    ("BUY-1010","JSW-EMP-04530","Anita Singh","anita.singh@jswsteel.in","+91-9876543219",
     "Procurement — MRO","Junior Buyer",
     "MRO-BLT,MRO-CHM,SRV-TRN","Supply",1500000,3,15,
     "sneha.patil@jswsteel.in","Active","2025-02-01 09:00:00","2025-11-12 15:00:00"),
]
c.executemany("INSERT OR REPLACE INTO Buyer_Master VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", buyers)

# ─── UOM_CONVERSION ───────────────────────────────────────────────────────────
uom_rows = [
    ("DZ","NO",12.0),("GR","NO",144.0),("KG","G",1000.0),("M","MM",1000.0),
    ("L","ML",1000.0),("DR","L",210.0),("SET","NO",1.0),("BOX","NO",100.0),
    ("PKT","NO",10.0),("PAIR","NO",2.0),("CAN","L",20.0),("CYL","KG",1.0),
    ("TIN","G",500.0),("SRV","NO",1.0),("M","CM",100.0),("KG","MG",1000000.0),
    ("NO","NO",1.0),
]
c.executemany("INSERT OR REPLACE INTO UOM_Conversion VALUES (?,?,?)", uom_rows)

conn.commit()

# Verification
print("=== PART 2 VERIFICATION ===")
for t,label in [("Vendor_Master","Vendors"),("Supplier_Master","Supplier Scores"),
                ("Monthly_Performance","Monthly Perf Records"),
                ("Buyer_Master","Buyers"),("Designations_Master","Designations"),
                ("DOP","DOP Tiers"),("Onboarding_Tracker","Onboarding"),
                ("UOM_Conversion","UOM Conversions")]:
    n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {label:30s}: {n}")

conn.close()
print("✅ Part 2 complete")
