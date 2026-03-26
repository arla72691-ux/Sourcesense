# agents/pr_03_buyer_assignment.py
import logging
import smtplib
import sys
import os
import datetime
from email.mime.text import MIMEText

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Re-using the send_email function from spec_extraction would be ideal.
# For this file-based setup, we define it again.
def send_email(to_email: str, subject: str, body: str):
    """Sends an email using the configured SMTP settings."""
    if not config.is_email_configured():
        logging.warning(f"Email not configured. Skipping email to {to_email}.")
        return False

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
            return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False

def buyer_assignment(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.03 — Buyer Assignment + DOP Routing
    """
    logging.info("Entering PR.03 - Buyer Assignment agent.")
    state['current_agent'] = "pr_03_buyer_assignment"
    errors = state.get('errors', [])
    buyer_was_assigned = False

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Consolidated_PRs WHERE PR_Status = 'Specs_Ready'")
            clusters_to_assign = cursor.fetchall()

            if not clusters_to_assign:
                logging.info("No clusters ready for buyer assignment.")
                state['buyer_assigned'] = None
                return state

            for cluster in clusters_to_assign:
                cluster_id = cluster['Consolidation_Cluster_ID']
                material_group = cluster['Material_Group']
                total_value = cluster['Total_Value']

                cursor.execute("""
                    SELECT bm.*, ad.Full_Name AS Buyer_Name, ad.Email AS Buyer_Email
                    FROM Buyer_Master bm
                    JOIN Active_Directory ad ON bm.Employee_ID = ad.Employee_ID
                    WHERE ad.Active_Status = 'Active' AND bm.Material_Group_Codes LIKE ?
                """, (f'%{material_group}%',))
                potential_buyers = cursor.fetchall()

                best_buyer = None
                lowest_ratio = float('inf')

                for buyer in potential_buyers:
                    # Verify spend limit
                    if buyer['Annual_Spend_Limit'] < total_value:
                        continue
                    
                    # Find buyer with the lowest workload ratio
                    workload_ratio = (buyer['Current_Workload'] + 1) / buyer['Max_Workload']
                    if workload_ratio < lowest_ratio:
                        lowest_ratio = workload_ratio
                        best_buyer = dict(buyer)
                
                if best_buyer:
                    buyer_id = best_buyer['Buyer_ID']
                    logging.info(f"Assigning cluster {cluster_id} to buyer {buyer_id}.")
                    
                    # Update cluster with assigned buyer
                    cursor.execute("UPDATE Consolidated_PRs SET Assigned_Buyer = ?, PR_Status = 'Buyer_Assigned', Buyer_Assigned_At = ? WHERE Consolidation_Cluster_ID = ?",
                                   (buyer_id, datetime.datetime.now().isoformat(), cluster_id))
                    
                    # Update buyer's workload
                    cursor.execute("UPDATE Buyer_Master SET Current_Workload = Current_Workload + 1 WHERE Buyer_ID = ?", (buyer_id,))

                    # DOP Routing and Approval Log
                    cursor.execute("SELECT Tier_Level, Approver_Designation FROM DOP WHERE ? BETWEEN Value_Range_Min AND Value_Range_Max", (total_value,))
                    dop_tier = cursor.fetchone()
                    if dop_tier:
                        approver_designation = dop_tier['Approver_Designation']
                        cursor.execute("SELECT Email FROM Active_Directory WHERE Designation_Code = ?", (approver_designation,))
                        approver = cursor.fetchone()
                        if approver:
                            cursor.execute("INSERT INTO Approval_Log (Entity_Type, Entity_ID, Approver_Email, Approver_Designation, Decision, Decided_At) VALUES (?, ?, ?, ?, ?, ?)",
                                           ('Cluster', cluster_id, approver['Email'], approver_designation, 'Pending', datetime.datetime.now().isoformat()))
                            logging.info(f"Approval request for {cluster_id} sent to {approver_designation} ({approver['Employee_Email']}).")
                        else:
                            errors.append(f"Could not find approver email for designation {approver_designation}.")
                    else:
                        errors.append(f"Could not determine DOP for cluster {cluster_id} with value {total_value}.")

                    # Log process event
                    cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                                   ('S2C.RFQ.03', 'Cluster', cluster_id, 'BuyerAssignment', f'Assigned to {buyer_id}', 'Agent:PR.03', datetime.datetime.now().isoformat()))

                    # Send email to buyer
                    email_subject = f"New Procurement Cluster Assigned: {cluster_id}"
                    email_body = f"Dear {best_buyer['Buyer_Name']},\n\nYou have been assigned a new procurement cluster: {cluster_id} for material group {material_group}.\n\nTotal Value: {total_value}\nPRs: {cluster['PR_Number']}\n\nPlease review and proceed with the RFQ process.\n\nThank you."
                    send_email(best_buyer['Buyer_Email'], email_subject, email_body)
                    state['buyer_assigned'] = buyer_id
                    buyer_was_assigned = True

                else:
                    # No suitable buyer found, escalate
                    logging.warning(f"No suitable buyer found for cluster {cluster_id}.")
                    errors.append(f"No buyer for cluster {cluster_id}.")
                    # In a real system, we would find the manager of the material group and email them.
                    # For now, we just log the error.

    except Exception as e:
        logging.error(f"An error occurred in Buyer Assignment: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'].extend(errors)
    if errors and not buyer_was_assigned:
        logging.error(f"Errors occurred: {errors}")

    logging.info("Exiting PR.03.")
    return state
