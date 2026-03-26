"""
Database Migration Script v3 — Sourcesense S2C Platform

  1. Add Commercial_Terms columns to Consolidated_PRs
  2. Create Comm_Requests table
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 's2c_sourcesense.db')


def run(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    c = conn.cursor()

    # ─────────────────────────────────────────────────────────────────
    # 1. Add commercial terms columns to Consolidated_PRs
    # ─────────────────────────────────────────────────────────────────
    print("[1] Adding commercial terms columns to Consolidated_PRs...")

    new_columns = [
        ("Commercial_Terms_Status", "VARCHAR(30)"),
        ("Comm_Request_ID",         "VARCHAR(30)"),
        ("Unit_Price",              "DECIMAL(15,4)"),
        ("HSN_Code",                "VARCHAR(15)"),
        ("LCITC_Percent",           "DECIMAL(5,2)  DEFAULT 0.0"),
        ("PnF_Percent",             "DECIMAL(5,2)  DEFAULT 0.0"),
        ("Freight_Percent",         "DECIMAL(5,2)  DEFAULT 0.0"),
        ("GST_Percent",             "DECIMAL(5,2)  DEFAULT 18.0"),
        ("Incoterms",               "VARCHAR(30)"),
        ("Ship_To",                 "VARCHAR(100)"),
    ]

    c.execute("PRAGMA table_info(Consolidated_PRs)")
    existing = {row[1] for row in c.fetchall()}

    for col_name, col_def in new_columns:
        if col_name not in existing:
            c.execute(f"ALTER TABLE Consolidated_PRs ADD COLUMN {col_name} {col_def}")
            print(f"    Added column: {col_name}")
        else:
            print(f"    Column already exists (skipped): {col_name}")

    # ─────────────────────────────────────────────────────────────────
    # 2. Create Comm_Requests table
    # ─────────────────────────────────────────────────────────────────
    print("[2] Creating Comm_Requests table...")

    c.execute("""
        CREATE TABLE IF NOT EXISTS Comm_Requests (
            Comm_Request_ID  VARCHAR(30)   PRIMARY KEY,
            Buyer_ID         VARCHAR(15)   NOT NULL,
            Buyer_Email      VARCHAR(100)  NOT NULL,
            Cluster_IDs      TEXT          NOT NULL,
            Status           VARCHAR(30)   NOT NULL DEFAULT 'Pending_Response',
            Sent_At          DATETIME      NOT NULL,
            Received_At      DATETIME,
            Notes            TEXT
        )
    """)
    print("    Done.")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("\nMigration v3 complete.")


if __name__ == '__main__':
    print(f"Migrating: {DB_PATH}\n")
    with sqlite3.connect(DB_PATH) as conn:
        run(conn)
