# state.py
from typing import TypedDict, Optional, List, Dict, Any

class S2CState(TypedDict):
    # Current processing context
    cluster_id: Optional[str]           # Consolidation_Cluster_ID being processed
    rfq_id: Optional[str]               # RFQ_ID being processed
    nfa_id: Optional[str]               # NFA_ID being processed
    po_ref_id: Optional[str]            # PO_Reference ID being processed

    # Pipeline routing
    current_agent: str                   # Which agent is running
    next_agent: Optional[str]           # Which agent to run next (routing)
    pr_status: Optional[str]            # Current PR_Status from DB

    # Results from each agent (passed forward)
    consolidated_clusters: List[Dict]   # Output of PR.01
    specs_extracted: bool               # Output of PR.02
    buyer_assigned: Optional[str]       # Output of PR.03
    vendors_shortlisted: List[str]      # Output of RFQ.04
    rfq_created: bool                   # Output of RFQ.05
    evaluations_complete: bool          # Output of EVAL.08-10
    negotiated_price: Optional[float]   # Output of NEG.11-12
    nfa_approved: bool                  # Output of NFA.14
    po_created: bool                    # Output of PO.16
    sap_po_number: Optional[str]        # Output of PO.16

    # Control flags
    errors: List[str]                   # Accumulated errors
    compliance_results: Dict[str, str]  # Control ID → Pass/Fail
    should_stop: bool                   # Hard stop on critical failure

    # Config
    db_path: str                        # Path to s2c_sourcesense.db
    dms_root: str                       # Path to DMS_Documents folder
