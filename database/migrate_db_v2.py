"""
Database Migration Script v2 — Sourcesense S2C Platform

  1. Create Active_Directory (from Buyer_Master personal info + Designations_Master)
  2. Revamp Buyer_Master to buyer-specific fields only (drop personal info)
  3. Drop Designations_Master
  4. Add OEM_Part_Number, Drawing_Reference, Cross_References to Material_Master;
     migrate from Material_References; drop Material_References
  5. Create Human_Feedback table
"""

import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 's2c_sourcesense.db')


def run(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    c = conn.cursor()

    # ─────────────────────────────────────────────────────────────────
    # 1. CREATE Active_Directory
    # ─────────────────────────────────────────────────────────────────
    print("[1] Creating Active_Directory...")
    c.execute("""
        CREATE TABLE Active_Directory (
            Employee_ID         VARCHAR(20)  PRIMARY KEY,
            Full_Name           VARCHAR(100) NOT NULL,
            Email               VARCHAR(100) NOT NULL,
            Phone               VARCHAR(20),
            Department          VARCHAR(50),
            Designation         VARCHAR(100),
            Designation_Code    VARCHAR(20),
            Manager_Employee_ID VARCHAR(20),
            Active_Status       VARCHAR(15)  DEFAULT 'Active',
            Created_At          DATETIME     NOT NULL,
            Updated_At          DATETIME     NOT NULL
        )
    """)

    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')

    # --- Approvers from Designations_Master ---
    # Assign sequential Employee_IDs starting from JSW-EMP-04531
    c.execute("SELECT * FROM Designations_Master")
    designations = c.fetchall()

    # Designation_Code → (Employee_ID, title, department) mapping
    desig_meta = {
        'DES-L1-HOD-MRO': ('JSW-EMP-04531', 'Head of Department — MRO',   'Procurement — MRO'),
        'DES-L1-MGR-MRO': ('JSW-EMP-04532', 'Manager — MRO',              'Procurement — MRO'),
        'DES-L2-GM-PROC': ('JSW-EMP-04533', 'General Manager — Procurement','Procurement'),
        'DES-L3-VP-SCM':  ('JSW-EMP-04534', 'Vice President — SCM',        'Supply Chain'),
        'DES-L4-CFO':     ('JSW-EMP-04535', 'Chief Financial Officer',      'Finance'),
        'DES-L4-MD':      ('JSW-EMP-04536', 'Managing Director',            'Executive'),
        'DES-L1-HOD-CAP': ('JSW-EMP-04537', 'Head of Department — Capital', 'Procurement — Capital'),
        'DES-L1-MGR-CAP': ('JSW-EMP-04538', 'Manager — Capital',            'Procurement — Capital'),
    }

    for row in designations:
        desig_code = row[0]   # Designation_Code
        emp_name   = row[1]   # Employee_Name
        emp_email  = row[2]   # Employee_Email
        emp_id, title, dept = desig_meta.get(desig_code, (None, None, None))
        if not emp_id:
            continue
        c.execute("""
            INSERT INTO Active_Directory
                (Employee_ID, Full_Name, Email, Department, Designation,
                 Designation_Code, Active_Status, Created_At, Updated_At)
            VALUES (?, ?, ?, ?, ?, ?, 'Active', ?, ?)
        """, (emp_id, emp_name, emp_email, dept, title, desig_code, now, now))

    # Build email → Employee_ID lookup (approvers are now in)
    c.execute("SELECT Employee_ID, Email FROM Active_Directory")
    email_to_empid = {r[1]: r[0] for r in c.fetchall()}

    # --- Buyers from Buyer_Master ---
    c.execute("SELECT * FROM Buyer_Master")
    buyers = c.fetchall()
    # Columns: Buyer_ID, Employee_ID, Buyer_Name, Buyer_Email, Buyer_Phone,
    #          Department, Designation, Material_Group_Codes, Procurement_Category,
    #          Annual_Spend_Limit, Current_Workload, Max_Workload, Manager_Email,
    #          Active_Status, Created_At, Updated_At
    for row in buyers:
        (buyer_id, emp_id, name, email, phone, dept, designation,
         mg_codes, proc_cat, spend_limit, workload, max_workload,
         manager_email, active_status, created_at, updated_at) = row

        manager_emp_id = email_to_empid.get(manager_email)

        c.execute("""
            INSERT INTO Active_Directory
                (Employee_ID, Full_Name, Email, Phone, Department, Designation,
                 Manager_Employee_ID, Active_Status, Created_At, Updated_At)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (emp_id, name, email, phone, dept, designation,
              manager_emp_id, active_status, created_at, updated_at))

        email_to_empid[email] = emp_id

    # Second pass: update manager refs for buyers whose manager is another buyer
    c.execute("SELECT Employee_ID, Email FROM Active_Directory")
    email_to_empid = {r[1]: r[0] for r in c.fetchall()}

    for row in buyers:
        emp_id       = row[1]
        manager_email = row[12]
        manager_emp_id = email_to_empid.get(manager_email)
        if manager_emp_id:
            c.execute("UPDATE Active_Directory SET Manager_Employee_ID = ? WHERE Employee_ID = ?",
                      (manager_emp_id, emp_id))

    print(f"    Inserted {len(designations) + len(buyers)} employees into Active_Directory. Done.")

    # ─────────────────────────────────────────────────────────────────
    # 2. REVAMP Buyer_Master — keep only buyer-specific fields
    # ─────────────────────────────────────────────────────────────────
    print("[2] Revamping Buyer_Master...")
    c.execute("""
        CREATE TABLE Buyer_Master_New (
            Buyer_ID                VARCHAR(15)   PRIMARY KEY,
            Employee_ID             VARCHAR(20)   NOT NULL,
            Material_Group_Codes    TEXT          NOT NULL,
            Procurement_Category    VARCHAR(20)   NOT NULL,
            Annual_Spend_Limit      DECIMAL(18,2) NOT NULL,
            Current_Workload        INTEGER       DEFAULT 0,
            Max_Workload            INTEGER       DEFAULT 15
        )
    """)
    c.execute("""
        INSERT INTO Buyer_Master_New
        SELECT Buyer_ID, Employee_ID, Material_Group_Codes, Procurement_Category,
               Annual_Spend_Limit, Current_Workload, Max_Workload
        FROM Buyer_Master
    """)
    c.execute("DROP TABLE Buyer_Master")
    c.execute("ALTER TABLE Buyer_Master_New RENAME TO Buyer_Master")
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 3. DROP Designations_Master
    # ─────────────────────────────────────────────────────────────────
    print("[3] Dropping Designations_Master...")
    c.execute("DROP TABLE Designations_Master")
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 4. Merge Material_References into Material_Master
    # ─────────────────────────────────────────────────────────────────
    print("[4] Merging Material_References into Material_Master...")
    c.execute("ALTER TABLE Material_Master ADD COLUMN OEM_Part_Number  VARCHAR(100)")
    c.execute("ALTER TABLE Material_Master ADD COLUMN Drawing_Reference VARCHAR(100)")
    c.execute("ALTER TABLE Material_Master ADD COLUMN Cross_References  TEXT")

    c.execute("SELECT Material_Code, Ref_Type, Ref_Value FROM Material_References")
    for mat_code, ref_type, ref_value in c.fetchall():
        if ref_type == 'OEM_Part_Number':
            c.execute("UPDATE Material_Master SET OEM_Part_Number = ? WHERE Material_Code = ?",
                      (ref_value, mat_code))
        elif ref_type == 'Drawing_Reference':
            c.execute("UPDATE Material_Master SET Drawing_Reference = ? WHERE Material_Code = ?",
                      (ref_value, mat_code))
        elif ref_type == 'Cross_Reference':
            # Could be multiple — append comma-separated
            c.execute("SELECT Cross_References FROM Material_Master WHERE Material_Code = ?", (mat_code,))
            existing = c.fetchone()[0]
            new_val = f"{existing}, {ref_value}" if existing else ref_value
            c.execute("UPDATE Material_Master SET Cross_References = ? WHERE Material_Code = ?",
                      (new_val, mat_code))

    c.execute("DROP TABLE Material_References")
    print("    Done.")

    # ─────────────────────────────────────────────────────────────────
    # 5. CREATE Human_Feedback table
    # ─────────────────────────────────────────────────────────────────
    print("[5] Creating Human_Feedback table...")
    c.execute("""
        CREATE TABLE Human_Feedback (
            Feedback_ID      VARCHAR(20)  PRIMARY KEY,
            Process_Stage    VARCHAR(50)  NOT NULL,
            Entity_Type      VARCHAR(30),
            Entity_ID        VARCHAR(30),
            Context_Summary  TEXT,
            Response         VARCHAR(20),
            Comments         TEXT,
            Feedback_By      VARCHAR(100),
            Requested_At     DATETIME     NOT NULL,
            Resolved_At      DATETIME
        )
    """)
    print("    Done.")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("\nMigration v2 complete.")


if __name__ == '__main__':
    print(f"Migrating: {DB_PATH}\n")
    with sqlite3.connect(DB_PATH) as conn:
        run(conn)
