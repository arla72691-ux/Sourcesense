# agents/pr_01_consolidation.py
import logging
import json
import datetime
import sys
import os
import sqlite3
from typing import List, Dict

# Add project root to path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google import genai
from feedback import request_human_feedback
from state import S2CState
from db import get_db
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Gemini AI
try:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
except Exception as e:
    logging.error(f"Failed to configure Gemini AI: {e}")
    raise

def pr_consolidation(state: S2CState) -> S2CState:
    """
    LangGraph node: PR.01 — Purchase Requisition Consolidation
    """
    logging.info("Entering PR.01 - PR Consolidation agent.")
    state['current_agent'] = "pr_01_consolidation"
    errors = state.get('errors', [])
    

    prompt_template = '''
You are a procurement clustering AI for a steel plant.
Given these open Purchase Requisitions:
{pr_list_json}

Group them into procurement clusters following these rules:
1. Same Material_Code = always same cluster (combine quantities).
2. Different Material_Code but same Material_Group AND same Plant AND
   delivery dates within 14 days = suggest clustering (output reasoning).
3. Never cluster materials from different Material_Groups.

Return JSON: [{"cluster_name": "...", "pr_numbers": [...], "reason": "..."}]'''
    
    pr_list_for_gemini = []
    open_prs_map = {}

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            
            sql_query = '''
                SELECT
                    pr.PR_Number, pr.Material_Code, pr.Plant, pr.Quantity, pr.UOM,
                    pr.Delivery_Date, pr.PR_Status,
                    mm.Material_Description, mm.Material_Group, mm.Base_UOM,
                    lm.Last_Purchase_Price
                FROM Master_PR_Data pr
                JOIN Material_Master mm ON pr.Material_Code = mm.Material_Code
                LEFT JOIN LPP_Master lm ON pr.Material_Code = lm.Material_Code AND pr.Plant = lm.Plant
                WHERE pr.PR_Status = 'Open'
            '''
            cursor.execute(sql_query)
            open_prs = cursor.fetchall()

            if not open_prs:
                logging.info("No open PRs to process.")
                state['consolidated_clusters'] = []
                return state

            for pr in open_prs:
                pr_dict = dict(pr)
                base_uom = pr_dict['Base_UOM']
                original_uom = pr_dict['UOM']
                quantity = pr_dict['Quantity']

                if original_uom != base_uom:
                    cursor.execute("SELECT Conversion_Factor FROM UOM_Conversion WHERE From_UOM = ? AND To_UOM_Base = ?", (original_uom, base_uom))
                    conversion = cursor.fetchone()
                    if conversion:
                        pr_dict['Base_Quantity'] = quantity * conversion['Conversion_Factor']
                        pr_dict['Original_Quantity'] = quantity
                    else:
                        errors.append(f"UOM conversion not found for PR {pr_dict['PR_Number']} from {original_uom} to {base_uom}.")
                        continue
                else:
                    pr_dict['Base_Quantity'] = quantity

                pr_list_for_gemini.append({
                    "pr_number": pr_dict['PR_Number'],
                    "material_code": pr_dict['Material_Code'],
                    "material_group": pr_dict['Material_Group'],
                    "plant": pr_dict['Plant'],
                    "delivery_date": pr_dict['Delivery_Date'],
                    "quantity": pr_dict['Base_Quantity'],
                    "uom": base_uom
                })
                open_prs_map[pr_dict['PR_Number']] = pr_dict
        
        if not pr_list_for_gemini:
            logging.warning("No PRs left to process after UOM conversion handling.")
            state['consolidated_clusters'] = []
            state['errors'] = errors
            return state

        gemini_prompt = prompt_template.format(pr_list_json=json.dumps(pr_list_for_gemini, indent=2))
        
        logging.info("Calling Gemini for PR clustering...")
        response = client.models.generate_content(model="gemini-2.5-pro", contents=gemini_prompt)
        
        try:
            cleaned_json_response = response.text.strip().replace('```json', '').replace('```', '')
            ai_clusters = json.loads(cleaned_json_response)
            logging.info(f"Gemini returned {len(ai_clusters)} clusters.")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from Gemini response: {e} - Response: {response.text}")
            errors.append(f"AI response was not valid JSON: {response.text}")
            state['errors'] = errors
            state['should_stop'] = True
            return state

        consolidated_clusters_for_state = []

        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            
            today_str = datetime.date.today().strftime("%Y%m%d")
            cursor.execute("SELECT COUNT(*) FROM Consolidated_PRs WHERE Consolidation_Cluster_ID LIKE ?", (f"CL-{today_str}-%",))
            seq_start = cursor.fetchone()[0]

            for i, cluster in enumerate(ai_clusters, start=seq_start + 1):
                cluster_id = f"CL-{today_str}-{i:05d}"
                pr_numbers_in_cluster = cluster['pr_numbers']
                
                total_value = 0
                total_quantity = 0
                materials_in_cluster = []
                
                for pr_num in pr_numbers_in_cluster:
                    pr_data = open_prs_map[pr_num]
                    total_quantity += pr_data['Base_Quantity']
                    lpp = pr_data['Last_Purchase_Price'] if pr_data['Last_Purchase_Price'] else 0
                    total_value += pr_data['Base_Quantity'] * lpp
                    materials_in_cluster.append(pr_data)

                if not materials_in_cluster:
                    continue
                
                first_pr = materials_in_cluster[0]

                budget_overrun_flag = 1 if total_value > 10000000 else 0
                
                repeat_emergency_flag = 0
                try:
                    thirty_days_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
                    cursor.execute("""
                        SELECT 1 FROM Procurement_Historical_Pricing 
                        WHERE Material_Code = ? AND Purchase_Date >= ?
                        LIMIT 1
                    """, (first_pr['Material_Code'], thirty_days_ago))
                    if cursor.fetchone():
                        repeat_emergency_flag = 1
                except sqlite3.OperationalError:
                    logging.warning("Table 'Procurement_Historical_Pricing' not found. Skipping CTRL-017 check.")
                    errors.append("CTRL-017 Skipped: Procurement_Historical_Pricing table does not exist.")

                cursor.execute("""
                    INSERT INTO Consolidated_PRs (
                        Consolidation_Cluster_ID, PR_Number, Material_Code, Material_Group, Description,
                        Quantity, UOM_Base, Total_Value, Plant, PR_Status, Repeat_Emergency_Flag, Budget_Overrun_Flag, Created_At
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cluster_id, ",".join(pr_numbers_in_cluster), first_pr['Material_Code'], first_pr['Material_Group'],
                    first_pr['Material_Description'], total_quantity, first_pr['Base_UOM'], total_value,
                    first_pr['Plant'], 'New', repeat_emergency_flag, budget_overrun_flag, datetime.datetime.now().isoformat()
                ))

                cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?, ?, ?, ?, ?, ?)",
                               ('CTRL-006', 'Cluster', cluster_id, 'Pass' if not budget_overrun_flag else 'Fail', f'Total Value: {total_value}', datetime.datetime.now().isoformat()))
                cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?, ?, ?, ?, ?, ?)",
                               ('CTRL-017', 'Cluster', cluster_id, 'Pass' if not repeat_emergency_flag else 'Fail', f'Material: {first_pr["Material_Code"]}', datetime.datetime.now().isoformat()))

                cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               ('S2C.PR.01', 'Cluster', cluster_id, 'Creation', f'Cluster created from PRs: {",".join(pr_numbers_in_cluster)}', 'Agent:PR.01', datetime.datetime.now().isoformat()))
                
                for pr_num in pr_numbers_in_cluster:
                    cursor.execute("UPDATE Master_PR_Data SET PR_Status = 'Consolidated' WHERE PR_Number = ?", (pr_num,))

                consolidated_clusters_for_state.append({
                    "cluster_id": cluster_id,
                    "pr_numbers": pr_numbers_in_cluster,
                    "total_value": total_value
                })

        state['consolidated_clusters'] = consolidated_clusters_for_state
        logging.info(f"Successfully created {len(consolidated_clusters_for_state)} new clusters.")

        # Human feedback: buyer reviews AI-generated clusters before pipeline proceeds
        if consolidated_clusters_for_state:
            with get_db(state['db_path']) as fb_conn:
                fb_cursor = fb_conn.cursor()
                summary = json.dumps([
                    {"cluster_id": cl["cluster_id"],
                     "pr_numbers": cl["pr_numbers"],
                     "total_value": cl["total_value"]}
                    for cl in consolidated_clusters_for_state
                ], indent=2)
                request_human_feedback(
                    fb_cursor,
                    stage='PR_CLUSTER_REVIEW',
                    entity_type='Cluster_Batch',
                    entity_id=f"BATCH-{consolidated_clusters_for_state[0]['cluster_id']}",
                    context_summary=f"{len(consolidated_clusters_for_state)} clusters created:\n{summary}",
                    feedback_by=None,
                    simulate=True
                )

    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from Gemini response: {e} - Response: {response.text}")
        errors.append(f"AI response was not valid JSON: {response.text}")
    except Exception as e:
        logging.error(f"An error occurred in PR Consolidation: {e}", exc_info=True)
        errors.append(str(e))

    if errors:
        state['errors'] = errors
        state['should_stop'] = True
        logging.error(f"Errors occurred: {errors}")

    logging.info("Exiting PR.01.")
    return state
