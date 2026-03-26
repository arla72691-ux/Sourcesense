# agents/eval_10_overall_ranking.py
import logging
import json
import sys
import os
import datetime
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import S2CState
from db import get_db
from feedback import request_human_feedback
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_weights(criteria_string: str) -> dict:
    """Parses a string like 'Tech: 40%, Comm: 60%, Min score: 70' into a dict."""
    weights = {'tech': 0.0, 'comm': 0.0, 'min_score': 0.0}
    try:
        tech_match = re.search(r'Tech:\s*(\d+)%', criteria_string, re.I)
        if tech_match: weights['tech'] = float(tech_match.group(1)) / 100
        
        comm_match = re.search(r'Comm:\s*(\d+)%', criteria_string, re.I)
        if comm_match: weights['comm'] = float(comm_match.group(1)) / 100
        
        min_match = re.search(r'Min score:\s*(\d+)', criteria_string, re.I)
        if min_match: weights['min_score'] = float(min_match.group(1))
    except Exception as e:
        logging.error(f"Could not parse weights from string '{criteria_string}': {e}")
    return weights

def overall_ranking(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.12 — Overall Ranking
    """
    logging.info("Entering EVAL.10 - Overall Ranking agent.")
    state['current_agent'] = "overall_ranking"
    errors = state.get('errors', [])
    state['evaluations_complete'] = False

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            # Find RFQs where commercial evaluation is done.
            cursor.execute("""
                SELECT DISTINCT r.RFQ_ID, r.Evaluation_Criteria
                FROM RFQ_Comm_Evaluations ce
                JOIN RFQ_Submissions s ON ce.Submission_ID = s.Submission_ID
                JOIN RFQ_Log r ON s.RFQ_ID = r.RFQ_ID
                WHERE s.Submission_ID NOT IN (SELECT Submission_ID FROM RFQ_Overall_Evaluations)
            """)
            rfqs_to_rank = cursor.fetchall()

            if not rfqs_to_rank:
                logging.info("No RFQs ready for overall ranking.")
                return state

            for rfq in rfqs_to_rank:
                rfq_id = rfq['RFQ_ID']
                logging.info(f"Calculating overall ranking for RFQ {rfq_id}.")

                # Step 1: Parse weights
                weights = parse_weights(rfq['Evaluation_Criteria'])
                if not all(weights.values()):
                    errors.append(f"Invalid weights for RFQ {rfq_id}: {rfq['Evaluation_Criteria']}")
                    continue

                # Step 2: Get all submissions and their scores
                cursor.execute("""
                    SELECT s.Submission_ID, s.Vendor_Code, te.Tech_Score, ce.Price_Score, ce.Payment_Score, ce.Delivery_Score
                    FROM RFQ_Submissions s
                    JOIN RFQ_Tech_Evaluations te ON s.Submission_ID = te.Submission_ID
                    JOIN RFQ_Comm_Evaluations ce ON s.Submission_ID = ce.Submission_ID
                    WHERE s.RFQ_ID = ?
                """, (rfq_id,))
                submissions = cursor.fetchall()

                ranked_list = []
                for sub in submissions:
                    comm_avg = (sub['Price_Score'] + sub['Payment_Score'] + sub['Delivery_Score']) / 3
                    tech_weighted = sub['Tech_Score'] * weights['tech']
                    comm_weighted = comm_avg * weights['comm']
                    overall_score = tech_weighted + comm_weighted

                    # Step 3: Insert overall evaluation
                    cursor.execute("INSERT INTO RFQ_Overall_Evaluations (Submission_ID, Tech_Weighted_Score, Comm_Weighted_Score, Overall_Score) VALUES (?, ?, ?, ?)",
                                   (sub['Submission_ID'], tech_weighted, comm_weighted, overall_score))
                    
                    ranked_list.append({
                        'vendor': sub['Vendor_Code'], 
                        'score': round(overall_score, 2)
                    })
                
                # Step 4: Rank list
                ranked_list.sort(key=lambda x: x['score'], reverse=True)

                # Step 5 & 6: Log top vendor and check thresholds
                if ranked_list:
                    top_vendor = ranked_list[0]
                    logging.info(f"Evaluation complete for {rfq_id}: {top_vendor['vendor']} ranked 1st with score {top_vendor['score']}")
                    cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                                   ('S2C.RFQ.12', 'RFQ', rfq_id, 'EvaluationComplete', f"Evaluation complete: {top_vendor['vendor']} ranked 1st with score {top_vendor['score']}", 'Agent:EVAL.10', datetime.datetime.now().isoformat()))

                # Step 7: CTRL-011 final check
                cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?,?,?,?,?,?)",
                               ('CTRL-011', 'RFQ', rfq_id, 'Pass', 'All submissions have been ranked.', datetime.datetime.now().isoformat()))

                # Human feedback: buyer reviews ranking before negotiation starts
                cursor.execute("""
                    SELECT c.Assigned_Buyer FROM Consolidated_PRs c
                    JOIN RFQ_Log r ON c.Consolidation_Cluster_ID = r.Consolidation_Cluster_ID
                    WHERE r.RFQ_ID = ?
                """, (rfq_id,))
                buyer_row = cursor.fetchone()
                buyer_id = buyer_row['Assigned_Buyer'] if buyer_row else None
                request_human_feedback(
                    cursor,
                    stage='EVAL_RANKING_REVIEW',
                    entity_type='RFQ',
                    entity_id=rfq_id,
                    context_summary=json.dumps(ranked_list, indent=2),
                    feedback_by=buyer_id,
                    simulate=True
                )

                # Step 8: Update final statuses
                cursor.execute("UPDATE RFQ_Log SET RFQ_Status = 'Evaluation_Complete' WHERE RFQ_ID = ?", (rfq_id,))
                state['evaluations_complete'] = True

    except Exception as e:
        logging.error(f"An error occurred in Overall Ranking: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting EVAL.10.")
    return state
