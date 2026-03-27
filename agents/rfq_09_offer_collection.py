# agents/rfq_09_offer_collection.py
import logging
import sys
import os
import datetime
import smtplib
from email.mime.text import MIMEText

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db, next_id
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper for simulation/external triggers ---
def record_submission(db_path, rfq_id, vendor_code, quoted_price, lead_time_days, file_content=None):
    logging.info(f"SIMULATION: Recording submission from {vendor_code} for {rfq_id}.")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        # Fix: add Submission_ID via next_id
        sub_id = next_id(cursor, 'RFQ_Submissions', 'Submission_ID', 'SUB')
        cursor.execute("INSERT INTO RFQ_Submissions (Submission_ID, RFQ_ID, Vendor_Code, Quoted_Unit_Price, Lead_Time_Days, Submitted_At) VALUES (?,?,?,?,?,?)",
                       (sub_id, rfq_id, vendor_code, quoted_price, lead_time_days, datetime.datetime.now().isoformat()))
        # In a real system, file_content would be saved to DMS and file_id stored.
        # Fix: add Event_ID via next_id
        evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
        cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?,?)",
                       (evt_id, 'S2C.RFQ.09', 'Submission', rfq_id, 'SubmissionReceived', f'Offer from {vendor_code}', vendor_code, datetime.datetime.now().isoformat()))

def simulate_submissions(db_path):
    """Auto-detect all Dispatched RFQs with no submissions yet and insert simulated offers."""
    logging.warning("SIMULATION: Inserting fake submissions for open RFQs.")
    with get_db(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT r.RFQ_ID FROM RFQ_Log r WHERE r.RFQ_Status = 'Dispatched' AND r.RFQ_ID NOT IN (SELECT DISTINCT RFQ_ID FROM RFQ_Submissions)")
        rfqs_without_submissions = [r['RFQ_ID'] for r in c.fetchall()]
        for rfq_id in rfqs_without_submissions:
            c.execute("SELECT Vendor_Code FROM RFQ_Dispatch_Log WHERE RFQ_ID = ?", (rfq_id,))
            vendors = [r['Vendor_Code'] for r in c.fetchall()]
            for i, vendor_code in enumerate(vendors):
                # Vary prices slightly per vendor
                base_price = 2500.0
                price = round(base_price * (1 + i * 0.03 - 0.01), 2)  # spread prices
                lead_time = 14 + i * 2
                record_submission(db_path, rfq_id, vendor_code, price, lead_time)

# --- Email helper ---
def send_email(to_email: str, subject: str, body: str):
    # ... (email sending logic as in other agents)
    pass

def offer_collection(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.09 — Offer Collection (Scheduled Agent)
    """
    logging.info("Entering RFQ.09 - Offer Collection agent.")
    state['current_agent'] = "rfq_09_offer_collection"
    errors = state.get('errors', [])

    # Simulate vendor submissions for any dispatched RFQs that have none yet
    simulate_submissions(state['db_path'])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT RFQ_ID, Submission_Deadline FROM RFQ_Log WHERE RFQ_Status = 'Dispatched'")
            rfqs_to_check = cursor.fetchall()

            if not rfqs_to_check:
                logging.info("No dispatched RFQs to check for submissions.")
                return state

            today = datetime.date.today()

            for rfq in rfqs_to_check:
                rfq_id = rfq['RFQ_ID']
                deadline = datetime.datetime.strptime(rfq['Submission_Deadline'], '%Y-%m-%d').date()
                days_until_deadline = (deadline - today).days

                cursor.execute("SELECT Vendor_Code FROM RFQ_Dispatch_Log WHERE RFQ_ID = ?", (rfq_id,))
                dispatched_vendors = {row['Vendor_Code'] for row in cursor.fetchall()}

                cursor.execute("SELECT Vendor_Code FROM RFQ_Submissions WHERE RFQ_ID = ?", (rfq_id,))
                submitted_vendors = {row['Vendor_Code'] for row in cursor.fetchall()}

                vendors_yet_to_submit = dispatched_vendors - submitted_vendors

                # Check if process should be closed
                all_submitted = len(vendors_yet_to_submit) == 0
                deadline_passed = days_until_deadline < -2 # Deadline + 48hr extension

                if all_submitted or deadline_passed:
                    logging.info(f"Closing submission for RFQ {rfq_id}. All submitted: {all_submitted}, Deadline passed: {deadline_passed}")
                    cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'Submissions_Closed' WHERE RFQ_ID = ?", (rfq_id,))
                    cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'RFQ_Evaluation' WHERE RFQ_ID = ?", (rfq_id,))
                    state['evaluations_complete'] = False # Reset for the next phase
                else:
                    # Send reminders
                    for vendor in vendors_yet_to_submit:
                        if days_until_deadline > 2:
                            logging.info(f"Sending reminder for RFQ {rfq_id} to {vendor}.")
                            # send_email(...) call would be here
                        elif -2 <= days_until_deadline <= 2:
                            logging.info(f"Sending deadline extension warning for RFQ {rfq_id} to {vendor}.")
                            # send_email(...) call would be here
                        else: # Deadline has passed
                            logging.warning(f"Marking {vendor} as non-responsive for RFQ {rfq_id}.")
                            # Note: The prompt asks to update Vendor_Shortlist, but that table has no such column.
                            # Logging this as an event is more appropriate.
                            cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                                           ('S2C.RFQ.09', 'Vendor', vendor, 'NonResponsive', f'Vendor did not submit for RFQ {rfq_id}', 'Agent:RFQ.09', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Offer Collection: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting RFQ.09.")
    return state
