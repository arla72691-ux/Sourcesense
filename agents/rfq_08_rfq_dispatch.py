# agents/rfq_08_rfq_dispatch.py
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

def send_email(to_email: str, subject: str, body: str, attachment_path: str = None):
    if not config.is_email_configured():
        logging.warning(f"Email not configured. Skipping email to {to_email}.")
        return
    # In a real implementation, this would handle attachments properly.
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config.SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SENDER_EMAIL, [to_email], msg.as_string())
            logging.info(f"RFQ dispatched via email to {to_email}.")
    except Exception as e:
        logging.error(f"Failed to dispatch RFQ to {to_email}: {e}")

def rfq_dispatch(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.08 — RFQ Dispatch
    """
    logging.info("Entering RFQ.08 - RFQ Dispatch agent.")
    state['current_agent'] = "rfq_08_rfq_dispatch"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT RFQ_ID, Consolidation_Cluster_ID FROM RFQ_Log WHERE RFQ_Status = 'Approved'")
            rfqs_to_dispatch = cursor.fetchall()

            if not rfqs_to_dispatch:
                logging.info("No approved RFQs to dispatch.")
                return state

            for rfq in rfqs_to_dispatch:
                rfq_id = rfq['RFQ_ID']
                cluster_id = rfq['Consolidation_Cluster_ID']

                # Step 1 & 2: CTRL-001 final enforcement
                cursor.execute("SELECT Vendor_Code FROM Vendor_Shortlist WHERE RFQ_ID = ?", (rfq_id,))
                shortlisted_vendors = cursor.fetchall()
                vendor_count = len(shortlisted_vendors)

                if vendor_count < 3:
                    cursor.execute("SELECT Approval_Status FROM SVJ_Log WHERE RFQ_ID = ?", (rfq_id,))
                    svj = cursor.fetchone()
                    if not svj or svj['Approval_Status'] != 'Approved':
                        details = f"Dispatch blocked for RFQ {rfq_id}: {vendor_count} vendors and no approved SVJ."
                        logging.error(f"CTRL-001 FAIL (final): {details}")
                        comp_id = next_id(cursor, 'Compliance_Log', 'Compliance_ID', 'COMP')
                        cursor.execute("INSERT INTO Compliance_Log (Compliance_ID, Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?,?)",
                                       (comp_id, 'CTRL-001', 'RFQ', rfq_id, 'Fail', details, datetime.datetime.now().isoformat()))
                        errors.append(details)
                        continue # Stop processing this RFQ
                    else:
                        logging.warning(f"CTRL-001 proceeding with {vendor_count} vendors for RFQ {rfq_id} due to approved SVJ.")

                # If we are here, compliance is passed.
                comp_id = next_id(cursor, 'Compliance_Log', 'Compliance_ID', 'COMP')
                cursor.execute("INSERT INTO Compliance_Log (Compliance_ID, Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?,?)",
                               (comp_id, 'CTRL-001', 'RFQ', rfq_id, 'Pass', f'Dispatching to {vendor_count} vendors.', datetime.datetime.now().isoformat()))

                # Step 3: Dispatch to each vendor
                rfq_doc_path = os.path.join(config.DMS_ROOT, 'RFQ', f"RFQ_{rfq_id}.txt")
                try:
                    with open(rfq_doc_path, 'r') as f:
                        rfq_content = f.read()
                except FileNotFoundError:
                    errors.append(f"RFQ document not found for dispatch: {rfq_doc_path}")
                    continue

                for vendor_row in shortlisted_vendors:
                    vendor_code = vendor_row['Vendor_Code']
                    # Simulate vendor email
                    vendor_email = f"{vendor_code.lower()}@vendor.com"
                    email_subject = f"Request for Quotation: {rfq_id}"

                    send_email(vendor_email, email_subject, rfq_content, attachment_path=rfq_doc_path)

                    # Log the dispatch — Fix: add Dispatch_ID via next_id
                    disp_id = next_id(cursor, 'RFQ_Dispatch_Log', 'Dispatch_ID', 'DISP')
                    cursor.execute("INSERT INTO RFQ_Dispatch_Log (Dispatch_ID, RFQ_ID, Vendor_Code, Dispatch_Method, Dispatched_At, Delivery_Status) VALUES (?, ?, ?, 'Email', ?, 'Sent')",
                                   (disp_id, rfq_id, vendor_code, datetime.datetime.now().isoformat()))

                # Step 4 & 5: Update statuses
                cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'Dispatched' WHERE RFQ_ID = ?", (rfq_id,))
                cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'RFQ_Dispatched', RFQ_Dispatched_At = ? WHERE Consolidation_Cluster_ID = ?",
                               (datetime.datetime.now().isoformat(), cluster_id))

                # Step 7: Log process event
                logging.info(f"RFQ {rfq_id} dispatched to {vendor_count} vendors.")
                evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
                cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?,?)",
                               (evt_id, 'S2C.RFQ.08', 'RFQ', rfq_id, 'Dispatch', f'RFQ sent to {vendor_count} vendors.', 'Agent:RFQ.08', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in RFQ Dispatch: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting RFQ.08.")
    return state
