# agents/eval_08_tech_evaluation.py
import logging
import json
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import google.generativeai as genai
from state import S2CState
from db import get_db
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=config.GEMINI_API_KEY)

def tech_evaluation(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.10 — Technical Evaluation
    """
    logging.info("Entering EVAL.08 - Technical Evaluation agent.")
    state['current_agent'] = "tech_evaluation"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.RFQ_ID, c.Long_Text_Specifications, c.Material_Code, c.Description
                FROM RFQ_Log r
                JOIN Consolidated_PRs c ON r.Consolidation_Cluster_ID = c.Consolidation_Cluster_ID
                WHERE r.RFQ_Status = 'Submissions_Closed'
            """)
            rfqs_to_eval = cursor.fetchall()

            if not rfqs_to_eval:
                logging.info("No RFQs with closed submissions to evaluate.")
                return state

            model = genai.GenerativeModel("gemini-2.5-pro")

            for rfq in rfqs_to_eval:
                rfq_id = rfq['RFQ_ID']
                logging.info(f"Starting technical evaluation for RFQ {rfq_id}.")
                specs = rfq['Long_Text_Specifications']

                cursor.execute("SELECT * FROM RFQ_Submissions WHERE RFQ_ID = ?", (rfq_id,))
                submissions = cursor.fetchall()
                
                if not submissions:
                    logging.warning(f"No submissions found for RFQ {rfq_id} to evaluate.")
                    continue

                all_evaluated = True
                for sub in submissions:
                    submission_id = sub['Submission_ID']
                    # In a real system, we'd pull file content from DMS based on Submission_File_ID
                    submission_content = "(No submission document attached)"

                    prompt = f"""You are a technical evaluator for procurement at a steel plant.
                    Required specifications: {specs}
                    Vendor {sub['Vendor_Code']} submitted this quote for {rfq['Description']}:
                    Price: {sub['Quoted_Unit_Price']}/unit, Lead Time: {sub['Lead_Time_Days']} days
                    Submission Content: {submission_content}

                    Score the technical compliance on a scale of 0-100:
                    - Spec compliance (40 pts): Does it meet dimensions, grade, standards?
                    - Material quality (30 pts): Brand, certifications, test reports
                    - Documentation (20 pts): Completeness of submission
                    - Alternatives offered (10 pts): Acceptable cross-references provided

                    Return JSON: {{"tech_score": ..., "breakdown": {{...}}, "tech_remarks": "...", "disqualify": false, "disqualify_reason": null}}"""

                    try:
                        response = model.generate_content(prompt)
                        cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
                        eval_result = json.loads(cleaned_json)
                        
                        cursor.execute("INSERT INTO RFQ_Tech_Evaluations (Submission_ID, Tech_Score, Tech_Remarks) VALUES (?, ?, ?)",
                                       (submission_id, eval_result['tech_score'], eval_result['tech_remarks']))

                        if eval_result.get('disqualify', False):
                            reason = eval_result.get('disqualify_reason', 'AI evaluation')
                            logging.warning(f"Submission {submission_id} disqualified by AI. Reason: {reason}")
                            cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?)",
                                           ('Tech-Eval', 'Submission', submission_id, 'Fail', f'Disqualified during tech eval: {reason}', datetime.datetime.now().isoformat()))

                    except (json.JSONDecodeError, Exception) as e:
                        all_evaluated = False
                        errors.append(f"Failed to evaluate submission {submission_id}: {e}")
                        logging.error(f"Could not process AI evaluation for submission {submission_id}: {e}")

                # Step 7: CTRL-011
                if all_evaluated:
                    cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?)",
                                   ('CTRL-011', 'RFQ', rfq_id, 'Pass', 'All submissions technically evaluated.', datetime.datetime.now().isoformat()))
                    # This agent is done, but the overall eval process for the RFQ is not.
                    # We don't update the main status here.
                else:
                    cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?)",
                                   ('CTRL-011', 'RFQ', rfq_id, 'Fail', 'One or more submissions failed technical evaluation.', datetime.datetime.now().isoformat()))
                
                # Step 8: Log Process Event
                cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                               ('S2C.RFQ.10', 'RFQ', rfq_id, 'TechEvaluation', 'Technical evaluation completed for all submissions.', 'Agent:EVAL.08', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Technical Evaluation: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting EVAL.08.")
    return state
