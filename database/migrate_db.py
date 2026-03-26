"""
Database Migration Script — Sourcesense S2C Platform
Applies all cleanup changes to s2c_sourcesense.db:

  1. Merge Supplier_Master into Vendor_Master
  2. Fix Onboarding_Tracker: rename GST_Number→GSTIN, populate all 45 vendors
  3. Fix Monthly_Performance: Month/Year integers → Period VARCHAR(7), refresh dates
  4. Make Vendor_Shortlist.RFQ_ID nullable
  5. Unify NFA_Approval_Log into Approval_Log (add Tier_Level), drop NFA_Approval_Log
  6. Create LPP_Master (Material_Code + Plant), populate from Material_Master LPP data
  7. Create PO_History (granular), merge Procurement_Historical_Pricing + Vendor_History
  8. Remove LPP columns from Material_Master
  9. Drop Supplier_Master, Procurement_Historical_Pricing, Vendor_History
"""

import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 's2c_sourcesense.db')


def run(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    c = conn.cursor()

    # ─────────────────────────────────────────────────────────────────
    # 1. MERGE Supplier_Master → Vendor_Master
    # ─────────────────────────────────────────────────────────────────
    print("[1] Merging Supplier_Master into Vendor_Master...")
    c.execute("ALTER TABLE Vendor_Master ADD COLUMN Overall_Score DECIMAL(5,2)")
    c.execute("ALTER TABLE Vendor_Master ADD COLUMN Last_Evaluation_Date DATE")
    c.execute("ALTER TABLE Vendor_Master ADD COLUMN CAPA_Due_Date DATE")

    c.execute("""
        UPDATE Vendor_Master SET
            Overall_Score       = (SELECT Overall_Score       FROM Supplier_Master WHERE Supplier_Code = Vendor_Master.Vendor_Code),
            Last_Evaluation_Date= (SELECT Last_Evaluation_Date FROM Supplier_Master WHERE Supplier_Code = Vendor_Master.Vendor_Code),
            CAPA_Due_Date       = (SELECT CAPA_Due_Date        FROM Supplier_Master WHERE Supplier_Code = Vendor_Master.Vendor_Code)
    """)
    c.execute("DROP TABLE Supplier_Master")
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 2. FIX Onboarding_Tracker: rename column, fill all 45 vendors
    # ─────────────────────────────────────────────────────────────────
    print("[2] Fixing Onboarding_Tracker...")
    # Rename GST_Number → GSTIN (SQLite 3.25+)
    c.execute("ALTER TABLE Onboarding_Tracker RENAME COLUMN GST_Number TO GSTIN")

    # Fetch all vendor GSTINs already tracked
    c.execute("SELECT GSTIN FROM Onboarding_Tracker")
    tracked = {r[0] for r in c.fetchall()}

    # Fetch all vendors not yet tracked
    c.execute("SELECT Vendor_Code, GSTIN, Blacklisted FROM Vendor_Master WHERE GSTIN IS NOT NULL")
    all_vendors = c.fetchall()

    # Determine next ONB sequence number
    c.execute("SELECT MAX(CAST(SUBSTR(Onboarding_ID,10) AS INTEGER)) FROM Onboarding_Tracker")
    row = c.fetchone()
    seq = (row[0] or 96) + 1

    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    for vendor_code, gstin, blacklisted in all_vendors:
        if gstin in tracked:
            continue
        # Blacklisted vendor → Rejected; others → Approved
        decision = 'Rejected' if blacklisted else 'Approved'
        pan_gst_valid = 0 if blacklisted else 1
        onb_id = f"ONB-2026-{seq:05d}"
        c.execute("""
            INSERT INTO Onboarding_Tracker
                (Onboarding_ID, GSTIN, PAN_Valid, GST_Valid, Finance_Decision, Vendor_Activated_At)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (onb_id, gstin, pan_gst_valid, pan_gst_valid, decision, now))
        seq += 1
    print(f"    Added {seq - 97} new onboarding entries. Done.")

    # ─────────────────────────────────────────────────────────────────
    # 3. FIX Monthly_Performance: Month/Year → Period VARCHAR(7)
    #    and roll dates forward so they fall within the last 3 months
    # ─────────────────────────────────────────────────────────────────
    print("[3] Fixing Monthly_Performance schema and refreshing dates...")

    c.execute("SELECT * FROM Monthly_Performance")
    old_rows = c.fetchall()

    # Map old (month, year) combos to new Period values within last 3 months
    # Today = 2026-03-26 → last 3 months = 2025-12, 2026-01, 2026-02, 2026-03
    unique_periods = sorted({(r[1], r[2]) for r in old_rows})  # (Month, Year)
    period_map = {}
    target_periods = ['2025-12', '2026-01', '2026-02', '2026-03']
    for i, (month, year) in enumerate(unique_periods):
        period_map[(month, year)] = target_periods[i % len(target_periods)]

    c.execute("DROP TABLE Monthly_Performance")
    c.execute("""
        CREATE TABLE Monthly_Performance (
            Supplier_Code           VARCHAR(20) NOT NULL,
            Period                  VARCHAR(7)  NOT NULL,
            Quality_Incidents       INTEGER     DEFAULT 0,
            Delivery_On_Time_Pct    DECIMAL(5,2),
            PRIMARY KEY (Supplier_Code, Period)
        )
    """)

    for row in old_rows:
        supplier_code, month, year, quality_incidents, delivery_pct = row
        period = period_map.get((month, year), f"{year}-{month:02d}")
        c.execute("""
            INSERT OR REPLACE INTO Monthly_Performance
                (Supplier_Code, Period, Quality_Incidents, Delivery_On_Time_Pct)
            VALUES (?, ?, ?, ?)
        """, (supplier_code, period, quality_incidents, delivery_pct))
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 4. Make Vendor_Shortlist.RFQ_ID nullable (recreate table)
    # ─────────────────────────────────────────────────────────────────
    print("[4] Making Vendor_Shortlist.RFQ_ID nullable...")
    c.execute("SELECT * FROM Vendor_Shortlist")
    vs_rows = c.fetchall()
    c.execute("DROP TABLE Vendor_Shortlist")
    c.execute("""
        CREATE TABLE Vendor_Shortlist (
            Shortlist_ID        VARCHAR(20) PRIMARY KEY,
            RFQ_ID              VARCHAR(20),
            Vendor_Code         VARCHAR(20) NOT NULL,
            Shortlist_Reason    TEXT,
            Historical_Score    DECIMAL(5,2),
            Added_At            DATETIME    NOT NULL
        )
    """)
    for row in vs_rows:
        c.execute("INSERT INTO Vendor_Shortlist VALUES (?,?,?,?,?,?)", row)
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 5. UNIFY NFA_Approval_Log into Approval_Log
    # ─────────────────────────────────────────────────────────────────
    print("[5] Unifying NFA_Approval_Log into Approval_Log...")
    c.execute("ALTER TABLE Approval_Log ADD COLUMN Tier_Level INTEGER")

    # Determine next APPR sequence
    c.execute("SELECT MAX(CAST(SUBSTR(Approval_ID, 6) AS INTEGER)) FROM Approval_Log")
    appr_seq = (c.fetchone()[0] or 0) + 1

    c.execute("SELECT * FROM NFA_Approval_Log")
    nfa_approvals = c.fetchall()
    # NFA_Approval_Log columns: NFA_Approval_ID, NFA_ID, Tier_Level, Approver_Designation,
    #                           Approver_Email, Decision, Comments, Decided_At
    for row in nfa_approvals:
        _, nfa_id, tier_level, approver_desig, approver_email, decision, comments, decided_at = row
        appr_id = f"APPR-{appr_seq:04d}"
        c.execute("""
            INSERT INTO Approval_Log
                (Approval_ID, Entity_Type, Entity_ID, Approver_Email,
                 Approver_Designation, Decision, Comments, Decided_At, Tier_Level)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (appr_id, 'NFA', nfa_id, approver_email,
              approver_desig, decision, comments, decided_at, tier_level))
        appr_seq += 1

    c.execute("DROP TABLE NFA_Approval_Log")
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 6. CREATE LPP_Master (Material_Code + Plant granularity)
    # ─────────────────────────────────────────────────────────────────
    print("[6] Creating LPP_Master...")
    c.execute("""
        CREATE TABLE LPP_Master (
            Material_Code       VARCHAR(20) NOT NULL,
            Plant               VARCHAR(10) NOT NULL,
            Last_Purchase_Price DECIMAL(15,2),
            Currency            VARCHAR(5)  DEFAULT 'INR',
            Last_PO_Date        DATE,
            Last_Vendor_Code    VARCHAR(20),
            Last_PO_Number      VARCHAR(20),
            Updated_At          DATETIME,
            PRIMARY KEY (Material_Code, Plant)
        )
    """)

    # Pull existing LPP data from Material_Master
    c.execute("""
        SELECT Material_Code, Last_Purchase_Price, LPP_Currency, LPP_Date, LPP_Vendor_Code
        FROM Material_Master
        WHERE Last_Purchase_Price IS NOT NULL
    """)
    lpp_rows = c.fetchall()

    plants = ['1010', '1020', '1030']
    now_str = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')

    for mat_code, lpp, currency, lpp_date, vendor_code in lpp_rows:
        for plant in plants:
            c.execute("""
                INSERT OR IGNORE INTO LPP_Master
                    (Material_Code, Plant, Last_Purchase_Price, Currency,
                     Last_PO_Date, Last_Vendor_Code, Updated_At)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mat_code, plant, lpp, currency or 'INR', lpp_date, vendor_code, now_str))

    # Also enrich from PO_History data (most recent PO per material+plant)
    # We'll do this after PO_History is created (step 7b)
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 7. CREATE PO_History — merge Procurement_Historical_Pricing
    #    and Vendor_History into one granular per-PO table
    # ─────────────────────────────────────────────────────────────────
    print("[7] Creating PO_History...")
    c.execute("""
        CREATE TABLE PO_History (
            PO_History_ID       VARCHAR(20) PRIMARY KEY,
            Vendor_Code         VARCHAR(20) NOT NULL,
            Material_Code       VARCHAR(20) NOT NULL,
            Plant               VARCHAR(10),
            PO_Number           VARCHAR(20),
            PO_Date             DATE        NOT NULL,
            Unit_Price          DECIMAL(15,2) NOT NULL,
            Quantity            DECIMAL(15,3),
            Currency            VARCHAR(5)  DEFAULT 'INR',
            Delivery_Days       DECIMAL(5,1),
            Quality_Rating      DECIMAL(3,1),
            Quality_Incidents   INTEGER     DEFAULT 0
        )
    """)

    # Migrate Procurement_Historical_Pricing records (already granular)
    # Join with Vendor_History to get delivery/quality where vendor+material matches
    c.execute("""
        SELECT
            p.Pricing_ID, p.Vendor_Code, p.Material_Code, p.PO_Date,
            p.Unit_Price, p.Quantity, p.Currency,
            v.Avg_Delivery_Days, v.Quality_Rating
        FROM Procurement_Historical_Pricing p
        LEFT JOIN Vendor_History v
            ON p.Vendor_Code = v.Vendor_Code AND p.Material_Code = v.Material_Code
    """)
    php_rows = c.fetchall()

    for row in php_rows:
        pricing_id, vendor, material, po_date, price, qty, currency, delivery_days, quality = row
        ph_id = f"PH-{pricing_id.replace('PHP-', '')}"
        c.execute("""
            INSERT INTO PO_History
                (PO_History_ID, Vendor_Code, Material_Code, PO_Date,
                 Unit_Price, Quantity, Currency, Delivery_Days, Quality_Rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ph_id, vendor, material, po_date, price, qty, currency or 'INR',
              delivery_days, quality))

    # Get vendor+material combos already migrated from PHP
    c.execute("SELECT Vendor_Code, Material_Code FROM PO_History")
    already_migrated = {(r[0], r[1]) for r in c.fetchall()}

    # Migrate remaining Vendor_History records not covered by PHP
    # These have aggregate data — we treat each as a single representative record
    c.execute("SELECT * FROM Vendor_History")
    vh_rows = c.fetchall()
    vh_seq = len(php_rows) + 1

    for row in vh_rows:
        hist_id, vendor, material, last_po_date, last_po_price, total_pos, avg_delivery, quality = row
        if (vendor, material) in already_migrated:
            continue  # already have granular data from PHP
        ph_id = f"PH-{vh_seq:03d}"
        c.execute("""
            INSERT INTO PO_History
                (PO_History_ID, Vendor_Code, Material_Code, PO_Date,
                 Unit_Price, Delivery_Days, Quality_Rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ph_id, vendor, material, last_po_date, last_po_price, avg_delivery, quality))
        vh_seq += 1

    # 7b. Back-fill LPP_Master with most recent PO per material+plant from PO_History
    # Since PO_History doesn't have Plant yet (came from tables without plant data),
    # we fall back to the Material_Master-sourced entries already in LPP_Master.
    # LPP_Master is already populated; skip.

    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 8. REMOVE LPP columns from Material_Master (recreate table)
    # ─────────────────────────────────────────────────────────────────
    print("[8] Removing LPP columns from Material_Master...")
    c.execute("""
        CREATE TABLE Material_Master_New (
            Material_Code           VARCHAR(20) PRIMARY KEY,
            Material_Number         VARCHAR(20),
            Material_Description    TEXT        NOT NULL,
            Material_Group          VARCHAR(10) NOT NULL,
            Material_Group_Desc     VARCHAR(100),
            HSN_SAC_Code            VARCHAR(15),
            Base_UOM                VARCHAR(10) NOT NULL,
            Category                VARCHAR(20) NOT NULL,
            Standard_Lead_Time_Days INTEGER,
            Min_Order_Qty           DECIMAL(15,3),
            Safety_Stock            DECIMAL(15,3),
            Reorder_Point           DECIMAL(15,3),
            ABC_Classification      VARCHAR(1),
            Criticality             VARCHAR(10),
            MSDS_Required           BOOLEAN     DEFAULT 0,
            Spec_Document_File_ID   VARCHAR(50),
            Created_At              DATETIME    NOT NULL,
            Updated_At              DATETIME    NOT NULL
        )
    """)
    c.execute("""
        INSERT INTO Material_Master_New
        SELECT
            Material_Code, Material_Number, Material_Description, Material_Group,
            Material_Group_Desc, HSN_SAC_Code, Base_UOM, Category,
            Standard_Lead_Time_Days, Min_Order_Qty, Safety_Stock, Reorder_Point,
            ABC_Classification, Criticality, MSDS_Required, Spec_Document_File_ID,
            Created_At, Updated_At
        FROM Material_Master
    """)
    c.execute("DROP TABLE Material_Master")
    c.execute("ALTER TABLE Material_Master_New RENAME TO Material_Master")
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 9. DROP now-redundant tables
    # ─────────────────────────────────────────────────────────────────
    print("[9] Dropping redundant tables...")
    c.execute("DROP TABLE Procurement_Historical_Pricing")
    c.execute("DROP TABLE Vendor_History")
    print("    Done.")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("\nMigration complete.")


if __name__ == '__main__':
    print(f"Migrating: {DB_PATH}\n")
    with sqlite3.connect(DB_PATH) as conn:
        run(conn)
