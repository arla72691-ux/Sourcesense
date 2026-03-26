# graphs/master_graph.py
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.graph import StateGraph, END
from state import S2CState
import config

# Import all phase graph builders
# Note: These imports will fail if the files don't exist yet.
from graphs.phase1_graph import build_phase1_graph
from graphs.phase2_graph import build_phase2_graph
from graphs.phase3_graph import build_phase3_graph
from graphs.phase4_graph import build_phase4_graph

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_master_graph():
    """
    Master graph wiring all 19 agents by composing phase-specific subgraphs.
    """
    # Each phase is a compiled subgraph, which can be treated as a single node.
    phase1 = build_phase1_graph()
    phase2 = build_phase2_graph()
    phase3 = build_phase3_graph()
    phase4 = build_phase4_graph()

    master_graph = StateGraph(S2CState)

    # Add each phase as a node in the master graph
    master_graph.add_node("phase1_pr", phase1.invoke)
    master_graph.add_node("phase2_rfq", phase2.invoke)
    master_graph.add_node("phase3_neg", phase3.invoke)
    master_graph.add_node("phase4_po", phase4.invoke)

    master_graph.set_entry_point("phase1_pr")

    # Define the routing logic between phases
    def route_after_phase1(state):
        if state.get("should_stop"): return END
        # buyer_assigned is the key state change that signals Phase 1 is done
        if state.get("buyer_assigned"): 
            logging.info("MASTER ROUTER: Phase 1 complete, proceeding to Phase 2 (RFQ).")
            return "phase2_rfq"
        return END

    def route_after_phase2(state):
        if state.get("should_stop"): return END
        # evaluations_complete signals Phase 2 is done
        if state.get("evaluations_complete"): 
            logging.info("MASTER ROUTER: Phase 2 complete, proceeding to Phase 3 (Negotiation).")
            return "phase3_neg"
        return END

    def route_after_phase3(state):
        if state.get("should_stop"): return END
        # nfa_approved signals Phase 3 is done
        if state.get("nfa_approved"): 
            logging.info("MASTER ROUTER: Phase 3 complete, proceeding to Phase 4 (PO Creation).")
            return "phase4_po"
        return END

    master_graph.add_conditional_edges("phase1_pr", route_after_phase1)
    master_graph.add_conditional_edges("phase2_rfq", route_after_phase2)
    master_graph.add_conditional_edges("phase3_neg", route_after_phase3)
    master_graph.add_edge("phase4_po", END)

    return master_graph.compile()

if __name__ == "__main__":
    app = build_master_graph()
    
    # Optionally, print the graph structure in Mermaid format
    # print(app.get_graph().draw_mermaid())

    initial_state = S2CState(
        cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
        current_agent="phase1_pr", next_agent=None, pr_status=None,
        consolidated_clusters=[], specs_extracted=False, buyer_assigned=None,
        vendors_shortlisted=[], rfq_created=False, evaluations_complete=False,
        negotiated_price=None, nfa_approved=False, po_created=False,
        sap_po_number=None, errors=[], compliance_results={}, should_stop=False,
        db_path=config.DB_PATH, dms_root=config.DMS_ROOT
    )

    logging.info("Invoking the full S2C master graph...")
    result = app.invoke(initial_state)
    
    print("\n--- Full Pipeline Execution Complete ---")
    if result.get("errors"):
        print(f"Errors encountered: {result[\"errors\"]}")
    else:
        print("Execution finished without critical errors.")
    print("---------------------------------------")
