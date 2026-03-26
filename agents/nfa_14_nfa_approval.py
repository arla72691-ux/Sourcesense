# agents/nfa_14_nfa_approval.py
import logging
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Simulates the webhook response and subsequent logic
def handle_approval_response(db_path, nfa_id, tier, decision):
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""UPDATE Approval_Log SET Decision = ?, Decided_At = ?
                          WHERE Entity_Type = 'NFA' AND Entity_ID = ? AND Tier_Level = ?""",
                       (decision, datetime.datetime.now().isoformat(), nfa_id, tier))
        if decision == 'Rejected':
            cursor.execute("UPDATE NFA_Log SET NFA_Status = 'Rejected' WHERE NFA_ID = ?", (nfa_id,))
            # Notify buyer, etc.
            return False # Stop chain

        # Check if more tiers are pending
        cursor.execute("""SELECT Tier_Level FROM Approval_Log
                          WHERE Entity_Type = 'NFA' AND Entity_ID = ? AND Decision = 'Pending'
                          ORDER BY Tier_Level ASC""", (nfa_id,))
        next_tier = cursor.fetchone()
        if next_tier:
            # Trigger email to next tier (omitted for sim)
            logging.info(f"NFA {nfa_id} Tier {tier} approved. Triggering next tier {next_tier['Tier_Level']}.")
            return True # More tiers to go
        else:
            # Last tier approved
            cursor.execute("UPDATE NFA_Log SET NFA_Status = 'Approved' WHERE NFA_ID = ?", (nfa_id,))
            cursor.execute("UPDATE Consolidated_PRs SET NFA_Status = 'Approved', NFA_Approved_At = ? WHERE NFA_ID = (SELECT NFA_ID FROM NFA_Log WHERE NFA_ID = ?)",
                           (datetime.datetime.now().isoformat(), nfa_id))
            logging.info(f"Final approval for NFA {nfa_id} received. Process complete.")
            return False # End of chain

def simulate_nfa_approval(db_path, nfa_id):
    logging.warning(f"SIMULATION: Auto-approving all tiers for NFA {nfa_id}.")
    more_tiers = True
    while more_tiers:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT Tier_Level FROM Approval_Log
                              WHERE Entity_Type = 'NFA' AND Entity_ID = ? AND Decision = 'Pending'
                              ORDER BY Tier_Level ASC LIMIT 1""", (nfa_id,))
            pending_tier = cursor.fetchone()
            if pending_tier:
                more_tiers = handle_approval_response(db_path, nfa_id, pending_tier['Tier_Level'], 'Approved')
            else:
                more_tiers = False
    return True

def nfa_approval(state: S2CState) -> S2CState:
    """
    LangGraph node: NFA.14 — NFA Approval
    """
    logging.info("Entering NFA.14 - NFA Approval agent.")
    state['current_agent'] = "nfa_approval"
    errors = state.get('errors', [])
    state['nfa_approved'] = False

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM NFA_Log WHERE NFA_Status = 'Draft'")
            nfas_to_approve = cursor.fetchall()

            if not nfas_to_approve:
                logging.info("No draft NFAs to process for approval.")
                return state

            for nfa in nfas_to_approve:
                nfa_id = nfa['NFA_ID']
                total_value = nfa['Total_NFA_Value']
                logging.info(f"Initiating approval chain for NFA {nfa_id} with value {total_value}.")

                # Step 3: Build approval chain
                cursor.execute("SELECT Tier_Level, Approver_Designation FROM DOP WHERE ? BETWEEN Value_Range_Min AND Value_Range_Max ORDER BY Tier_Level ASC", (total_value,))
                approval_chain = cursor.fetchall()
                if nfa['Price_Vs_LPP_Status'] == 'Above_LPP':
                    # Add CFO if not already present
                    if not any(a['Approver_Designation'] == 'DES-CFO' for a in approval_chain):
                         approval_chain.append({'Tier_Level': 99, 'Approver_Designation': 'DES-CFO'}) # T99 for CFO

                if not approval_chain: continue

                # Insert all pending approvals into the unified Approval_Log
                c2 = conn.cursor()
                c2.execute("SELECT MAX(CAST(SUBSTR(Approval_ID,6) AS INTEGER)) FROM Approval_Log")
                appr_seq = (c2.fetchone()[0] or 0) + 1
                for tier in approval_chain:
                    cursor.execute("""INSERT INTO Approval_Log
                                      (Approval_ID, Entity_Type, Entity_ID, Approver_Designation, Decision, Tier_Level)
                                      VALUES (?, 'NFA', ?, ?, 'Pending', ?)""",
                                   (f"APPR-{appr_seq:04d}", nfa_id,
                                    tier['Approver_Designation'], tier['Tier_Level']))
                    appr_seq += 1

                # Start the chain by emailing the first tier (simulated)
                logging.info(f"Approval chain for {nfa_id} created. Notifying first tier.")
                
                # Update NFA status
                cursor.execute("UPDATE NFA_Log SET NFA_Status = 'Approval_Pending' WHERE NFA_ID = ?", (nfa_id,))

                # For testing, run the full approval simulation
                if simulate_nfa_approval(state['db_path'], nfa_id):
                    state['nfa_approved'] = True
    
    except Exception as e:
        logging.error(f"An error occurred in NFA Approval: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting NFA.14.")
    return state
