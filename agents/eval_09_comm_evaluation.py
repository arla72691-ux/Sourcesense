# agents/eval_09_comm_evaluation.py
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

def comm_evaluation(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.11 — Commercial Evaluation
    """
    logging.info("Entering EVAL.09 - Commercial Evaluation agent.")
    state['current_agent'] = "comm_evaluation"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            # Find RFQs where tech evaluation is done. A simple way is to find RFQs
            # with submissions that have tech evaluations but no commercial ones yet.
            cursor.execute("""
                SELECT DISTINCT r.RFQ_ID, c.Material_Code
                FROM RFQ_Tech_Evaluations te
                JOIN RFQ_Submissions s ON te.Submission_ID = s.Submission_ID
                JOIN RFQ_Log r ON s.RFQ_ID = r.RFQ_ID
                JOIN Consolidated_PRs c ON r.Consolidation_Cluster_ID = c.Consolidation_Cluster_ID
                WHERE s.Submission_ID NOT IN (SELECT Submission_ID FROM RFQ_Comm_Evaluations)
            """)
            rfqs_to_eval = cursor.fetchall()

            if not rfqs_to_eval:
                logging.info("No RFQs ready for commercial evaluation.")
                return state

            for rfq in rfqs_to_eval:
                rfq_id = rfq['RFQ_ID']
                material_code = rfq['Material_Code']
                logging.info(f"Starting commercial evaluation for RFQ {rfq_id}.")

                # Step 1: Get all submissions for this RFQ
                cursor.execute("SELECT * FROM RFQ_Submissions WHERE RFQ_ID = ?", (rfq_id,))
                submissions = cursor.fetchall()
                if not submissions:
                    continue

                # Step 2 & 3: Get benchmarks
                cursor.execute("SELECT Standard_Lead_Time_Days FROM Material_Master WHERE Material_Code = ?", (material_code,))
                lead_time_benchmark = cursor.fetchone()['Standard_Lead_Time_Days']

                # PRICE SCORE - find the lowest price first
                best_price = min(sub['Quoted_Unit_Price'] for sub in submissions if sub['Quoted_Unit_Price'] > 0)

                for sub in submissions:
                    sub_id = sub['Submission_ID']

                    # PRICE SCORE
                    price_score = (best_price / sub['Quoted_Unit_Price']) * 100 if sub['Quoted_Unit_Price'] > 0 else 0
                    price_score = min(price_score, 100) # Cap at 100

                    # PAYMENT SCORE (based on a simulated field or default)
                    # This logic is simplified; a real system would parse vendor terms.
                    payment_score = 85 # Defaulting to Net 45

                    # DELIVERY SCORE
                    delivery_score = 50 # Default score
                    if sub['Lead_Time_Days'] <= lead_time_benchmark:
                        delivery_score = 100
                    elif sub['Lead_Time_Days'] <= lead_time_benchmark * 1.25:
                        delivery_score = 85
                    elif sub['Lead_Time_Days'] <= lead_time_benchmark * 1.5:
                        delivery_score = 70

                    # Step 5: Insert scores
                    remarks = f"Price Score: {price_score:.2f}, Delivery Score: {delivery_score:.2f}"
                    ce_id = next_id(cursor, 'RFQ_Comm_Evaluations', 'Comm_Eval_ID', 'CE')
                    cursor.execute("INSERT INTO RFQ_Comm_Evaluations (Comm_Eval_ID, Submission_ID, Price_Score, Payment_Score, Delivery_Score, Comm_Remarks) VALUES (?, ?, ?, ?, ?, ?)",
                                   (ce_id, sub_id, price_score, payment_score, delivery_score, remarks))

                # Step 6: Log process event
                logging.info(f"Commercial evaluation completed for RFQ {rfq_id}.")
                evt_id = next_id(cursor, 'Process_Events_Log', 'Event_ID', 'EVT')
                cursor.execute("INSERT INTO Process_Events_Log (Event_ID, Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?,?)",
                               (evt_id, 'S2C.RFQ.11', 'RFQ', rfq_id, 'CommEvaluation', 'Commercial evaluation of all submissions complete.', 'Agent:EVAL.09', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Commercial Evaluation: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting EVAL.09.")
    return state
