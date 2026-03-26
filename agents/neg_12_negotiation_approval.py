# agents/neg_12_negotiation_approval.py
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

# This function simulates the logic that would run inside a webhook handler
def handle_bofo_response(db_path, rfq_id, vendor_code, bafo_price):
    logging.info(f"Handling BAFO response for RFQ {rfq_id} from {vendor_code} with price {bafo_price}.")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        # Update the negotiated price
        cursor.execute("UPDATE Negotiation_Shortlist_Approval SET Negotiated_Price = ? WHERE RFQ_ID = ? AND Vendor_Code = ?",
                       (bafo_price, rfq_id, vendor_code))
        
        # For simulation, we will auto-approve and set the state for the next agent
        cursor.execute("UPDATE Negotiation_Shortlist_Approval SET Approval_Status = 'Approved' WHERE RFQ_ID = ?", (rfq_id,))
        cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'Negotiation_Approved' WHERE RFQ_ID = ?", (rfq_id,))
        logging.info(f"BAFO for RFQ {rfq_id} has been auto-approved for simulation.")
        return True, bafo_price
    return False, None

def simulate_negotiation_approval(state: S2CState):
    """Finds a negotiation 'Under_Negotiation' and simulates an approved BAFO."""
    logging.warning("SIMULATION: Running negotiation approval simulation.")
    with get_db(state['db_path']) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.RFQ_ID, n.Vendor_Code, s.Quoted_Unit_Price FROM RFQ_Log r 
            JOIN Negotiation_Shortlist_Approval n ON r.RFQ_ID = n.RFQ_ID
            JOIN RFQ_Submissions s ON r.RFQ_ID = s.RFQ_ID AND n.Vendor_Code = s.Vendor_Code
            WHERE r.RFQ_Status = 'Under_Negotiation' AND n.Approval_Status = 'Pending'
        """)
        negotiation_to_sim = cursor.fetchone()

        if negotiation_to_sim:
            rfq_id = negotiation_to_sim['RFQ_ID']
            vendor_code = negotiation_to_sim['Vendor_Code']
            original_quote = negotiation_to_sim['Quoted_Unit_Price']
            # Simulate a 5% price reduction
            bafo_price = original_quote * 0.95
            
            approved, final_price = handle_bofo_response(state['db_path'], rfq_id, vendor_code, bafo_price)
            if approved:
                state['negotiated_price'] = final_price
                state['rfq_id'] = rfq_id # Pass rfq_id to the next state
                return True
    return False

def negotiation_approval(state: S2CState) -> S2CState:
    """
    LangGraph node: NEG.12 — Negotiation Approval
    In a real system, this node would be a persistent state waiting for a webhook.
    For this simulation, it actively simulates the approval process.
    """
    logging.info("Entering NEG.12 - Negotiation Approval agent.")
    state['current_agent'] = "negotiation_approval"
    errors = state.get('errors', [])
    state['nfa_approved'] = False # Default state

    try:
        # The graph will only proceed if a BAFO is approved. We simulate that here.
        was_approved = simulate_negotiation_approval(state)

        if not was_approved:
            logging.info("No pending negotiations found to simulate approval.")
            # In a real scenario, we would simply END here and wait.
            state['should_stop'] = True
        else:
            logging.info("Negotiation successfully approved (simulated). Ready for NFA generation.")

    except Exception as e:
        logging.error(f"An error occurred in Negotiation Approval: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting NEG.12.")
    return state
