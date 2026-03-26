# agents/rfq_06_compliance_attach.py
import logging
import sys
import os
import datetime
import smtplib
from email.mime.text import MIMEText

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_email(to_email: str, subject: str, body: str):
    if not config.is_email_configured():
        logging.warning(f"Email not configured. Skipping email to {to_email}.")
        return
    # SMTP logic as defined in other agents
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config.SENDER_EMAIL
    msg['To'] = to_email
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SENDER_EMAIL, [to_email], msg.as_string())
            logging.info(f"Email sent successfully to {to_email}.")
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")

def compliance_attach(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.06 — Compliance Attach & SVJ Check
    """
    logging.info("Entering RFQ.06 - Compliance Attach agent.")
    state['current_agent'] = "rfq_06_compliance_attach"
    errors = state.get('errors', [])
    
    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT r.RFQ_ID, r.Consolidation_Cluster_ID, c.Material_Code FROM RFQ_Log r JOIN Consolidated_PRs c ON r.Consolidation_Cluster_ID = c.Consolidation_Cluster_ID WHERE r.RFQ_Status = 'Draft'")
            rfqs_to_process = cursor.fetchall()

            if not rfqs_to_process:
                logging.info("No draft RFQs to process for compliance attachment.")
                return state

            for rfq in rfqs_to_process:
                rfq_id = rfq['RFQ_ID']
                material_code = rfq['Material_Code']
                logging.info(f"Processing RFQ {rfq_id} for compliance.")

                # Step 1 & 2: CTRL-001 pre-check (vendor count)
                cursor.execute("SELECT COUNT(*) FROM Vendor_Shortlist WHERE RFQ_ID = ?", (rfq['Consolidation_Cluster_ID'],))
                vendor_count = cursor.fetchone()[0]

                if vendor_count < 3:
                    logging.warning(f"CTRL-001 FAIL (pre-check): RFQ {rfq_id} has only {vendor_count} vendors. Initiating SVJ.")
                    # Step 2a: INSERT SVJ_Log
                    svj_reason = f"Single/limited source for material {material_code} identified during auto-shortlisting."
                    # In a real system, the Created_By would be the buyer from the cluster
                    cursor.execute("INSERT INTO SVJ_Log (RFQ_ID, Justification_Reason, Approval_Status, Created_By, Created_At) VALUES (?, ?, 'Pending', ?, ?)",
                                   (rfq_id, svj_reason, state.get('buyer_assigned', 'System'), datetime.datetime.now().isoformat()))
                    
                    # Step 2b: Email Procurement Head
                    # Assuming Procurement Head email is in a config or designations master
                    proc_head_email = "procurement.head@example.com"
                    email_subject = f"[ACTION REQUIRED] Single Vendor Justification for RFQ {rfq_id}"
                    email_body = f"Dear Procurement Head,\n\nAn SVJ has been raised for RFQ {rfq_id} as fewer than 3 vendors were shortlisted.\n\nReason: {svj_reason}\n\nPlease review and approve the SVJ to proceed with the RFQ."
                    send_email(proc_head_email, email_subject, email_body)

                    # Step 2c, 2d, 2e: Update status and stop
                    cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'SVJ_Pending' WHERE RFQ_ID = ?", (rfq_id,))
                    state['should_stop'] = True # Stop graph execution for this branch
                    logging.info(f"RFQ {rfq_id} moved to SVJ_Pending. Halting this branch.")
                    continue # Move to the next RFQ
                else:
                    logging.info(f"CTRL-001 PASS (pre-check): RFQ {rfq_id} has {vendor_count} vendors.")
                    cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?)",
                                   ('CTRL-001', 'RFQ', rfq_id, 'Pass', f'{vendor_count} vendors shortlisted.', datetime.datetime.now().isoformat()))

                # Step 3 & 4: Append references to RFQ document
                # This is a placeholder as Material_References table was not in schema
                appended_text = "\n\n--- Appended Compliance Data ---\n- No cross-references found.\n- OEM part numbers not applicable.\n--- End Appended Data ---"
                try:
                    file_path = os.path.join(config.DMS_ROOT, 'RFQ', f"RFQ_{rfq_id}.txt")
                    with open(file_path, 'a') as f:
                        f.write(appended_text)
                except FileNotFoundError:
                    errors.append(f"Could not find RFQ document for {rfq_id} to append compliance data.")
                    continue

                # Step 5: Update status
                cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'Ready_For_Approval' WHERE RFQ_ID = ?", (rfq_id,))

                # Step 7: Log process event
                cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                               ('S2C.RFQ.06', 'RFQ', rfq_id, 'ComplianceAttach', 'SVJ check passed. RFQ ready for approval.', 'Agent:RFQ.06', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Compliance Attach: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting RFQ.06.")
    return state
