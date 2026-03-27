# agents/po_18_vendor_dispatch.py
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

def simulate_vendor_acknowledgment(db_path, po_ref_id):
    logging.warning(f"SIMULATION: Auto-acknowledging PO for {po_ref_id}.")
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE PO_Reference SET Vendor_Acknowledged_At = ? WHERE PO_Ref_ID = ?",
                       (datetime.datetime.now().isoformat(), po_ref_id))
        evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
        cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                       (evt_id, 'S2C.PO.19', 'PO', po_ref_id, 'Vendor_Acknowledged', 'System_Sim', datetime.datetime.now().isoformat()))
    return True

def vendor_dispatch(state: S2CState) -> S2CState:
    """
    LangGraph node: PO.18 — Vendor Dispatch & Acknowledgment
    """
    logging.info("Entering PO.18 - Vendor Dispatch agent.")
    state['current_agent'] = "vendor_dispatch"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM PO_Reference WHERE PO_Document_File_ID IS NOT NULL AND Vendor_Acknowledged_At IS NULL")
            pos_to_dispatch = cursor.fetchall()

            if not pos_to_dispatch:
                logging.info("No POs to dispatch to vendors.")
                return state

            for po_ref in pos_to_dispatch:
                po_ref_id = po_ref['PO_Ref_ID']
                sap_po_number = po_ref['SAP_PO_Number']

                # Step 2: Get data for email
                cursor.execute("SELECT v.Vendor_Name, v.Vendor_Code, s.PO_Net_Value, s.Delivery_Date, m.Material_Description FROM SAP_PO_Data s JOIN Vendor_Master v ON s.Vendor_Code = v.Vendor_Code JOIN Material_Master m ON s.Material_Code = m.Material_Code WHERE s.SAP_PO_Number = ?", (sap_po_number,))
                email_data = cursor.fetchone()

                # Step 3: Read PO doc (simulated)
                po_doc_path = os.path.join(config.DMS_ROOT, 'PO', f"PO_{sap_po_number}.txt")
                # with open(po_doc_path, 'r') as f: po_content = f.read()

                # Step 4: Send email (simulated)
                vendor_email = f"{email_data['Vendor_Code'].lower()}@vendor.com"
                logging.info(f"Dispatching PO {sap_po_number} to vendor {email_data['Vendor_Name']} at {vendor_email}.")
                # send_email(...) call would be here

                # Step 7: Simulate immediate acknowledgment for workflow progression
                simulate_vendor_acknowledgment(state['db_path'], po_ref_id)

    except Exception as e:
        logging.error(f"An error occurred in Vendor Dispatch: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting PO.18.")
    return state
