# agents/rfq_07_rfq_approval.py
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

def send_email(to_email: str, subject: str, body: str):
    if not config.is_email_configured():
        logging.warning(f"Email not configured. Skipping email to {to_email}.")
        return
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config.SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SENDER_EMAIL, [to_email], msg.as_string())
    except Exception as e:
        logging.error(f"Failed to send approval email to {to_email}: {e}")

def simulate_approval(rfq_id: str, db_path: str):
    """For testing: Sets all pending approvals for an RFQ to 'Approved'."""
    logging.warning(f"SIMULATION: Auto-approving all requests for RFQ {rfq_id}.")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Approval_Log SET Decision = 'Approved', Decided_At = ? WHERE Entity_Type = 'RFQ' AND Entity_ID = ? AND Decision = 'Pending'",
                       (datetime.datetime.now().isoformat(), rfq_id))
        # Also update the main RFQ status as if the webhook handler did
        cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'Approved' WHERE RFQ_ID = ?", (rfq_id,))
    logging.warning(f"SIMULATION: RFQ {rfq_id} status set to Approved.")

def rfq_approval(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.07 — RFQ Approval
    """
    logging.info("Entering RFQ.07 - RFQ Approval agent.")
    state['current_agent'] = "rfq_07_rfq_approval"
    errors = state.get('errors', [])

    rfq_ids_to_simulate = []
    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.RFQ_ID, c.Total_Value, c.Description
                FROM RFQ_Log r
                JOIN Consolidated_PRs c ON r.Consolidation_Cluster_ID = c.Consolidation_Cluster_ID
                WHERE r.RFQ_Status = 'Ready_For_Approval'
            """,)
            rfqs_to_process = cursor.fetchall()

            if not rfqs_to_process:
                logging.info("No RFQs ready for approval.")
                return state

            for rfq in rfqs_to_process:
                rfq_id = rfq['RFQ_ID']
                total_value = rfq['Total_Value']
                logging.info(f"Processing RFQ {rfq_id} for approval with value {total_value}.")

                # Step 2: Query DOP table
                cursor.execute("SELECT Approver_Designation FROM DOP WHERE ? BETWEEN Value_Range_Min AND Value_Range_Max", (total_value,))
                approvers = cursor.fetchall()

                if not approvers:
                    errors.append(f"No DOP tier found for RFQ {rfq_id} with value {total_value}.")
                    continue

                # Step 3: Insert approval logs and send emails
                for approver_info in approvers:
                    designation = approver_info['Approver_Designation']
                    # Fix: Designations_Master no longer exists; use Active_Directory with Email column
                    cursor.execute("SELECT Email FROM Active_Directory WHERE Designation_Code = ?", (designation,))
                    approver = cursor.fetchone()
                    if not approver:
                        errors.append(f"No employee found for designation {designation} for RFQ {rfq_id}.")
                        continue

                    # Fix: use 'Email' column (not 'Employee_Email')
                    approver_email = approver['Email']
                    # Fix: add Approval_ID via next_id; remove non-existent Created_At column
                    appr_id = next_id(cursor, 'Approval_Log', 'Approval_ID', 'APPR')
                    cursor.execute("INSERT INTO Approval_Log (Approval_ID, Entity_Type, Entity_ID, Approver_Email, Approver_Designation, Decision) VALUES (?, ?, ?, ?, ?, 'Pending')",
                                   (appr_id, 'RFQ', rfq_id, approver_email, designation))

                    email_subject = f"[ACTION REQUIRED] RFQ {rfq_id} Approval — {rfq['Description']}"
                    email_body = f"""Dear Approver,\n\nPlease review and approve RFQ {rfq_id}.\n
Details:\n- Value: {total_value}\n- Description: {rfq['Description']}\n\nAn approval link would be here in a real system.
"""
                    send_email(approver_email, email_subject, email_body)

                # Step 4: CTRL-005
                comp_id = next_id(cursor, 'Compliance_Log', 'Compliance_ID', 'COMP')
                cursor.execute("INSERT INTO Compliance_Log (Compliance_ID, Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?,?)",
                               (comp_id, 'CTRL-005', 'RFQ', rfq_id, 'Pass', f'DOP check complete. {len(approvers)} approvers notified.', datetime.datetime.now().isoformat()))

                # Step 5: Update RFQ status
                cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'Approval_Pending' WHERE RFQ_ID = ?", (rfq_id,))
                logging.info(f"RFQ {rfq_id} moved to Approval_Pending.")

                # Collect IDs to simulate after outer connection is committed and closed
                rfq_ids_to_simulate.append(rfq_id)

    except Exception as e:
        logging.error(f"An error occurred in RFQ Approval: {e}", exc_info=True)
        errors.append(str(e))

    # Simulate approvals AFTER outer connection is closed to avoid DB locking
    for rfq_id in rfq_ids_to_simulate:
        try:
            simulate_approval(rfq_id, state['db_path'])
        except Exception as e:
            logging.error(f"Failed to simulate approval for RFQ {rfq_id}: {e}", exc_info=True)
            errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting RFQ.07.")
    return state
