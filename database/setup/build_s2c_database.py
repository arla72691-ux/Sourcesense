"""
S2C Sourcesense — Complete SQLite Database Builder
Creates all 24 entities, populates MDM masters, ERP references, and STM transaction data.
Mimics SAP ERP + Ariba Sourcing Tool + PiLog MDM + DMS
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_BUILD_PATH = "/sessions/vibrant-zealous-mccarthy/s2c_sourcesense.db"
DB_FINAL_PATH = "/sessions/vibrant-zealous-mccarthy/mnt/01. Sourcesense jsons/s2c_sourcesense.db"
DB_PATH = DB_BUILD_PATH

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
c = conn.cursor()

# ============================================================================
# PHASE 1: DDL — CREATE ALL 24 TABLES
# ============================================================================

# --- MDM TABLES (8) ---

c.execute("""
CREATE TABLE Material_Master (
    Material_Code       VARCHAR(20) PRIMARY KEY,
    Material_Number     VARCHAR(20),
    Material_Description TEXT NOT NULL,
    Material_Group      VARCHAR(10) NOT NULL,
    Material_Group_Desc VARCHAR(100),
    HSN_SAC_Code        VARCHAR(15),
    Base_UOM            VARCHAR(10) NOT NULL,
    Category            VARCHAR(20) NOT NULL,
    Last_Purchase_Price DECIMAL(15,2),
    LPP_Currency        VARCHAR(5) DEFAULT 'INR',
    LPP_Date            DATE,
    LPP_Vendor_Code     VARCHAR(20),
    Standard_Lead_Time_Days INTEGER,
    Min_Order_Qty       DECIMAL(15,3),
    Safety_Stock        DECIMAL(15,3),
    Reorder_Point       DECIMAL(15,3),
    ABC_Classification  VARCHAR(1),
    Criticality         VARCHAR(10),
    MSDS_Required       BOOLEAN DEFAULT 0,
    Spec_Document_File_ID VARCHAR(50),
    Created_At          DATETIME NOT NULL,
    Updated_At          DATETIME NOT NULL
)""")

c.execute("""
CREATE TABLE Vendor_Master (
    Vendor_Code         VARCHAR(20) PRIMARY KEY,
    Vendor_Name         VARCHAR(200) NOT NULL,
    Country             VARCHAR(50) NOT NULL,
    GSTIN               VARCHAR(20),
    PAN_Number          VARCHAR(15),
    MSME_Number         VARCHAR(30),
    MSME_Category       VARCHAR(20),
    Blacklisted         BOOLEAN DEFAULT 0,
    Active_Status       VARCHAR(15) DEFAULT 'Active'
)""")

c.execute("""
CREATE TABLE Buyer_Master (
    Buyer_ID            VARCHAR(15) PRIMARY KEY,
    Employee_ID         VARCHAR(20) NOT NULL,
    Buyer_Name          VARCHAR(100) NOT NULL,
    Buyer_Email         VARCHAR(100) NOT NULL,
    Buyer_Phone         VARCHAR(20),
    Department          VARCHAR(50) NOT NULL,
    Designation         VARCHAR(100) NOT NULL,
    Material_Group_Codes TEXT NOT NULL,
    Procurement_Category VARCHAR(20) NOT NULL,
    Annual_Spend_Limit  DECIMAL(18,2) NOT NULL,
    Current_Workload    INTEGER DEFAULT 0,
    Max_Workload        INTEGER DEFAULT 15,
    Manager_Email       VARCHAR(100) NOT NULL,
    Active_Status       VARCHAR(15) DEFAULT 'Active',
    Created_At          DATETIME NOT NULL,
    Updated_At          DATETIME NOT NULL
)""")

c.execute("""
CREATE TABLE Supplier_Master (
    Supplier_Code       VARCHAR(20) PRIMARY KEY,
    Overall_Score       DECIMAL(5,2),
    Status              VARCHAR(15) DEFAULT 'Active',
    Last_Evaluation_Date DATE,
    CAPA_Due_Date       DATE,
    FOREIGN KEY (Supplier_Code) REFERENCES Vendor_Master(Vendor_Code)
)""")

c.execute("""
CREATE TABLE Designations_Master (
    Designation_Code    VARCHAR(15) PRIMARY KEY,
    Employee_Name       VARCHAR(100) NOT NULL,
    Employee_Email      VARCHAR(100) NOT NULL
)""")

c.execute("""
CREATE TABLE UOM_Conversion (
    From_UOM            VARCHAR(10) NOT NULL,
    To_UOM_Base         VARCHAR(10) NOT NULL,
    Conversion_Factor   DECIMAL(15,6) NOT NULL,
    PRIMARY KEY (From_UOM, To_UOM_Base)
)""")

c.execute("""
CREATE TABLE Onboarding_Tracker (
    Onboarding_ID       VARCHAR(20) PRIMARY KEY,
    GST_Number          VARCHAR(20) NOT NULL,
    PAN_Valid           BOOLEAN,
    GST_Valid           BOOLEAN,
    Finance_Decision    VARCHAR(10),
    Vendor_Activated_At DATETIME
)""")

c.execute("""
CREATE TABLE Material_References (
    Ref_ID              VARCHAR(20) PRIMARY KEY,
    Material_Code       VARCHAR(20) NOT NULL,
    Ref_Type            VARCHAR(30) NOT NULL,
    Ref_Value           TEXT NOT NULL,
    FOREIGN KEY (Material_Code) REFERENCES Material_Master(Material_Code)
)""")

# --- ERP TABLES (6) ---

c.execute("""
CREATE TABLE Master_PR_Data (
    PR_Number           VARCHAR(20) PRIMARY KEY,
    PR_Line_Item        INTEGER NOT NULL,
    Material_Code       VARCHAR(20) NOT NULL,
    Plant               VARCHAR(10) NOT NULL,
    Quantity            DECIMAL(15,3) NOT NULL,
    UOM                 VARCHAR(10) NOT NULL,
    Requisitioner       VARCHAR(100),
    PR_Date             DATE NOT NULL,
    Delivery_Date       DATE,
    Budget_Code         VARCHAR(20),
    PR_Status           VARCHAR(20) DEFAULT 'Open',
    FOREIGN KEY (Material_Code) REFERENCES Material_Master(Material_Code)
)""")

c.execute("""
CREATE TABLE DOP (
    DOP_ID              VARCHAR(15) PRIMARY KEY,
    Value_Range_Min     DECIMAL(18,2) NOT NULL,
    Value_Range_Max     DECIMAL(18,2) NOT NULL,
    Tier_Level          INTEGER NOT NULL,
    Approver_Designation VARCHAR(50) NOT NULL
)""")

c.execute("""
CREATE TABLE Vendor_History (
    History_ID          VARCHAR(20) PRIMARY KEY,
    Vendor_Code         VARCHAR(20) NOT NULL,
    Material_Code       VARCHAR(20) NOT NULL,
    Last_PO_Date        DATE,
    Last_PO_Price       DECIMAL(15,2),
    Total_POs_12M       INTEGER DEFAULT 0,
    Avg_Delivery_Days   DECIMAL(5,1),
    Quality_Rating      DECIMAL(3,1),
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code),
    FOREIGN KEY (Material_Code) REFERENCES Material_Master(Material_Code)
)""")

c.execute("""
CREATE TABLE Monthly_Performance (
    Supplier_Code       VARCHAR(20) NOT NULL,
    Month               INTEGER NOT NULL,
    Year                INTEGER NOT NULL,
    Quality_Incidents   INTEGER DEFAULT 0,
    Delivery_On_Time_Pct DECIMAL(5,2),
    PRIMARY KEY (Supplier_Code, Month, Year),
    FOREIGN KEY (Supplier_Code) REFERENCES Supplier_Master(Supplier_Code)
)""")

c.execute("""
CREATE TABLE Procurement_Historical_Pricing (
    Pricing_ID          VARCHAR(20) PRIMARY KEY,
    Material_Code       VARCHAR(20) NOT NULL,
    Vendor_Code         VARCHAR(20) NOT NULL,
    PO_Date             DATE NOT NULL,
    Unit_Price          DECIMAL(15,2) NOT NULL,
    Quantity            DECIMAL(15,3),
    Currency            VARCHAR(5) DEFAULT 'INR',
    FOREIGN KEY (Material_Code) REFERENCES Material_Master(Material_Code),
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code)
)""")

c.execute("""
CREATE TABLE SAP_PO_Data (
    SAP_PO_Number       VARCHAR(20) PRIMARY KEY,
    Vendor_Code         VARCHAR(20) NOT NULL,
    Material_Code       VARCHAR(20) NOT NULL,
    Plant               VARCHAR(10),
    Unit_Price          DECIMAL(15,2),
    Quantity            DECIMAL(15,3),
    UOM                 VARCHAR(10),
    PO_Net_Value        DECIMAL(18,2),
    Delivery_Date       DATE,
    Payment_Terms       VARCHAR(50),
    Incoterms           VARCHAR(20),
    PO_Type             VARCHAR(10) DEFAULT 'NB',
    PO_Status           VARCHAR(20) DEFAULT 'Open',
    GRN_Number          VARCHAR(20),
    Invoice_Number      VARCHAR(50),
    Payment_Status      VARCHAR(20) DEFAULT 'Not_Initiated',
    SAP_Created_At      DATETIME,
    Goods_Receipt_Date  DATE,
    Invoice_Date        DATE,
    Payment_Date        DATE,
    Remarks             TEXT,
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code),
    FOREIGN KEY (Material_Code) REFERENCES Material_Master(Material_Code)
)""")

# --- STM TRANSACTION TABLES (17) ---

c.execute("""
CREATE TABLE Consolidated_PRs (
    Consolidation_Cluster_ID VARCHAR(30) PRIMARY KEY,
    PR_Number           VARCHAR(20) NOT NULL,
    Material_Code       VARCHAR(20) NOT NULL,
    Material_Group      VARCHAR(10) NOT NULL,
    Description         TEXT NOT NULL,
    Long_Text_Specifications TEXT,
    Quantity            DECIMAL(15,3) NOT NULL,
    UOM                 VARCHAR(10) NOT NULL,
    UOM_Base            VARCHAR(10) NOT NULL,
    Total_Value         DECIMAL(18,2) NOT NULL,
    Currency            VARCHAR(5) DEFAULT 'INR',
    Plant               VARCHAR(10) NOT NULL,
    Cost_Center         VARCHAR(15),
    Capex_Opex          VARCHAR(10) NOT NULL,
    Procurement_Category VARCHAR(20) NOT NULL,
    PR_Status           VARCHAR(30) NOT NULL DEFAULT 'New',
    Assigned_Buyer      VARCHAR(100),
    Payment_Terms       VARCHAR(50),
    Delivery_Date       DATE,
    RFQ_ID              VARCHAR(20),
    NFA_Status          VARCHAR(20),
    Repeat_Emergency_Flag BOOLEAN DEFAULT 0,
    Budget_Overrun_Flag BOOLEAN DEFAULT 0,
    Created_At          DATETIME NOT NULL,
    Buyer_Assigned_At   DATETIME,
    Comm_Terms_Received_At DATETIME,
    RFQ_Generated_At    DATETIME,
    RFQ_Approved_At     DATETIME,
    RFQ_Dispatched_At   DATETIME,
    NFA_Approved_At     DATETIME,
    PO_Created_At       DATETIME,
    Closed_At           DATETIME,
    FOREIGN KEY (PR_Number) REFERENCES Master_PR_Data(PR_Number),
    FOREIGN KEY (Material_Code) REFERENCES Material_Master(Material_Code)
)""")

c.execute("""
CREATE TABLE RFQ_Log (
    RFQ_ID              VARCHAR(20) PRIMARY KEY,
    Consolidation_Cluster_ID VARCHAR(30) NOT NULL,
    RFQ_Status          VARCHAR(20) DEFAULT 'Draft',
    Evaluation_Criteria TEXT,
    Submission_Deadline DATETIME,
    Created_By          VARCHAR(100),
    Created_At          DATETIME NOT NULL,
    Updated_At          DATETIME,
    FOREIGN KEY (Consolidation_Cluster_ID) REFERENCES Consolidated_PRs(Consolidation_Cluster_ID)
)""")

c.execute("""
CREATE TABLE Vendor_Shortlist (
    Shortlist_ID        VARCHAR(20) PRIMARY KEY,
    RFQ_ID              VARCHAR(20) NOT NULL,
    Vendor_Code         VARCHAR(20) NOT NULL,
    Shortlist_Reason    TEXT,
    Historical_Score    DECIMAL(5,2),
    Added_At            DATETIME NOT NULL,
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID),
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code)
)""")

c.execute("""
CREATE TABLE Spec_Requests (
    Spec_Request_ID     VARCHAR(20) PRIMARY KEY,
    Consolidation_Cluster_ID VARCHAR(30) NOT NULL,
    Requested_From      VARCHAR(100),
    Status              VARCHAR(20) DEFAULT 'Pending',
    File_ID             VARCHAR(50),
    Created_At          DATETIME NOT NULL,
    FOREIGN KEY (Consolidation_Cluster_ID) REFERENCES Consolidated_PRs(Consolidation_Cluster_ID)
)""")

c.execute("""
CREATE TABLE RFQ_Dispatch_Log (
    Dispatch_ID         VARCHAR(20) PRIMARY KEY,
    RFQ_ID              VARCHAR(20) NOT NULL,
    Vendor_Code         VARCHAR(20) NOT NULL,
    Dispatch_Method     VARCHAR(20) DEFAULT 'Email',
    Dispatched_At       DATETIME NOT NULL,
    Delivery_Status     VARCHAR(20) DEFAULT 'Sent',
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID),
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code)
)""")

c.execute("""
CREATE TABLE RFQ_Submissions (
    Submission_ID       VARCHAR(20) PRIMARY KEY,
    RFQ_ID              VARCHAR(20) NOT NULL,
    Vendor_Code         VARCHAR(20) NOT NULL,
    Quoted_Unit_Price   DECIMAL(15,2),
    Lead_Time_Days      INTEGER,
    Submission_File_ID  VARCHAR(50),
    Submitted_At        DATETIME,
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID),
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code)
)""")

c.execute("""
CREATE TABLE RFQ_Tech_Evaluations (
    Tech_Eval_ID        VARCHAR(20) PRIMARY KEY,
    Submission_ID       VARCHAR(20) NOT NULL,
    Tech_Score          DECIMAL(5,2),
    Tech_Remarks        TEXT,
    FOREIGN KEY (Submission_ID) REFERENCES RFQ_Submissions(Submission_ID)
)""")

c.execute("""
CREATE TABLE RFQ_Comm_Evaluations (
    Comm_Eval_ID        VARCHAR(20) PRIMARY KEY,
    Submission_ID       VARCHAR(20) NOT NULL,
    Price_Score         DECIMAL(5,2),
    Payment_Score       DECIMAL(5,2),
    Delivery_Score      DECIMAL(5,2),
    Comm_Remarks        TEXT,
    FOREIGN KEY (Submission_ID) REFERENCES RFQ_Submissions(Submission_ID)
)""")

c.execute("""
CREATE TABLE RFQ_Overall_Evaluations (
    Overall_Eval_ID     VARCHAR(20) PRIMARY KEY,
    Submission_ID       VARCHAR(20) NOT NULL,
    Tech_Weighted_Score DECIMAL(5,2),
    Comm_Weighted_Score DECIMAL(5,2),
    Overall_Score       DECIMAL(5,2),
    FOREIGN KEY (Submission_ID) REFERENCES RFQ_Submissions(Submission_ID)
)""")

c.execute("""
CREATE TABLE NFA_Log (
    NFA_ID              VARCHAR(20) PRIMARY KEY,
    Consolidation_Cluster_ID VARCHAR(30) NOT NULL,
    RFQ_ID              VARCHAR(20),
    Recommended_Vendor  VARCHAR(20),
    Negotiated_Unit_Price DECIMAL(15,2),
    Total_NFA_Value     DECIMAL(18,2),
    Price_Vs_LPP_Status VARCHAR(20),
    Price_Deviation_Pct DECIMAL(5,2),
    Savings_Vs_LPP_Pct  DECIMAL(5,2),
    Price_Justification TEXT,
    NFA_Status          VARCHAR(20) DEFAULT 'Draft',
    NFA_Document_File_ID VARCHAR(50),
    Created_By          VARCHAR(100),
    Created_At          DATETIME NOT NULL,
    Updated_At          DATETIME,
    FOREIGN KEY (Consolidation_Cluster_ID) REFERENCES Consolidated_PRs(Consolidation_Cluster_ID),
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID),
    FOREIGN KEY (Recommended_Vendor) REFERENCES Vendor_Master(Vendor_Code)
)""")

c.execute("""
CREATE TABLE Approval_Log (
    Approval_ID         VARCHAR(20) PRIMARY KEY,
    Entity_Type         VARCHAR(30) NOT NULL,
    Entity_ID           VARCHAR(30) NOT NULL,
    Approver_Email      VARCHAR(100) NOT NULL,
    Approver_Designation VARCHAR(50),
    Decision            VARCHAR(20),
    Comments            TEXT,
    Decided_At          DATETIME
)""")

c.execute("""
CREATE TABLE NFA_Approval_Log (
    NFA_Approval_ID     VARCHAR(20) PRIMARY KEY,
    NFA_ID              VARCHAR(20) NOT NULL,
    Tier_Level          INTEGER NOT NULL,
    Approver_Designation VARCHAR(50),
    Approver_Email      VARCHAR(100),
    Decision            VARCHAR(20),
    Comments            TEXT,
    Decided_At          DATETIME,
    FOREIGN KEY (NFA_ID) REFERENCES NFA_Log(NFA_ID)
)""")

c.execute("""
CREATE TABLE SVJ_Log (
    SVJ_ID              VARCHAR(20) PRIMARY KEY,
    RFQ_ID              VARCHAR(20) NOT NULL,
    Justification_Reason TEXT NOT NULL,
    Supporting_Doc_File_ID VARCHAR(50),
    Approval_Status     VARCHAR(20) DEFAULT 'Pending',
    Created_By          VARCHAR(100),
    Created_At          DATETIME NOT NULL,
    Approved_By         VARCHAR(100),
    Decided_At          DATETIME,
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID)
)""")

c.execute("""
CREATE TABLE PO_Reference (
    PO_Ref_ID           VARCHAR(20) PRIMARY KEY,
    NFA_ID              VARCHAR(20) NOT NULL,
    Consolidation_Cluster_ID VARCHAR(30),
    SAP_PO_Number       VARCHAR(20),
    PO_Document_File_ID VARCHAR(50),
    Vendor_Acknowledged_At DATETIME,
    API_Call_Status      VARCHAR(20) DEFAULT 'Pending',
    Created_By          VARCHAR(100),
    Created_At          DATETIME NOT NULL,
    FOREIGN KEY (NFA_ID) REFERENCES NFA_Log(NFA_ID)
)""")

c.execute("""
CREATE TABLE Negotiation_Intelligence_Log (
    Brief_ID            VARCHAR(20) PRIMARY KEY,
    RFQ_ID              VARCHAR(20) NOT NULL,
    Spend_Analysis      TEXT,
    Market_Research_Summary TEXT,
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID)
)""")

c.execute("""
CREATE TABLE Negotiation_Shortlist_Approval (
    Neg_Approval_ID     VARCHAR(20) PRIMARY KEY,
    RFQ_ID              VARCHAR(20) NOT NULL,
    Vendor_Code         VARCHAR(20) NOT NULL,
    Negotiated_Price    DECIMAL(15,2),
    Approval_Status     VARCHAR(20) DEFAULT 'Pending',
    Approved_By         VARCHAR(100),
    Approved_At         DATETIME,
    FOREIGN KEY (RFQ_ID) REFERENCES RFQ_Log(RFQ_ID),
    FOREIGN KEY (Vendor_Code) REFERENCES Vendor_Master(Vendor_Code)
)""")

# --- DMS TABLE ---

c.execute("""
CREATE TABLE DMS_Documents (
    Document_ID         VARCHAR(50) PRIMARY KEY,
    Document_Type       VARCHAR(30) NOT NULL,
    Entity_Type         VARCHAR(30),
    Entity_ID           VARCHAR(30),
    File_Name           VARCHAR(200) NOT NULL,
    File_Path           TEXT NOT NULL,
    Uploaded_By         VARCHAR(100),
    Uploaded_At         DATETIME NOT NULL,
    File_Size_KB        INTEGER,
    Version             INTEGER DEFAULT 1
)""")

# --- COMPLIANCE TABLE ---

c.execute("""
CREATE TABLE Compliance_Log (
    Compliance_ID       VARCHAR(20) PRIMARY KEY,
    Control_ID          VARCHAR(10) NOT NULL,
    Entity_Type         VARCHAR(30) NOT NULL,
    Entity_ID           VARCHAR(30) NOT NULL,
    Result              VARCHAR(10) NOT NULL,
    Details             TEXT,
    Checked_At          DATETIME NOT NULL,
    Override_By         VARCHAR(100),
    Override_Reason     TEXT
)""")

# --- EVENTS LOG ---

c.execute("""
CREATE TABLE Process_Events_Log (
    Event_ID            VARCHAR(20) PRIMARY KEY,
    Process_ID          VARCHAR(15) NOT NULL,
    Entity_Type         VARCHAR(30),
    Entity_ID           VARCHAR(30),
    Event_Type          VARCHAR(30) NOT NULL,
    Event_Description   TEXT,
    Actor               VARCHAR(100),
    Created_At          DATETIME NOT NULL
)""")

conn.commit()
print("✅ All 27 tables created (24 core + 3 supporting)")

# ============================================================================
# PHASE 2: POPULATE MDM MASTER DATA (8 tables)
# ============================================================================

# --- Material_Master: 15 MRO materials across 5 groups ---
materials = [
    ("1000-10042678","10042678","Deep Groove Ball Bearing 6205-2RS","MRO-BRG","Bearings","84829100","NO","Supply",462.00,"INR","2025-09-15","V-20045",21,50,100,200,"A","Critical",0,"DOC-SPEC-001","2023-01-15 09:00:00","2025-09-15 14:00:00"),
    ("1000-10042679","10042679","Spherical Roller Bearing 22210 EK","MRO-BRG","Bearings","84829100","NO","Supply",2850.00,"INR","2025-08-20","V-20045",28,20,40,80,"A","Critical",0,"DOC-SPEC-002","2023-01-15 09:00:00","2025-08-20 10:00:00"),
    ("1000-10042680","10042680","Tapered Roller Bearing 30206","MRO-BRG","Bearings","84829100","NO","Supply",780.00,"INR","2025-10-01","V-20046",21,30,60,120,"B","High",0,None,"2023-02-01 09:00:00","2025-10-01 11:00:00"),
    ("1000-10055001","10055001","Contactor 3-Pole 25A 240V AC","MRO-ELE","Electrical","85389000","NO","Supply",1450.00,"INR","2025-07-10","V-20048",14,10,20,40,"B","High",0,None,"2023-03-01 09:00:00","2025-07-10 09:00:00"),
    ("1000-10055002","10055002","Thermal Overload Relay 16-25A","MRO-ELE","Electrical","85363000","NO","Supply",890.00,"INR","2025-08-05","V-20048",14,15,30,60,"B","Medium",0,None,"2023-03-01 09:00:00","2025-08-05 11:00:00"),
    ("1000-10055003","10055003","VFD Drive 7.5kW 3-Phase 415V","MRO-ELE","Electrical","85044000","NO","Supply",28500.00,"INR","2025-06-20","V-20049",42,2,4,6,"A","Critical",0,"DOC-SPEC-003","2023-03-15 09:00:00","2025-06-20 14:00:00"),
    ("1000-10067001","10067001","Hydraulic Cylinder 80mm Bore 500mm Stroke","MRO-HYD","Hydraulics","84122100","NO","Supply",18500.00,"INR","2025-09-01","V-20050",35,3,6,10,"A","Critical",0,"DOC-SPEC-004","2023-04-01 09:00:00","2025-09-01 10:00:00"),
    ("1000-10067002","10067002","Hydraulic Hose 1/2in 4000PSI 2M","MRO-HYD","Hydraulics","40094200","M","Supply",650.00,"INR","2025-10-10","V-20050",7,50,100,200,"C","Medium",0,None,"2023-04-01 09:00:00","2025-10-10 09:00:00"),
    ("1000-10078001","10078001","Servo 68 Hydraulic Oil 210L Drum","MRO-LUB","Lubricants","27101990","DR","Supply",14200.00,"INR","2025-09-25","V-20051",7,5,10,15,"B","High",1,None,"2023-05-01 09:00:00","2025-09-25 11:00:00"),
    ("1000-10078002","10078002","EP Grease NLGI-2 15kg Pail","MRO-LUB","Lubricants","27101990","KG","Supply",3800.00,"INR","2025-10-05","V-20051",7,10,20,30,"C","Low",1,None,"2023-05-01 09:00:00","2025-10-05 14:00:00"),
    ("1000-10089001","10089001","Welding Rod E6013 3.15mm 25kg","MRO-WLD","Welding","83111000","KG","Supply",2100.00,"INR","2025-08-15","V-20052",5,20,50,100,"B","Medium",0,None,"2023-06-01 09:00:00","2025-08-15 10:00:00"),
    ("1000-10089002","10089002","MIG Wire ER70S-6 1.2mm 15kg Spool","MRO-WLD","Welding","83111000","KG","Supply",1650.00,"INR","2025-09-10","V-20052",5,15,30,60,"B","Medium",0,None,"2023-06-01 09:00:00","2025-09-10 09:00:00"),
    ("1000-10042681","10042681","Needle Roller Bearing HK2020","MRO-BRG","Bearings","84829100","NO","Supply",320.00,"INR","2025-10-20","V-20047",14,100,200,400,"C","Low",0,None,"2023-07-01 09:00:00","2025-10-20 10:00:00"),
    ("1000-10055004","10055004","MCB 3-Pole 32A C-Curve","MRO-ELE","Electrical","85362000","NO","Supply",560.00,"INR","2025-09-30","V-20048",10,20,40,80,"C","Medium",0,None,"2023-07-15 09:00:00","2025-09-30 11:00:00"),
    ("1000-10067003","10067003","Directional Control Valve 4/3 Way","MRO-HYD","Hydraulics","84812090","NO","Supply",12800.00,"INR","2025-08-25","V-20050",28,2,4,6,"A","High",0,"DOC-SPEC-005","2023-08-01 09:00:00","2025-08-25 14:00:00"),
]
c.executemany("INSERT INTO Material_Master VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", materials)

# --- Vendor_Master: 10 vendors ---
vendors = [
    ("V-20045","SKF India Limited","India","27AABCS1234M1ZV","AABCS1234M",None,None,0,"Active"),
    ("V-20046","NTN Bearing India Pvt Ltd","India","27AABCN5678M1ZV","AABCN5678M",None,None,0,"Active"),
    ("V-20047","Timken India Limited","India","27AABCT9012M1ZV","AABCT9012M",None,None,0,"Active"),
    ("V-20048","Schneider Electric India","India","27AABCSE345M1ZV","AABCSE345M",None,None,0,"Active"),
    ("V-20049","ABB India Limited","India","27AABCAB678M1ZV","AABCAB678M",None,None,0,"Active"),
    ("V-20050","Bosch Rexroth India","India","27AABCBR901M1ZV","AABCBR901M",None,None,0,"Active"),
    ("V-20051","Indian Oil Corporation — Lubes","India","27AABCI1234M1ZV","AABCI1234M",None,None,0,"Active"),
    ("V-20052","ESAB India Limited","India","27AABCES567M1ZV","AABCES567M",None,None,0,"Active"),
    ("V-20053","Fastenings & MRO Solutions Pvt Ltd","India","27AABCF8901M1ZV","AABCF8901M","MH20D0001234","Micro",0,"Active"),
    ("V-20054","Precision Bearings India Pvt Ltd","India","27AABCPB234M1ZV","AABCPB234M","MH20D0005678","Small",0,"Active"),
]
c.executemany("INSERT INTO Vendor_Master VALUES (?,?,?,?,?,?,?,?,?)", vendors)

# --- Buyer_Master: 4 buyers ---
buyers = [
    ("BUY-1001","JSW-EMP-04521","Ramesh Kumar","ramesh.kumar@jswsteel.in","+91-9876543210","Procurement — MRO & Consumables","Senior Buyer","MRO-BRG,MRO-ELE,MRO-HYD,MRO-LUB,MRO-WLD","Supply",5000000.00,8,15,"vikram.singh@jswsteel.in","Active","2023-04-01 09:00:00","2025-11-14 11:45:00"),
    ("BUY-1002","JSW-EMP-04522","Priya Sharma","priya.sharma@jswsteel.in","+91-9876543211","Procurement — MRO & Consumables","Buyer","MRO-BRG,MRO-ELE","Supply",2000000.00,6,15,"ramesh.kumar@jswsteel.in","Active","2023-06-15 09:00:00","2025-11-10 14:00:00"),
    ("BUY-1003","JSW-EMP-04523","Anil Deshmukh","anil.deshmukh@jswsteel.in","+91-9876543212","Procurement — Capital & Projects","Senior Buyer","MRO-HYD,MRO-ELE","Supply",8000000.00,5,12,"vikram.singh@jswsteel.in","Active","2022-01-10 09:00:00","2025-10-30 09:00:00"),
    ("BUY-1004","JSW-EMP-04524","Sneha Patil","sneha.patil@jswsteel.in","+91-9876543213","Procurement — MRO & Consumables","Junior Buyer","MRO-LUB,MRO-WLD","Supply",1000000.00,4,15,"ramesh.kumar@jswsteel.in","Active","2024-08-01 09:00:00","2025-11-12 16:00:00"),
]
c.executemany("INSERT INTO Buyer_Master VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", buyers)

# --- Supplier_Master: ratings for all 10 vendors ---
suppliers = [
    ("V-20045",87.50,"Active","2025-10-31",None),
    ("V-20046",82.00,"Active","2025-10-31",None),
    ("V-20047",79.50,"Active","2025-09-30",None),
    ("V-20048",91.00,"Active","2025-10-31",None),
    ("V-20049",88.50,"Active","2025-10-31",None),
    ("V-20050",85.00,"Active","2025-09-30","2025-12-15"),
    ("V-20051",76.00,"Active","2025-10-31",None),
    ("V-20052",83.50,"Active","2025-09-30",None),
    ("V-20053",72.00,"Active","2025-08-31",None),
    ("V-20054",68.50,"Probation","2025-10-31","2025-11-30"),
]
c.executemany("INSERT INTO Supplier_Master VALUES (?,?,?,?,?)", suppliers)

# --- Designations_Master: approval chain ---
designations = [
    ("DES-SR-BUY-MRO","Vikram Singh","vikram.singh@jswsteel.in"),
    ("DES-MGR-PROC","Anjali Mehta","anjali.mehta@jswsteel.in"),
    ("DES-GM-PROC","Rajesh Iyer","rajesh.iyer@jswsteel.in"),
    ("DES-VP-SCM","Sunil Kapoor","sunil.kapoor@jswsteel.in"),
    ("DES-CFO","Meena Reddy","meena.reddy@jswsteel.in"),
    ("DES-CPO","Arjun Nair","arjun.nair@jswsteel.in"),
]
c.executemany("INSERT INTO Designations_Master VALUES (?,?,?)", designations)

# --- UOM_Conversion ---
uom_conversions = [
    ("DZ","NO",12.0),("GR","NO",144.0),("KG","G",1000.0),("M","MM",1000.0),
    ("L","ML",1000.0),("DR","L",210.0),("SET","NO",1.0),("BOX","NO",100.0),
    ("PKT","NO",10.0),("PAIR","NO",2.0),
]
c.executemany("INSERT INTO UOM_Conversion VALUES (?,?,?)", uom_conversions)

# --- Onboarding_Tracker ---
onboarding = [
    ("ONB-2025-00089","27AABCF8901M1ZV",1,1,"Approved","2025-10-10 14:00:00"),
    ("ONB-2025-00090","27AABCPB234M1ZV",1,1,"Approved","2025-10-15 10:00:00"),
    ("ONB-2025-00091","27AABCS1234M1ZV",1,1,"Approved","2022-03-01 09:00:00"),
]
c.executemany("INSERT INTO Onboarding_Tracker VALUES (?,?,?,?,?,?)", onboarding)

# --- Material_References ---
mat_refs = [
    ("MREF-001","1000-10042678","Cross_Reference","FAG 6205-2RSR / NTN 6205LLU / Timken 6205-2RS"),
    ("MREF-002","1000-10042678","OEM_Part_Number","CONV-DRV-BRG-6205"),
    ("MREF-003","1000-10042679","Cross_Reference","FAG 22210-E1-K / NTN 22210EK"),
    ("MREF-004","1000-10055003","Drawing_Reference","DRG-VFD-7.5KW-REV03"),
    ("MREF-005","1000-10067001","Drawing_Reference","DRG-HYD-CYL-80x500-REV02"),
]
c.executemany("INSERT INTO Material_References VALUES (?,?,?,?)", mat_refs)

conn.commit()
print("✅ MDM master data populated (8 tables)")

# ============================================================================
# PHASE 3: POPULATE ERP REFERENCE DATA (6 tables)
# ============================================================================

# --- DOP: 5 approval tiers ---
dop = [
    ("DOP-JSW-SUPPLY-T1",0,500000,1,"Senior Buyer / Manager — Procurement"),
    ("DOP-JSW-SUPPLY-T2",500001,2000000,2,"GM — Procurement"),
    ("DOP-JSW-SUPPLY-T3",2000001,5000000,3,"VP — Supply Chain"),
    ("DOP-JSW-SUPPLY-T4",5000001,20000000,4,"CFO"),
    ("DOP-JSW-SUPPLY-T5",20000001,999999999,5,"CPO + Board"),
]
c.executemany("INSERT INTO DOP VALUES (?,?,?,?,?)", dop)

# --- Master_PR_Data: 12 raw PRs ---
prs = [
    ("PR-2025-00847",10,"1000-10042678","1010",240.0,"NO","Suresh Patil — BF Maintenance","2025-11-10","2025-12-15","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00848",10,"1000-10042679","1020",50.0,"NO","Manoj Gupta — SMS Maintenance","2025-11-10","2025-12-20","BDG-MRO-SMS-2025","Consolidated"),
    ("PR-2025-00849",10,"1000-10042680","1030",80.0,"NO","Amit Joshi — Rolling Mill","2025-11-11","2025-12-18","BDG-MRO-RM-2025","Consolidated"),
    ("PR-2025-00850",10,"1000-10055001","1010",30.0,"NO","Suresh Patil — BF Maintenance","2025-11-11","2025-12-10","BDG-MRO-BF-2025","Consolidated"),
    ("PR-2025-00851",10,"1000-10055003","1020",4.0,"NO","Ravi Kumar — SMS Electrical","2025-11-12","2026-01-15","BDG-CAPEX-SMS-2025","Consolidated"),
    ("PR-2025-00852",10,"1000-10067001","1010",6.0,"NO","Dinesh Shah — BF Hydraulics","2025-11-12","2026-01-10","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00853",10,"1000-10067002","1010",100.0,"M","Dinesh Shah — BF Hydraulics","2025-11-13","2025-12-05","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00854",10,"1000-10078001","1010",10.0,"DR","Suresh Patil — BF Maintenance","2025-11-13","2025-12-01","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00855",10,"1000-10089001","1010",200.0,"KG","Welding Shop — BF","2025-11-14","2025-12-10","BDG-MRO-BF-2025","Open"),
    ("PR-2025-00856",10,"1000-10055002","1030",20.0,"NO","Amit Joshi — Rolling Mill","2025-11-14","2025-12-20","BDG-MRO-RM-2025","Open"),
    ("PR-2025-00857",10,"1000-10042678","1020",120.0,"NO","Manoj Gupta — SMS","2025-11-15","2025-12-25","BDG-MRO-SMS-2025","Open"),
    ("PR-2025-00858",10,"1000-10089002","1020",60.0,"KG","Welding Shop — SMS","2025-11-15","2025-12-15","BDG-MRO-SMS-2025","Open"),
]
c.executemany("INSERT INTO Master_PR_Data VALUES (?,?,?,?,?,?,?,?,?,?,?)", prs)

# --- Vendor_History ---
vh = [
    ("VH-001","V-20045","1000-10042678","2025-09-15",462.00,8,18.5,4.5),
    ("VH-002","V-20046","1000-10042678","2025-08-10",470.00,5,20.0,4.2),
    ("VH-003","V-20047","1000-10042678","2025-07-20",485.00,3,22.0,4.0),
    ("VH-004","V-20045","1000-10042679","2025-08-20",2850.00,4,25.0,4.5),
    ("VH-005","V-20048","1000-10055001","2025-07-10",1450.00,6,12.0,4.8),
    ("VH-006","V-20049","1000-10055003","2025-06-20",28500.00,2,40.0,4.7),
    ("VH-007","V-20050","1000-10067001","2025-09-01",18500.00,3,32.0,4.3),
    ("VH-008","V-20051","1000-10078001","2025-09-25",14200.00,6,5.0,3.8),
    ("VH-009","V-20052","1000-10089001","2025-08-15",2100.00,10,4.0,4.4),
    ("VH-010","V-20053","1000-10042678","2025-06-01",490.00,2,25.0,3.5),
    ("VH-011","V-20054","1000-10042680","2025-05-15",800.00,2,28.0,3.2),
    ("VH-012","V-20048","1000-10055002","2025-08-05",890.00,4,10.0,4.6),
]
c.executemany("INSERT INTO Vendor_History VALUES (?,?,?,?,?,?,?,?)", vh)

# --- Monthly_Performance (last 3 months for top vendors) ---
mp = [
    ("V-20045",8,2025,0,100.00),("V-20045",9,2025,0,100.00),("V-20045",10,2025,0,100.00),
    ("V-20046",8,2025,1,95.00),("V-20046",9,2025,0,100.00),("V-20046",10,2025,0,97.50),
    ("V-20047",8,2025,0,90.00),("V-20047",9,2025,1,85.00),("V-20047",10,2025,0,92.50),
    ("V-20048",8,2025,0,100.00),("V-20048",9,2025,0,100.00),("V-20048",10,2025,0,100.00),
    ("V-20049",8,2025,0,97.50),("V-20049",9,2025,0,100.00),("V-20049",10,2025,0,100.00),
    ("V-20050",8,2025,1,92.00),("V-20050",9,2025,0,95.00),("V-20050",10,2025,0,88.00),
    ("V-20051",8,2025,0,85.00),("V-20051",9,2025,2,80.00),("V-20051",10,2025,0,90.00),
    ("V-20052",8,2025,0,100.00),("V-20052",9,2025,0,95.00),("V-20052",10,2025,1,97.50),
    ("V-20053",8,2025,2,75.00),("V-20053",9,2025,1,80.00),("V-20053",10,2025,0,85.00),
    ("V-20054",8,2025,3,70.00),("V-20054",9,2025,1,75.00),("V-20054",10,2025,2,72.00),
]
c.executemany("INSERT INTO Monthly_Performance VALUES (?,?,?,?,?)", mp)

# --- Procurement_Historical_Pricing ---
php = [
    ("PHP-001","1000-10042678","V-20045","2025-09-15",462.00,200,"INR"),
    ("PHP-002","1000-10042678","V-20046","2025-08-10",470.00,150,"INR"),
    ("PHP-003","1000-10042678","V-20047","2025-07-20",485.00,100,"INR"),
    ("PHP-004","1000-10042678","V-20053","2025-06-01",490.00,50,"INR"),
    ("PHP-005","1000-10042679","V-20045","2025-08-20",2850.00,40,"INR"),
    ("PHP-006","1000-10055001","V-20048","2025-07-10",1450.00,25,"INR"),
    ("PHP-007","1000-10055003","V-20049","2025-06-20",28500.00,3,"INR"),
    ("PHP-008","1000-10067001","V-20050","2025-09-01",18500.00,4,"INR"),
    ("PHP-009","1000-10078001","V-20051","2025-09-25",14200.00,8,"INR"),
    ("PHP-010","1000-10089001","V-20052","2025-08-15",2100.00,150,"INR"),
]
c.executemany("INSERT INTO Procurement_Historical_Pricing VALUES (?,?,?,?,?,?,?)", php)

conn.commit()
print("✅ ERP reference data populated (6 tables)")

# ============================================================================
# PHASE 4: POPULATE STM TRANSACTION DATA — Full pipeline for 5 clusters
# ============================================================================

# Cluster 1: Bearings 6205-2RS (COMPLETED through NFA approval, ready for PO)
# Cluster 2: Spherical Roller Bearings (at Techno-Commercial Comparison stage)
# Cluster 3: Contactors (at RFQ Dispatched, awaiting submissions)
# Cluster 4: VFD Drives (at Buyer Assignment stage — early pipeline)
# Cluster 5: Hydraulic Cylinders (at PR Consolidation — brand new)

# --- Consolidated_PRs ---
clusters = [
    ("CL-2025-00847-01","PR-2025-00847","1000-10042678","MRO-BRG","Deep Groove Ball Bearing 6205-2RS — Conveyor Drive, BF Plant",
     "SKF/FAG 6205-2RS | ID:25mm OD:52mm Width:15mm | C3 clearance | Grease-lubricated",240.0,"NO","NO",117600.00,"INR","1010","CC-1010-BF-MAINT","OPEX","Supply",
     "NFA_Approved","ramesh.kumar@jswsteel.in","Net 45 days from GRN","2025-12-15","RFQ-2025-00289","Approved",0,0,
     "2025-11-14 09:32:00","2025-11-14 11:45:00","2025-11-17 16:20:00","2025-11-18 10:00:00","2025-11-18 22:10:00","2025-11-19 08:05:00","2025-12-02 14:30:00",None,None),
    ("CL-2025-00848-01","PR-2025-00848","1000-10042679","MRO-BRG","Spherical Roller Bearing 22210 EK — SMS Caster Drive",
     "SKF 22210 EK | Bore:50mm OD:90mm Width:23mm | Tapered bore | Dynamic load 65kN",50.0,"NO","NO",142500.00,"INR","1020","CC-1020-SMS-MAINT","OPEX","Supply",
     "RFQ_Evaluation","ramesh.kumar@jswsteel.in","Net 30 days from GRN","2025-12-20","RFQ-2025-00290",None,0,0,
     "2025-11-15 10:00:00","2025-11-15 14:00:00","2025-11-18 09:00:00","2025-11-19 11:00:00","2025-11-19 18:00:00","2025-11-20 08:00:00",None,None,None),
    ("CL-2025-00850-01","PR-2025-00850","1000-10055001","MRO-ELE","Contactor 3-Pole 25A 240V AC — BF Electrical Panel",
     "Schneider LC1D25M7 or equivalent | 3P | 25A | 240V AC coil",30.0,"NO","NO",43500.00,"INR","1010","CC-1010-BF-ELEC","OPEX","Supply",
     "RFQ_Dispatched","priya.sharma@jswsteel.in","Net 30 days from GRN","2025-12-10","RFQ-2025-00291",None,0,0,
     "2025-11-16 09:00:00","2025-11-16 11:00:00","2025-11-18 14:00:00","2025-11-20 09:00:00","2025-11-20 16:00:00","2025-11-21 08:00:00",None,None,None),
    ("CL-2025-00851-01","PR-2025-00851","1000-10055003","MRO-ELE","VFD Drive 7.5kW 3-Phase 415V — SMS Rolling Mill",
     "ABB ACS580 or Siemens G120 | 7.5kW | 3-Phase 415V | IP55",4.0,"NO","NO",114000.00,"INR","1020","CC-1020-SMS-ELEC","CAPEX","Supply",
     "Buyer_Assigned","anil.deshmukh@jswsteel.in",None,"2026-01-15",None,None,0,0,
     "2025-11-17 09:00:00","2025-11-17 14:00:00",None,None,None,None,None,None,None),
    ("CL-2025-00852-01","PR-2025-00852","1000-10067001","MRO-HYD","Hydraulic Cylinder 80mm Bore 500mm Stroke — BF Charging Machine",
     "Bosch Rexroth CDT3 or equivalent | 80mm bore | 500mm stroke | 250 bar",6.0,"NO","NO",111000.00,"INR","1010","CC-1010-BF-HYD","OPEX","Supply",
     "New",None,None,"2026-01-10",None,None,0,0,
     "2025-11-18 09:00:00",None,None,None,None,None,None,None,None),
]
c.executemany("INSERT INTO Consolidated_PRs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", clusters)

# --- RFQ_Log ---
rfqs = [
    ("RFQ-2025-00289","CL-2025-00847-01","Closed","Tech: 40%, Comm: 60%, Min score: 70","2025-11-26 18:00:00","ramesh.kumar@jswsteel.in","2025-11-18 10:00:00","2025-12-01 10:00:00"),
    ("RFQ-2025-00290","CL-2025-00848-01","Under_Evaluation","Tech: 40%, Comm: 60%, Min score: 70","2025-11-28 18:00:00","ramesh.kumar@jswsteel.in","2025-11-19 11:00:00","2025-11-29 14:00:00"),
    ("RFQ-2025-00291","CL-2025-00850-01","Dispatched","Tech: 30%, Comm: 70%, Min score: 65","2025-12-02 18:00:00","priya.sharma@jswsteel.in","2025-11-20 09:00:00","2025-11-21 08:00:00"),
]
c.executemany("INSERT INTO RFQ_Log VALUES (?,?,?,?,?,?,?,?)", rfqs)

# --- Vendor_Shortlist ---
shortlists = [
    ("VS-001","RFQ-2025-00289","V-20045","Top rated in bearings, lowest LPP",87.50,"2025-11-18 10:30:00"),
    ("VS-002","RFQ-2025-00289","V-20046","Good history, competitive pricing",82.00,"2025-11-18 10:30:00"),
    ("VS-003","RFQ-2025-00289","V-20047","Third source, acceptable quality",79.50,"2025-11-18 10:30:00"),
    ("VS-004","RFQ-2025-00289","V-20054","MSME vendor, price discovery",68.50,"2025-11-18 10:30:00"),
    ("VS-005","RFQ-2025-00290","V-20045","Primary for spherical rollers",87.50,"2025-11-19 11:30:00"),
    ("VS-006","RFQ-2025-00290","V-20046","Secondary source",82.00,"2025-11-19 11:30:00"),
    ("VS-007","RFQ-2025-00290","V-20047","Tertiary source",79.50,"2025-11-19 11:30:00"),
    ("VS-008","RFQ-2025-00291","V-20048","Primary for electrical",91.00,"2025-11-20 09:30:00"),
    ("VS-009","RFQ-2025-00291","V-20049","ABB — secondary",88.50,"2025-11-20 09:30:00"),
    ("VS-010","RFQ-2025-00291","V-20053","MSME — price discovery",72.00,"2025-11-20 09:30:00"),
]
c.executemany("INSERT INTO Vendor_Shortlist VALUES (?,?,?,?,?,?)", shortlists)

# --- RFQ_Dispatch_Log ---
dispatches = [
    ("DSP-001","RFQ-2025-00289","V-20045","Email","2025-11-19 08:05:00","Delivered"),
    ("DSP-002","RFQ-2025-00289","V-20046","Email","2025-11-19 08:05:00","Delivered"),
    ("DSP-003","RFQ-2025-00289","V-20047","Email","2025-11-19 08:05:00","Delivered"),
    ("DSP-004","RFQ-2025-00289","V-20054","Email","2025-11-19 08:05:00","Delivered"),
    ("DSP-005","RFQ-2025-00290","V-20045","Email","2025-11-20 08:00:00","Delivered"),
    ("DSP-006","RFQ-2025-00290","V-20046","Email","2025-11-20 08:00:00","Delivered"),
    ("DSP-007","RFQ-2025-00290","V-20047","Email","2025-11-20 08:00:00","Delivered"),
    ("DSP-008","RFQ-2025-00291","V-20048","Email","2025-11-21 08:00:00","Delivered"),
    ("DSP-009","RFQ-2025-00291","V-20049","Email","2025-11-21 08:00:00","Delivered"),
    ("DSP-010","RFQ-2025-00291","V-20053","Email","2025-11-21 08:00:00","Delivered"),
]
c.executemany("INSERT INTO RFQ_Dispatch_Log VALUES (?,?,?,?,?,?)", dispatches)

# --- RFQ_Submissions (only for RFQ-289 completed, RFQ-290 partial) ---
submissions = [
    ("SUB-001","RFQ-2025-00289","V-20045",445.00,18,"DOC-SUB-001","2025-11-24 14:00:00"),
    ("SUB-002","RFQ-2025-00289","V-20046",458.00,20,"DOC-SUB-002","2025-11-25 10:00:00"),
    ("SUB-003","RFQ-2025-00289","V-20047",472.00,22,"DOC-SUB-003","2025-11-25 16:00:00"),
    ("SUB-004","RFQ-2025-00289","V-20054",495.00,25,"DOC-SUB-004","2025-11-26 09:00:00"),
    ("SUB-005","RFQ-2025-00290","V-20045",2780.00,25,"DOC-SUB-005","2025-11-27 14:00:00"),
    ("SUB-006","RFQ-2025-00290","V-20046",2920.00,22,"DOC-SUB-006","2025-11-28 10:00:00"),
    ("SUB-007","RFQ-2025-00290","V-20047",3050.00,28,"DOC-SUB-007","2025-11-28 16:00:00"),
]
c.executemany("INSERT INTO RFQ_Submissions VALUES (?,?,?,?,?,?,?)", submissions)

# --- RFQ_Tech_Evaluations (RFQ-289 done) ---
tech_evals = [
    ("TE-001","SUB-001",92.00,"Full spec compliance. C3 clearance confirmed. FAG equivalent acceptable."),
    ("TE-002","SUB-002",88.00,"Meets specs. Slight deviation on grease type — acceptable."),
    ("TE-003","SUB-003",85.00,"Meets minimum specs. No C3 clearance option — standard only."),
    ("TE-004","SUB-004",72.00,"Generic bearing. Limited documentation. Marginal tech compliance."),
    ("TE-005","SUB-005",90.00,"Full 22210 EK compliance. Tapered bore confirmed."),
    ("TE-006","SUB-006",86.00,"Meets specs. Slightly higher weight tolerance."),
    ("TE-007","SUB-007",82.00,"Acceptable. Older generation bearing design."),
]
c.executemany("INSERT INTO RFQ_Tech_Evaluations VALUES (?,?,?,?)", tech_evals)

# --- RFQ_Comm_Evaluations (RFQ-289 done) ---
comm_evals = [
    ("CE-001","SUB-001",95.00,90.00,92.00,"Best price. Net 45 days. 18 day lead time — excellent."),
    ("CE-002","SUB-002",88.00,85.00,85.00,"Competitive. Net 30 days. 20 day lead time."),
    ("CE-003","SUB-003",80.00,80.00,78.00,"Higher price. Net 30 days. 22 day lead time."),
    ("CE-004","SUB-004",65.00,70.00,70.00,"Highest price. Net 60 days. 25 day lead time."),
    ("CE-005","SUB-005",94.00,85.00,88.00,"Best price for 22210. Good terms."),
    ("CE-006","SUB-006",85.00,80.00,82.00,"Competitive second option."),
    ("CE-007","SUB-007",72.00,78.00,75.00,"Highest price in category."),
]
c.executemany("INSERT INTO RFQ_Comm_Evaluations VALUES (?,?,?,?,?,?)", comm_evals)

# --- RFQ_Overall_Evaluations (RFQ-289 done, RFQ-290 in progress) ---
overall_evals = [
    ("OE-001","SUB-001",36.80,55.80,92.60),  # SKF: T=92*0.4, C=93*0.6
    ("OE-002","SUB-002",35.20,51.60,86.80),  # NTN
    ("OE-003","SUB-003",34.00,47.60,81.60),  # Timken
    ("OE-004","SUB-004",28.80,41.00,69.80),  # Precision (below 70 threshold)
    ("OE-005","SUB-005",36.00,53.40,89.40),
    ("OE-006","SUB-006",34.40,49.40,83.80),
    ("OE-007","SUB-007",32.80,45.00,77.80),
]
c.executemany("INSERT INTO RFQ_Overall_Evaluations VALUES (?,?,?,?,?)", overall_evals)

# --- Negotiation_Intelligence_Log ---
neg_intel = [
    ("BRIEF-2025-00289","RFQ-2025-00289",
     "Annual spend on MRO-BRG category: INR 42.5L across 3 plants. SKF = 58% share. Volume leverage possible.",
     "Bearing prices stable Q4 2025. Domestic manufacturers offering 3-5% discount vs Q3. Steel input costs flat."),
]
c.executemany("INSERT INTO Negotiation_Intelligence_Log VALUES (?,?,?,?)", neg_intel)

# --- Negotiation_Shortlist_Approval (for RFQ-289) ---
neg_approvals = [
    ("NA-001","RFQ-2025-00289","V-20045",445.00,"Approved","vikram.singh@jswsteel.in","2025-12-01 10:00:00"),
]
c.executemany("INSERT INTO Negotiation_Shortlist_Approval VALUES (?,?,?,?,?,?,?)", neg_approvals)

# --- NFA_Log ---
nfas = [
    ("NFA-2025-00312","CL-2025-00847-01","RFQ-2025-00289","V-20045",445.00,106800.00,"Below_LPP",-3.68,3.68,None,"Approved","DOC-NFA-001","ramesh.kumar@jswsteel.in","2025-12-01 11:00:00","2025-12-02 14:30:00"),
]
c.executemany("INSERT INTO NFA_Log VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", nfas)

# --- NFA_Approval_Log ---
nfa_approvals = [
    ("NFAA-001","NFA-2025-00312",1,"DES-SR-BUY-MRO","vikram.singh@jswsteel.in","Approved","Good price vs LPP. Proceed.","2025-12-01 16:00:00"),
    ("NFAA-002","NFA-2025-00312",2,"DES-MGR-PROC","anjali.mehta@jswsteel.in","Approved","Approved. Within DOP limits.","2025-12-02 10:00:00"),
]
c.executemany("INSERT INTO NFA_Approval_Log VALUES (?,?,?,?,?,?,?,?)", nfa_approvals)

# --- Approval_Log (general) ---
approvals = [
    ("APR-001","RFQ","RFQ-2025-00289","vikram.singh@jswsteel.in","Senior Manager","Approved","RFQ compliant. Proceed to dispatch.","2025-11-18 22:10:00"),
    ("APR-002","RFQ","RFQ-2025-00290","vikram.singh@jswsteel.in","Senior Manager","Approved","Approved.","2025-11-19 18:00:00"),
    ("APR-003","RFQ","RFQ-2025-00291","vikram.singh@jswsteel.in","Senior Manager","Approved","Proceed.","2025-11-20 16:00:00"),
    ("APR-004","NFA","NFA-2025-00312","vikram.singh@jswsteel.in","Senior Manager","Approved","Good savings.","2025-12-01 16:00:00"),
    ("APR-005","NFA","NFA-2025-00312","anjali.mehta@jswsteel.in","GM Procurement","Approved","Within limits.","2025-12-02 10:00:00"),
]
c.executemany("INSERT INTO Approval_Log VALUES (?,?,?,?,?,?,?,?)", approvals)

# --- Spec_Requests ---
specs = [
    ("SREQ-001","CL-2025-00847-01","suresh.patil@jswsteel.in","Received","DOC-SPEC-001","2025-11-14 10:00:00"),
    ("SREQ-002","CL-2025-00848-01","manoj.gupta@jswsteel.in","Received","DOC-SPEC-002","2025-11-15 10:30:00"),
    ("SREQ-003","CL-2025-00851-01","ravi.kumar@jswsteel.in","Pending",None,"2025-11-17 09:30:00"),
]
c.executemany("INSERT INTO Spec_Requests VALUES (?,?,?,?,?,?)", specs)

# --- SVJ_Log (none needed for these RFQs — all have 3+ vendors) ---

# --- DMS_Documents ---
docs = [
    ("DOC-SPEC-001","Technical_Specification","Material","1000-10042678","BRG_6205_2RS_TechSpec.pdf","/DMS_Documents/Specs/BRG_6205_2RS_TechSpec.pdf","suresh.patil@jswsteel.in","2025-11-14 10:30:00",245,1),
    ("DOC-SPEC-002","Technical_Specification","Material","1000-10042679","BRG_22210_EK_TechSpec.pdf","/DMS_Documents/Specs/BRG_22210_EK_TechSpec.pdf","manoj.gupta@jswsteel.in","2025-11-15 11:00:00",312,1),
    ("DOC-SPEC-003","Technical_Specification","Material","1000-10055003","VFD_7.5KW_TechSpec.pdf","/DMS_Documents/Specs/VFD_7.5KW_TechSpec.pdf","ravi.kumar@jswsteel.in","2025-09-10 14:00:00",520,2),
    ("DOC-SUB-001","Vendor_Quotation","Submission","SUB-001","SKF_Quote_RFQ289.pdf","/DMS_Documents/RFQ/SKF_Quote_RFQ289.pdf","vendor.skf@skfindia.com","2025-11-24 14:00:00",180,1),
    ("DOC-SUB-002","Vendor_Quotation","Submission","SUB-002","NTN_Quote_RFQ289.pdf","/DMS_Documents/RFQ/NTN_Quote_RFQ289.pdf","vendor.ntn@ntnindia.com","2025-11-25 10:00:00",165,1),
    ("DOC-SUB-003","Vendor_Quotation","Submission","SUB-003","Timken_Quote_RFQ289.pdf","/DMS_Documents/RFQ/Timken_Quote_RFQ289.pdf","vendor@timkenindia.com","2025-11-25 16:00:00",190,1),
    ("DOC-SUB-004","Vendor_Quotation","Submission","SUB-004","PrecBrg_Quote_RFQ289.pdf","/DMS_Documents/RFQ/PrecBrg_Quote_RFQ289.pdf","sales@precisionbearings.in","2025-11-26 09:00:00",140,1),
    ("DOC-NFA-001","NFA_Document","NFA","NFA-2025-00312","NFA_312_Bearing_6205.pdf","/DMS_Documents/NFA/NFA_312_Bearing_6205.pdf","ramesh.kumar@jswsteel.in","2025-12-01 11:00:00",350,1),
    ("DOC-SUB-005","Vendor_Quotation","Submission","SUB-005","SKF_Quote_RFQ290.pdf","/DMS_Documents/RFQ/SKF_Quote_RFQ290.pdf","vendor.skf@skfindia.com","2025-11-27 14:00:00",195,1),
    ("DOC-SUB-006","Vendor_Quotation","Submission","SUB-006","NTN_Quote_RFQ290.pdf","/DMS_Documents/RFQ/NTN_Quote_RFQ290.pdf","vendor.ntn@ntnindia.com","2025-11-28 10:00:00",170,1),
    ("DOC-SUB-007","Vendor_Quotation","Submission","SUB-007","Timken_Quote_RFQ290.pdf","/DMS_Documents/RFQ/Timken_Quote_RFQ290.pdf","vendor@timkenindia.com","2025-11-28 16:00:00",185,1),
]
c.executemany("INSERT INTO DMS_Documents VALUES (?,?,?,?,?,?,?,?,?,?)", docs)

# --- Compliance_Log ---
compliance = [
    ("COMP-001","CTRL-001","RFQ","RFQ-2025-00289","Pass","4 vendors dispatched (>= 3 minimum)","2025-11-19 08:10:00",None,None),
    ("COMP-002","CTRL-001","RFQ","RFQ-2025-00290","Pass","3 vendors dispatched (>= 3 minimum)","2025-11-20 08:05:00",None,None),
    ("COMP-003","CTRL-001","RFQ","RFQ-2025-00291","Pass","3 vendors dispatched (>= 3 minimum)","2025-11-21 08:05:00",None,None),
    ("COMP-004","CTRL-003","NFA","NFA-2025-00312","Pass","Price INR 445 vs LPP INR 462 — Below LPP by 3.68%","2025-12-01 11:05:00",None,None),
    ("COMP-005","CTRL-005","NFA","NFA-2025-00312","Pass","NFA value INR 106,800 — within Tier 1 DOP limit (< 5L)","2025-12-01 11:10:00",None,None),
    ("COMP-006","CTRL-011","RFQ","RFQ-2025-00289","Pass","All 4 submissions evaluated (tech + comm + overall)","2025-11-30 10:00:00",None,None),
    ("COMP-007","CTRL-015","NFA","NFA-2025-00312","Pass","NFA document complete: vendor, price, justification, evaluation ref","2025-12-01 11:15:00",None,None),
]
c.executemany("INSERT INTO Compliance_Log VALUES (?,?,?,?,?,?,?,?,?)", compliance)

# --- Process_Events_Log ---
events = [
    ("EVT-001","S2C.PR.01","Consolidated_PRs","CL-2025-00847-01","PR_Consolidated","PR-2025-00847 consolidated into cluster CL-2025-00847-01","system","2025-11-14 09:32:00"),
    ("EVT-002","S2C.RFQ.02","Spec_Requests","SREQ-001","Spec_Requested","Spec request sent to suresh.patil@jswsteel.in","system","2025-11-14 10:00:00"),
    ("EVT-003","S2C.RFQ.03","Consolidated_PRs","CL-2025-00847-01","Buyer_Assigned","Buyer ramesh.kumar@jswsteel.in assigned based on MRO-BRG category","system","2025-11-14 11:45:00"),
    ("EVT-004","S2C.RFQ.06","RFQ_Log","RFQ-2025-00289","RFQ_Created","RFQ generated for cluster CL-2025-00847-01","ramesh.kumar@jswsteel.in","2025-11-18 10:00:00"),
    ("EVT-005","S2C.RFQ.07","Approval_Log","APR-001","RFQ_Approved","RFQ-2025-00289 approved by vikram.singh@jswsteel.in","system","2025-11-18 22:10:00"),
    ("EVT-006","S2C.RFQ.08","RFQ_Dispatch_Log","DSP-001","RFQ_Dispatched","RFQ dispatched to 4 vendors via email","system","2025-11-19 08:05:00"),
    ("EVT-007","S2C.NEG.13","NFA_Log","NFA-2025-00312","NFA_Created","NFA created: SKF @ INR 445/unit, savings 3.68% vs LPP","ramesh.kumar@jswsteel.in","2025-12-01 11:00:00"),
    ("EVT-008","S2C.NFA.15","NFA_Approval_Log","NFAA-002","NFA_Approved","NFA-2025-00312 fully approved (2 tiers)","system","2025-12-02 14:30:00"),
]
c.executemany("INSERT INTO Process_Events_Log VALUES (?,?,?,?,?,?,?,?)", events)

conn.commit()
print("✅ STM transaction data populated (full pipeline across 5 clusters)")

# ============================================================================
# PHASE 5: VERIFICATION
# ============================================================================
print("\n" + "="*60)
print("DATABASE VERIFICATION")
print("="*60)

tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"\nTotal tables: {len(tables)}")
for t in tables:
    count = c.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
    print(f"  {t[0]:40s} → {count:>4d} rows")

# FK integrity check
print("\n--- FK Integrity Checks ---")
checks = [
    ("Consolidated_PRs → Master_PR_Data", "SELECT COUNT(*) FROM Consolidated_PRs cp WHERE NOT EXISTS (SELECT 1 FROM Master_PR_Data m WHERE m.PR_Number = cp.PR_Number)"),
    ("Consolidated_PRs → Material_Master", "SELECT COUNT(*) FROM Consolidated_PRs cp WHERE NOT EXISTS (SELECT 1 FROM Material_Master m WHERE m.Material_Code = cp.Material_Code)"),
    ("Vendor_Shortlist → Vendor_Master", "SELECT COUNT(*) FROM Vendor_Shortlist vs WHERE NOT EXISTS (SELECT 1 FROM Vendor_Master v WHERE v.Vendor_Code = vs.Vendor_Code)"),
    ("NFA_Log → Vendor_Master", "SELECT COUNT(*) FROM NFA_Log n WHERE NOT EXISTS (SELECT 1 FROM Vendor_Master v WHERE v.Vendor_Code = n.Recommended_Vendor)"),
    ("Supplier_Master → Vendor_Master", "SELECT COUNT(*) FROM Supplier_Master s WHERE NOT EXISTS (SELECT 1 FROM Vendor_Master v WHERE v.Vendor_Code = s.Supplier_Code)"),
]
all_ok = True
for label, sql in checks:
    orphans = c.execute(sql).fetchone()[0]
    status = "✅ OK" if orphans == 0 else f"❌ {orphans} orphans"
    if orphans > 0: all_ok = False
    print(f"  {label:50s} {status}")

if all_ok:
    print("\n✅ ALL FK INTEGRITY CHECKS PASSED")
else:
    print("\n❌ SOME FK CHECKS FAILED — review data")

conn.close()

import shutil
shutil.copy2(DB_BUILD_PATH, DB_FINAL_PATH)
print(f"\n📁 Database built: {DB_BUILD_PATH}")
print(f"📁 Copied to: {DB_FINAL_PATH}")
print(f"📁 Size: {os.path.getsize(DB_FINAL_PATH)/1024:.1f} KB")
