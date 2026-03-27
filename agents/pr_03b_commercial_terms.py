# agents/pr_03b_commercial_terms.py
import logging
import json
import sys
import os
import datetime
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db, next_id
from feedback import request_human_feedback
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default simulation values for commercial terms
_SIM_PNF_PCT      = 1.0    # Packing & Forwarding %
_SIM_FREIGHT_PCT  = 2.0    # Freight %
_SIM_GST_PCT      = 18.0   # GST %
_SIM_LCITC_PCT    = 0.0    # Local Charges incl. TDS/TCS %
_SIM_INCOTERMS    = "DDP"  # Delivered Duty Paid (supply only)
_SIM_PAYMENT_TERM = "Net 30 days from GRN"


def _generate_comm_request_id() -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"COMM-{ts}-{suffix}"


def _send_comm_request_email(buyer_email: str, buyer_name: str,
                              comm_request_id: str, clusters: list) -> bool:
    """Sends commercial terms request email. Returns True if sent, False if skipped."""
    if not config.is_email_configured():
        logging.warning(f"Email not configured. Skipping comm terms email to {buyer_email}.")
        return False

    cluster_table = "\n".join(
        f"  {i+1}. {cl['Consolidation_Cluster_ID']} | {cl['Description']} "
        f"| Qty: {cl['Quantity']} {cl['UOM_Base']} | Plant: {cl['Plant']}"
        for i, cl in enumerate(clusters)
    )

    subject = f"[COMM REQUEST {comm_request_id}] Commercial Terms Required"
    body = (
        f"Dear {buyer_name},\n\n"
        f"Please provide commercial terms for the following procurement clusters "
        f"(Request ID: {comm_request_id}):\n\n"
        f"{cluster_table}\n\n"
        f"For each cluster, please fill in:\n"
        f"  - Unit Price (INR)\n"
        f"  - HSN/SAC Code\n"
        f"  - LCITC %\n"
        f"  - P&F %\n"
        f"  - Freight %\n"
        f"  - GST %\n"
        f"  - Payment Terms\n"
        f"  - Incoterms\n"
        f"  - Ship-To Address\n\n"
        f"Reply to this email with subject line unchanged and the completed template attached.\n\n"
        f"Thank you."
    )

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config.SENDER_EMAIL
    msg['To'] = buyer_email

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SENDER_EMAIL, [buyer_email], msg.as_string())
        logging.info(f"Comm terms request {comm_request_id} emailed to {buyer_email}.")
        return True
    except Exception as e:
        logging.error(f"Failed to send comm terms email to {buyer_email}: {e}")
        return False


def _simulate_comm_terms(cursor, cluster: dict) -> dict:
    """
    Auto-generates commercial terms for a cluster in simulation mode.
    Uses LPP_Master for unit price and Material_Master for HSN code.
    """
    material_code = cluster['Material_Code']
    plant         = cluster['Plant']
    quantity      = cluster['Quantity']

    # Unit price: from LPP_Master first, else derive from Total_Value
    cursor.execute(
        "SELECT Last_Purchase_Price FROM LPP_Master WHERE Material_Code = ? AND Plant = ?",
        (material_code, plant)
    )
    lpp_row = cursor.fetchone()
    if lpp_row and lpp_row['Last_Purchase_Price']:
        unit_price = float(lpp_row['Last_Purchase_Price'])
    else:
        unit_price = float(cluster['Total_Value']) / float(quantity) if quantity else 0.0

    # HSN code: from Material_Master
    cursor.execute(
        "SELECT HSN_SAC_Code FROM Material_Master WHERE Material_Code = ?",
        (material_code,)
    )
    hsn_row = cursor.fetchone()
    hsn_code = hsn_row['HSN_SAC_Code'] if hsn_row and hsn_row['HSN_SAC_Code'] else "8421"

    return {
        'unit_price':     round(unit_price, 4),
        'hsn_code':       hsn_code,
        'lcitc_percent':  _SIM_LCITC_PCT,
        'pnf_percent':    _SIM_PNF_PCT,
        'freight_percent':_SIM_FREIGHT_PCT,
        'gst_percent':    _SIM_GST_PCT,
        'payment_terms':  _SIM_PAYMENT_TERM,
        'incoterms':      _SIM_INCOTERMS,
        'ship_to':        plant,
    }


def commercial_terms_finalisation(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.03b — Commercial Terms Finalisation

    Groups clusters (PR_Status = 'Buyer_Assigned') by assigned buyer, dispatches
    a commercial terms request email (or simulates it), then populates term fields
    in Consolidated_PRs and advances status to 'Comm_Terms_Received'.
    """
    logging.info("Entering PR.03b - Commercial Terms Finalisation agent.")
    state['current_agent'] = "commercial_terms_finalisation"
    errors = state.get('errors', [])
    state['comm_terms_received'] = False

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()

            # Fetch all clusters awaiting commercial terms
            # Assigned_Buyer stores the buyer's email address directly
            cursor.execute("""
                SELECT cp.*, ad.Full_Name AS Buyer_Name, ad.Email AS Buyer_Email
                FROM Consolidated_PRs cp
                JOIN Active_Directory ad ON cp.Assigned_Buyer = ad.Email
                WHERE cp.PR_Status = 'Buyer_Assigned'
                AND (cp.Commercial_Terms_Status IS NULL OR cp.Commercial_Terms_Status = 'Pending_Response')
            """)
            clusters = cursor.fetchall()

            if not clusters:
                logging.info("No clusters awaiting commercial terms.")
                return state

            # Group clusters by buyer
            buyer_groups: dict[str, dict] = {}
            for cluster in clusters:
                buyer_id = cluster['Assigned_Buyer']
                if buyer_id not in buyer_groups:
                    buyer_groups[buyer_id] = {
                        'buyer_email': cluster['Buyer_Email'],
                        'buyer_name':  cluster['Buyer_Name'],
                        'clusters':    [],
                    }
                buyer_groups[buyer_id]['clusters'].append(dict(cluster))

            for buyer_id, group in buyer_groups.items():
                buyer_email  = group['buyer_email']
                buyer_name   = group['buyer_name']
                buyer_clusters = group['clusters']
                cluster_ids  = [cl['Consolidation_Cluster_ID'] for cl in buyer_clusters]

                comm_request_id = _generate_comm_request_id()
                now = datetime.datetime.now().isoformat()

                # Log the request in Comm_Requests
                cursor.execute("""
                    INSERT INTO Comm_Requests
                        (Comm_Request_ID, Buyer_ID, Buyer_Email, Cluster_IDs, Status, Sent_At)
                    VALUES (?, ?, ?, ?, 'Pending_Response', ?)
                """, (comm_request_id, buyer_id, buyer_email,
                      ",".join(cluster_ids), now))

                # Mark clusters as pending
                for cluster_id in cluster_ids:
                    cursor.execute("""
                        UPDATE Consolidated_PRs
                        SET Commercial_Terms_Status = 'Pending_Response',
                            Comm_Request_ID = ?
                        WHERE Consolidation_Cluster_ID = ?
                    """, (comm_request_id, cluster_id))

                # Dispatch email (skipped if not configured)
                _send_comm_request_email(buyer_email, buyer_name,
                                         comm_request_id, buyer_clusters)

                logging.info(
                    f"Comm terms request {comm_request_id} dispatched to {buyer_id} "
                    f"({buyer_email}) for {len(cluster_ids)} cluster(s)."
                )

                # ── Simulation: auto-fill terms and mark received ──────────────
                received_at = datetime.datetime.now().isoformat()
                terms_summary = []

                for cluster in buyer_clusters:
                    cluster_id = cluster['Consolidation_Cluster_ID']
                    terms = _simulate_comm_terms(cursor, cluster)

                    cursor.execute("""
                        UPDATE Consolidated_PRs
                        SET Commercial_Terms_Status = 'Received',
                            Unit_Price      = ?,
                            HSN_Code        = ?,
                            LCITC_Percent   = ?,
                            PnF_Percent     = ?,
                            Freight_Percent = ?,
                            GST_Percent     = ?,
                            Payment_Terms   = ?,
                            Incoterms       = ?,
                            Ship_To         = ?,
                            PR_Status       = 'Comm_Terms_Received',
                            Comm_Terms_Received_At = ?
                        WHERE Consolidation_Cluster_ID = ?
                    """, (
                        terms['unit_price'],    terms['hsn_code'],
                        terms['lcitc_percent'], terms['pnf_percent'],
                        terms['freight_percent'], terms['gst_percent'],
                        terms['payment_terms'], terms['incoterms'],
                        terms['ship_to'],       received_at,
                        cluster_id
                    ))

                    terms_summary.append({
                        'cluster_id':  cluster_id,
                        'unit_price':  terms['unit_price'],
                        'hsn_code':    terms['hsn_code'],
                        'gst_percent': terms['gst_percent'],
                        'payment_terms': terms['payment_terms'],
                        'incoterms':   terms['incoterms'],
                    })

                    logging.info(
                        f"Simulated comm terms for {cluster_id}: "
                        f"Unit Price={terms['unit_price']}, GST={terms['gst_percent']}%, "
                        f"Incoterms={terms['incoterms']}"
                    )

                # Mark Comm_Request as received
                cursor.execute("""
                    UPDATE Comm_Requests
                    SET Status = 'Received', Received_At = ?
                    WHERE Comm_Request_ID = ?
                """, (received_at, comm_request_id))

                # Process event log
                evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
                cursor.execute("""
                    INSERT INTO Process_Events_Log
                        (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    evt_id,
                    'S2C.PR.03b', 'Comm_Request', comm_request_id,
                    'Comm_Terms_Received',
                    f"Commercial terms received for {len(cluster_ids)} cluster(s) via simulation.",
                    'Agent:PR.03b', received_at
                ))

                # Human feedback: buyer confirms the auto-simulated terms
                request_human_feedback(
                    cursor,
                    stage='COMM_TERMS_REVIEW',
                    entity_type='Comm_Request',
                    entity_id=comm_request_id,
                    context_summary=json.dumps(terms_summary, indent=2),
                    feedback_by=buyer_id,
                    simulate=True
                )

            state['comm_terms_received'] = True
            logging.info("Commercial terms finalised for all pending clusters.")

    except Exception as e:
        logging.error(f"An error occurred in Commercial Terms Finalisation: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting PR.03b.")
    return state
