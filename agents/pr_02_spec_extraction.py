# agents/pr_02_spec_extraction.py
import logging
import json
import os
import smtplib
import sys
import datetime
from email.mime.text import MIMEText

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google import genai
from state import S2CState
from db import get_db, next_id
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Gemini
try:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
except Exception as e:
    logging.error(f"Failed to configure Gemini AI: {e}")
    raise

def send_email(to_email: str, subject: str, body: str):
    """Sends an email using the configured SMTP settings."""
    if not config.is_email_configured():
        logging.warning(f"Email not configured. Cannot send email to {to_email}.")
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
            logging.info(f"Email sent to {to_email}.")
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")

def spec_extraction(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.02 — Technical Specification Extraction
    """
    logging.info("Entering PR.02 - Spec Extraction agent.")
    state['current_agent'] = "pr_02_spec_extraction"
    errors = state.get('errors', [])
    specs_were_extracted = False

    prompt_template = '''Extract structured technical specifications from this document. Output JSON: {"dimensions": {...}, "standards": [...], "alternatives": [...], "critical_parameters": [...], "inspection_requirements": [...]} '''

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            # Process clusters created in the previous step
            # In a real multi-agent setup, this handoff would be more robust.
            cursor.execute("SELECT * FROM Consolidated_PRs WHERE PR_Status = 'New'")
            clusters_to_process = cursor.fetchall()

            if not clusters_to_process:
                logging.info("No new clusters to process for spec extraction.")
                state['specs_extracted'] = False
                return state

            for cluster in clusters_to_process:
                cluster_id = cluster['Consolidation_Cluster_ID']
                material_code = cluster['Material_Code'] # Assuming one primary material per cluster for now

                cursor.execute("""
                    SELECT m.Spec_Document_File_ID, pr.Requisitioner
                    FROM Material_Master m
                    JOIN Master_PR_Data pr ON m.Material_Code = pr.Material_Code
                    WHERE m.Material_Code = ?
                    LIMIT 1
                """, (material_code,))
                material_info = cursor.fetchone()

                final_status = 'Unknown'

                if material_info and material_info['Spec_Document_File_ID']:
                    spec_file_id = material_info['Spec_Document_File_ID']
                    # Assuming a folder structure DMS_ROOT/Specs/<file_id>
                    file_path = os.path.join(state['dms_root'], 'Specs', spec_file_id)
                    logging.info(f"Found spec doc [{spec_file_id}] for cluster {cluster_id}.")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            doc_content = f.read()

                        response = client.models.generate_content(model="gemini-2.5-pro", contents=prompt_template + "\n\n" + doc_content)
                        cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
                        extracted_specs = json.loads(cleaned_json)

                        cursor.execute("UPDATE Consolidated_PRs SET Long_Text_Specifications = ?, PR_Status = 'Specs_Ready' WHERE Consolidation_Cluster_ID = ?",
                                       (json.dumps(extracted_specs), cluster_id))
                        final_status = 'Specs_Ready'
                        specs_were_extracted = True
                        logging.info(f"Extracted and saved specs for cluster {cluster_id}.")

                    except FileNotFoundError:
                        errors.append(f"Spec file not found at path: {file_path}")
                        logging.error(f"Spec file {spec_file_id} for cluster {cluster_id} not found at {file_path}.")
                    except json.JSONDecodeError:
                        errors.append(f"Failed to decode JSON from Gemini for cluster {cluster_id}.")
                        logging.error(f"Bad JSON from Gemini for {cluster_id}: {response.text}")
                else:
                    # No spec doc, so request it
                    requisitioner_email = material_info['Requisitioner'] if material_info else 'default.requisitioner@example.com'
                    spr_id = next_id(cursor, 'Spec_Requests', 'Spec_Request_ID', 'SPR')
                    cursor.execute("INSERT INTO Spec_Requests (Spec_Request_ID, Consolidation_Cluster_ID, Requested_From, Status, Created_At) VALUES (?, ?, ?, ?, ?)",
                                   (spr_id, cluster_id, requisitioner_email, 'Pending', datetime.datetime.now().isoformat()))
                    cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'Specs_Pending' WHERE Consolidation_Cluster_ID = ?", (cluster_id,))
                    final_status = 'Specs_Pending'

                    logging.info(f"No spec doc for cluster {cluster_id}. Sending request to {requisitioner_email}.")
                    email_subject = f"Action Required: Missing Technical Specification for {cluster_id}"
                    email_body = f"Dear Requisitioner,\n\nPlease provide the technical specification document for material {material_code} related to procurement cluster {cluster_id}.\n\nThank you,\nSourcesense Platform"
                    send_email(requisitioner_email, email_subject, email_body)

                # Log Process Event
                evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
                cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (evt_id, 'S2C.RFQ.02', 'Cluster', cluster_id, 'SpecExtraction', f"Status: {final_status}", 'Agent:PR.02', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Spec Extraction: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'].extend(errors)
    state['specs_extracted'] = specs_were_extracted
    if errors:
        logging.error(f"Errors occurred: {errors}")

    logging.info("Exiting PR.02.")
    return state
