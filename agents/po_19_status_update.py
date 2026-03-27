# agents/po_19_status_update.py
import logging
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db, next_id

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def status_update(state: S2CState) -> S2CState:
    """
    LangGraph node: PO.19 — Status Update & Lifecycle Closure
    """
    logging.info("Entering PO.19 - Status Update agent.")
    state['current_agent'] = "status_update"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            # Find POs that have been acknowledged but not yet closed
            cursor.execute("""
                SELECT pr.PO_Ref_ID, pr.Consolidation_Cluster_ID, pr.SAP_PO_Number FROM PO_Reference pr
                JOIN Consolidated_PRs c ON pr.Consolidation_Cluster_ID = c.Consolidation_Cluster_ID
                WHERE pr.Vendor_Acknowledged_At IS NOT NULL AND c.PR_Status != 'Closed'
            """)
            pos_to_close = cursor.fetchall()

            if not pos_to_close:
                logging.info("No acknowledged POs to close out.")
                return state

            for po in pos_to_close:
                cluster_id = po['Consolidation_Cluster_ID']
                sap_po_number = po['SAP_PO_Number']
                logging.info(f"Closing lifecycle for cluster {cluster_id} (PO: {sap_po_number}).")

                cursor.execute("SELECT * FROM SAP_PO_Data WHERE SAP_PO_Number = ?", (sap_po_number,))
                sap_data = dict(cursor.fetchone())
                cursor.execute("SELECT Assigned_Buyer FROM Consolidated_PRs WHERE Consolidation_Cluster_ID = ?", (cluster_id,))
                buyer = cursor.fetchone()['Assigned_Buyer']

                # Step 4 & 5: Update cluster status to PO_Created and then Closed
                cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'PO_Created', PO_Created_At = ? WHERE Consolidation_Cluster_ID = ?",
                               (sap_data['SAP_Created_At'], cluster_id))
                cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'Closed', Closed_At = ? WHERE Consolidation_Cluster_ID = ?",
                               (datetime.datetime.now().isoformat(), cluster_id))

                # Step 6: UPDATE LPP_Master with new LPP
                cursor.execute("""
                    INSERT OR REPLACE INTO LPP_Master
                        (Material_Code, Plant, Last_Purchase_Price, Currency, Last_PO_Date, Last_Vendor_Code, Last_PO_Number, Updated_At)
                    VALUES (?, ?, ?, 'INR', ?, ?, ?, ?)
                """, (sap_data['Material_Code'], sap_data['Plant'], sap_data['Unit_Price'],
                      sap_data['SAP_Created_At'].split('T')[0], sap_data['Vendor_Code'],
                      sap_data['SAP_PO_Number'], datetime.datetime.now().isoformat()))
                logging.info(f"Updated LPP for material {sap_data['Material_Code']} to {sap_data['Unit_Price']}.")

                # Step 7: Release buyer workload
                cursor.execute("UPDATE Buyer_Master SET Current_Workload = MAX(0, Current_Workload - 1) WHERE Buyer_ID = ?", (buyer,))

                # Step 9 & 10: Notify and log final event
                logging.info(f"Notifying stakeholders about completion of PO {sap_po_number}.")
                # send_email(...) would be here

                evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
                cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?,?)",
                               (evt_id, 'S2C.PO.19', 'Cluster', cluster_id, 'Cluster_Closed', f'Procurement complete. PO {sap_po_number} acknowledged.', 'Agent:PO.19', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Status Update: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting PO.19.")
    return state
