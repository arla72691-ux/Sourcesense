# core/feedback.py
"""
Human feedback utility for the Sourcesense S2C platform.

Agents call request_human_feedback() at key decision points. In simulation mode
the record is immediately auto-approved. In production the agent would pause and
wait for an external webhook/UI response to update the Human_Feedback row.

Process stages used across agents:
    PR_CLUSTER_REVIEW           — pr_01: AI-generated PR clusters
    VENDOR_SHORTLIST_REVIEW     — rfq_04: vendor shortlist before RFQ dispatch
    EVAL_RANKING_REVIEW         — eval_10: final vendor ranking before negotiation
    NEGOTIATION_STRATEGY_REVIEW — neg_11: AI negotiation brief before contacting vendor
    PO_CONFIRMATION             — po_16: PO details before SAP BAPI call
"""

import logging
import datetime

logger = logging.getLogger(__name__)


def request_human_feedback(cursor, stage, entity_type, entity_id,
                            context_summary, feedback_by=None, simulate=True):
    """
    Insert a Human_Feedback record and optionally auto-approve it (simulation mode).

    Args:
        cursor:           Active DB cursor (within an open get_db context).
        stage:            Process stage constant, e.g. 'PR_CLUSTER_REVIEW'.
        entity_type:      e.g. 'Cluster', 'RFQ', 'PO'.
        entity_id:        ID of the entity being reviewed.
        context_summary:  Human-readable or JSON summary of what the agent produced.
        feedback_by:      Buyer_ID or Employee_ID of the expected reviewer (nullable).
        simulate:         If True, auto-approve immediately (test/dev mode).

    Returns:
        'Approved' in simulate mode, None when waiting for human input.
    """
    cursor.execute("SELECT COUNT(*) FROM Human_Feedback")
    count = cursor.fetchone()[0]
    feedback_id = f"HF-{count + 1:05d}"
    now = datetime.datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO Human_Feedback
            (Feedback_ID, Process_Stage, Entity_Type, Entity_ID,
             Context_Summary, Feedback_By, Requested_At)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (feedback_id, stage, entity_type, entity_id,
          context_summary, feedback_by, now))

    if simulate:
        cursor.execute("""
            UPDATE Human_Feedback
            SET Response = 'Approved',
                Comments = 'Auto-approved (simulation mode)',
                Resolved_At = ?
            WHERE Feedback_ID = ?
        """, (now, feedback_id))
        logger.info(
            f"[SIMULATION] Feedback {feedback_id} auto-approved "
            f"| stage={stage} | {entity_type} {entity_id}"
        )
        return 'Approved'

    logger.info(
        f"Feedback {feedback_id} pending human review "
        f"| stage={stage} | {entity_type} {entity_id}"
    )
    return None
