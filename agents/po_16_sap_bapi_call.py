# agents/po_16_sap_bapi_call.py
import logging
import sys
import os
import datetime
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PAYMENT_TERMS_MAP = {
    "Net 30 days from GRN": "Z030",
    "Net 45 days from GRN": "Z045",
    "Net 60 days from GRN": "Z060",
    "100% Advance": "Z000",
    "50% Advance + 50% on Delivery": "Z050",
}

def sap_bapi_call(state: S2CState) -> S2CState:
    """
    LangGraph node: PO.16 — SAP BAPI Call Simulation
    """
    logging.info("Entering PO.16 - SAP BAPI Call agent.")
    state['current_agent'] = "sap_bapi_call"
    errors = state.get('errors', [])
    state['po_created'] = False

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM PO_Reference WHERE API_Call_Status = 'Pending'")
            pending_calls = cursor.fetchall()

            if not pending_calls:
                logging.info("No pending POs to create in SAP.")
                return state

            for call in pending_calls:
                po_ref_id = call['PO_Ref_ID']
                nfa_id = call['NFA_ID']
                
                # Step 2: Gather all data for PO creation
                cursor.execute("SELECT Recommended_Vendor, Negotiated_Unit_Price FROM NFA_Log WHERE NFA_ID = ?", (nfa_id,))
                nfa_data = cursor.fetchone()
                cursor.execute("SELECT Material_Code, Quantity, UOM_Base, Plant, Delivery_Date, Payment_Terms, Total_Value FROM Consolidated_PRs WHERE Consolidation_Cluster_ID = ?", (call['Consolidation_Cluster_ID'],))
                cluster_data = cursor.fetchone()

                # Step 3: Generate SAP_PO_Number
                cursor.execute("SELECT MAX(SAP_PO_Number) FROM SAP_PO_Data")
                max_po = cursor.fetchone()[0]
                sap_po_number = str(int(max_po) + 1) if max_po else '4500087234'

                # Step 4 & 5: Map terms and calculate value
                sap_payment_terms = PAYMENT_TERMS_MAP.get(cluster_data['Payment_Terms'], 'Z030')
                po_net_value = nfa_data['Negotiated_Unit_Price'] * cluster_data['Quantity']

                # Step 6: BAPI Call Simulation with Retry Logic
                success = False
                for attempt in range(3):
                    try:
                        logging.info(f"Attempt {attempt + 1}/3 to create SAP PO for {po_ref_id}.")
                        cursor.execute("""
                            INSERT INTO SAP_PO_Data (SAP_PO_Number, Vendor_Code, Material_Code, Plant, Unit_Price, Quantity, UOM, PO_Net_Value, Delivery_Date, Payment_Terms, Incoterms, PO_Type, PO_Status, Payment_Status, SAP_Created_At)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DDP', 'NB', 'Open', 'Not_Initiated', ?)
                        """, (sap_po_number, nfa_data['Recommended_Vendor'], cluster_data['Material_Code'], cluster_data['Plant'], nfa_data['Negotiated_Unit_Price'], cluster_data['Quantity'], cluster_data['UOM_Base'], po_net_value, cluster_data['Delivery_Date'], sap_payment_terms, datetime.datetime.now().isoformat()))
                        success = True
                        break # Exit retry loop on success
                    except Exception as db_error:
                        logging.error(f"Attempt {attempt + 1} failed for {po_ref_id}: {db_error}")
                        time.sleep(1) # Wait 1 second before retrying

                # Step 7 & 8: Handle success or failure
                if success:
                    logging.info(f"Successfully created SAP PO {sap_po_number} for {po_ref_id}.")
                    cursor.execute("UPDATE PO_Reference SET SAP_PO_Number = ?, API_Call_Status = 'Success' WHERE PO_Ref_ID = ?", (sap_po_number, po_ref_id))
                    state["sap_po_number"] = sap_po_number
                    state["po_created"] = True
                    cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                                   ('S2C.PO.19', 'SAP_PO', sap_po_number, 'PO_Created', f"SAP PO created for NFA {nfa_id}", 'Agent:PO.16', datetime.datetime.now().isoformat()))
                else:
                    logging.critical(f"Permanently failed to create SAP PO for {po_ref_id} after 3 attempts.")
                    cursor.execute("UPDATE PO_Reference SET API_Call_Status = 'Failed_Permanent' WHERE PO_Ref_ID = ?", (po_ref_id,))
                    errors.append(f"Permanent failure creating SAP PO for {po_ref_id}.")
                    state["should_stop"] = True
                    # send_alert_email(...) would be here

    except Exception as e:
        logging.error(f"An error occurred in SAP BAPI Call: {e}", exc_info=True)
        errors.append(str(e))
        state["should_stop"] = True

    state['errors'] = errors
    logging.info("Exiting PO.16.")
    return state
