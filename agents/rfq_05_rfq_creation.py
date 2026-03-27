# agents/rfq_05_rfq_creation.py
import logging
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db, next_id
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_next_business_day(start_date, days_to_add):
    """Calculates a future date by adding business days."""
    current_date = start_date
    while days_to_add > 0:
        current_date += datetime.timedelta(days=1)
        weekday = current_date.weekday()
        if weekday >= 5: # Saturday or Sunday
            continue
        days_to_add -= 1
    return current_date

def rfq_creation(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.05 — RFQ Creation
    """
    logging.info("Entering RFQ.05 - RFQ Creation agent.")
    state['current_agent'] = "rfq_05_rfq_creation"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Consolidated_PRs WHERE PR_Status = 'Vendors_Shortlisted'")
            clusters_to_process = cursor.fetchall()

            if not clusters_to_process:
                logging.info("No clusters ready for RFQ creation.")
                return state

            for cluster in clusters_to_process:
                cluster_id = cluster['Consolidation_Cluster_ID']
                logging.info(f"Creating RFQ for cluster {cluster_id}.")

                # Step 2: Set default payment terms if null
                payment_terms = cluster['Payment_Terms']
                if not payment_terms:
                    if cluster['Capex_Opex'] == 'CAPEX':
                        payment_terms = "Net 45 days from GRN"
                    elif cluster['Total_Value'] < 500000:
                        payment_terms = "Net 30 days from GRN"
                    else:
                        payment_terms = "Net 45 days from GRN"

                    # Step 3: Update cluster with new terms
                    cursor.execute("UPDATE Consolidated_PRs SET Payment_Terms = ?, Comm_Terms_Received_At = ? WHERE Consolidation_Cluster_ID = ?",
                                   (payment_terms, datetime.datetime.now().isoformat(), cluster_id))

                # Step 4: Generate RFQ_ID
                year = datetime.date.today().year
                cursor.execute("SELECT COUNT(*) FROM RFQ_Log WHERE RFQ_ID LIKE ?", (f"RFQ-{year}-%",))
                seq = cursor.fetchone()[0] + 1
                rfq_id = f"RFQ-{year}-{seq:05d}"

                # Step 5: Set submission deadline
                submission_deadline = get_next_business_day(datetime.date.today(), 7)

                # Step 6 & 7: Insert into RFQ_Log
                eval_criteria = "Tech: 40%, Comm: 60%, Min score: 70"
                cursor.execute("""
                    INSERT INTO RFQ_Log (RFQ_ID, Consolidation_Cluster_ID, RFQ_Status, Evaluation_Criteria, Submission_Deadline, Created_By, Created_At)
                    VALUES (?, ?, 'Draft', ?, ?, ?, ?)
                """, (rfq_id, cluster_id, eval_criteria, submission_deadline.isoformat(), state['buyer_assigned'], datetime.datetime.now().isoformat()))

                # Step 8: Generate RFQ document text (simple template)
                rfq_doc_content = f"""--- RFQ DOCUMENT ---
COMPANY: JSW Steel (Simulation)
RFQ NUMBER: {rfq_id}
DATE: {datetime.date.today().isoformat()}

MATERIAL DETAILS:
  Code: {cluster['Material_Code']}
  Description: {cluster['Description']}
  Specifications: {cluster['Long_Text_Specifications']}
  Quantity: {cluster['Quantity']}
  UOM: {cluster['UOM_Base']}

COMMERCIAL TERMS:
  Delivery Date Required: {cluster['Delivery_Date']}
  Payment Terms: {payment_terms}
  Incoterms: FOR Destination

SUBMISSION INSTRUCTIONS:
  Evaluation Criteria: {eval_criteria}
  Submission Deadline: {submission_deadline.isoformat()}
--- END OF DOCUMENT ---"""

                # Step 9: Save RFQ doc to DMS
                dms_rfq_path = os.path.join(config.DMS_ROOT, 'RFQ')
                os.makedirs(dms_rfq_path, exist_ok=True)
                file_path = os.path.join(dms_rfq_path, f"RFQ_{rfq_id}.txt")
                with open(file_path, 'w') as f:
                    f.write(rfq_doc_content)
                logging.info(f"RFQ document saved to {file_path}")

                # Step 11: Update cluster status
                cursor.execute("UPDATE Consolidated_PRs SET RFQ_ID = ?, RFQ_Generated_At = ?, PR_Status = 'RFQ_Generated' WHERE Consolidation_Cluster_ID = ?",
                               (rfq_id, datetime.datetime.now().isoformat(), cluster_id))

                # Backfill Vendor_Shortlist rows that were inserted with RFQ_ID = NULL
                # (pipeline runs sequentially, so all NULLs belong to the current batch)
                cursor.execute("UPDATE Vendor_Shortlist SET RFQ_ID = ? WHERE RFQ_ID IS NULL", (rfq_id,))

                # Step 12: Log Process Event
                evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
                cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?,?)",
                               (evt_id, 'S2C.RFQ.05', 'RFQ', rfq_id, 'Creation', f'RFQ Draft created for cluster {cluster_id}', 'Agent:RFQ.05', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in RFQ Creation: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting RFQ.05.")
    return state
