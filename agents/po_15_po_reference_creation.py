# agents/po_15_po_reference_creation.py
import logging
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def po_reference_creation(state: S2CState) -> S2CState:
    """
    LangGraph node: PO.15 — PO Reference Creation
    """
    logging.info("Entering PO.15 - PO Reference Creation agent.")
    state['current_agent'] = "po_reference_creation"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            # Step 1: Find approved NFAs without a PO Reference
            cursor.execute("""
                SELECT n.NFA_ID, n.Consolidation_Cluster_ID, c.Assigned_Buyer FROM NFA_Log n
                JOIN Consolidated_PRs c ON n.Consolidation_Cluster_ID = c.Consolidation_Cluster_ID
                WHERE n.NFA_Status = 'Approved' AND n.NFA_ID NOT IN (SELECT NFA_ID FROM PO_Reference WHERE NFA_ID IS NOT NULL)
            """)
            nfas_to_process = cursor.fetchall()

            if not nfas_to_process:
                logging.info("No approved NFAs ready for PO reference creation.")
                return state

            for nfa in nfas_to_process:
                nfa_id = nfa['NFA_ID']
                # Step 2a & 2b: Double-check all approval tiers are met
                # This is a good practice check, though our simulation approves all at once.
                cursor.execute("SELECT COUNT(*) FROM NFA_Approval_Log WHERE NFA_ID = ?", (nfa_id,))
                total_tiers = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM NFA_Approval_Log WHERE NFA_ID = ? AND Decision = 'Approved'", (nfa_id,))
                approved_tiers = cursor.fetchone()[0]

                if total_tiers != approved_tiers:
                    logging.warning(f"Skipping NFA {nfa_id}: Not all approval tiers are marked 'Approved'. Total: {total_tiers}, Approved: {approved_tiers}")
                    continue

                # Step 2c: Create PO Reference
                year = datetime.date.today().year
                cursor.execute("SELECT COUNT(*) FROM PO_Reference WHERE PO_Ref_ID LIKE ?", (f"POREF-{year}-%",))
                seq = cursor.fetchone()[0] + 1
                po_ref_id = f"POREF-{year}-{seq:05d}"

                cursor.execute("""
                    INSERT INTO PO_Reference (PO_Ref_ID, NFA_ID, Consolidation_Cluster_ID, API_Call_Status, Created_By, Created_At)
                    VALUES (?, ?, ?, 'Pending', ?, ?)
                """, (po_ref_id, nfa_id, nfa['Consolidation_Cluster_ID'], nfa['Assigned_Buyer'], datetime.datetime.now().isoformat()))
                
                # Step 3 & 4: Update state and log
                state["po_ref_id"] = po_ref_id
                logging.info(f"Created PO_Reference {po_ref_id} for NFA {nfa_id}.")
                cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                               ('S2C.PO.19', 'PO_Reference', po_ref_id, 'PO_Reference_Created', f'Internal PO reference created for NFA {nfa_id}', 'Agent:PO.15', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in PO Reference Creation: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting PO.15.")
    return state
