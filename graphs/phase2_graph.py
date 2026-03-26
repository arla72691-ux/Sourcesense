# graphs/phase2_graph.py
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.graph import StateGraph, END
from state import S2CState
from agents.rfq_04_vendor_shortlisting import vendor_shortlisting
from agents.rfq_05_rfq_creation import rfq_creation
from agents.rfq_06_compliance_attach import compliance_attach
from agents.rfq_07_rfq_approval import rfq_approval
from agents.rfq_08_rfq_dispatch import rfq_dispatch
from agents.rfq_09_offer_collection import offer_collection
from agents.eval_08_tech_evaluation import tech_evaluation
from agents.eval_09_comm_evaluation import comm_evaluation
from agents.eval_10_overall_ranking import overall_ranking
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_phase2_graph():
    """Builds the LangGraph StateGraph for Phase 2 (RFQ & Evaluation)."""
    graph = StateGraph(S2CState)

    # Add all Phase 2 nodes
    graph.add_node("vendor_shortlisting", vendor_shortlisting)
    graph.add_node("rfq_creation", rfq_creation)
    graph.add_node("compliance_attach", compliance_attach)
    graph.add_node("rfq_approval", rfq_approval)
    graph.add_node("rfq_dispatch", rfq_dispatch)
    graph.add_node("offer_collection", offer_collection)
    graph.add_node("tech_evaluation", tech_evaluation)
    graph.add_node("comm_evaluation", comm_evaluation)
    graph.add_node("overall_ranking", overall_ranking)

    # Entry point for Phase 2
    graph.set_entry_point("vendor_shortlisting")

    # Wire the graph with sequential and conditional edges
    graph.add_edge("vendor_shortlisting", "rfq_creation")
    graph.add_edge("rfq_creation", "compliance_attach")

    # Conditional edge after compliance check for SVJ
    def route_after_compliance(state: S2CState):
        if state.get("should_stop"): # SVJ is pending
            logging.info("Routing from compliance: SVJ required, ending flow for now.")
            return END
        logging.info("Routing from compliance: Proceeding to approval.")
        return "rfq_approval"
    graph.add_conditional_edges("compliance_attach", route_after_compliance)

    # The approval node transitions to dispatch (approval is simulated internally for now)
    graph.add_edge("rfq_approval", "rfq_dispatch")
    graph.add_edge("rfq_dispatch", "offer_collection")

    # Conditional edge after offer collection
    def route_after_collection(state: S2CState):
        # This logic depends on the offer_collection agent setting a flag or status.
        # For now, we assume if evaluations are not complete, we start them.
        if not state.get("evaluations_complete"): 
            logging.info("Routing from collection: Submissions closed, proceeding to tech evaluation.")
            return "tech_evaluation"
        logging.info("Routing from collection: Still collecting offers, ending flow for now.")
        return END
    graph.add_conditional_edges("offer_collection", route_after_collection)

    # Evaluation pipeline is sequential
    graph.add_edge("tech_evaluation", "comm_evaluation")
    graph.add_edge("comm_evaluation", "overall_ranking")

    # The final node of Phase 2
    graph.add_edge("overall_ranking", END)

    return graph.compile()

if __name__ == "__main__":
    # This allows running Phase 2 independently, assuming Phase 1 has set up the data.
    logging.info("Building Phase 2 graph...")
    app = build_phase2_graph()

    # Initial state should reflect a cluster ready for this phase
    initial_state = S2CState(
        # ... (full state initialization) ...
        current_agent="", errors=[], should_stop=False,
        db_path=config.DB_PATH, dms_root=config.DMS_ROOT, 
        buyer_assigned="BUY-1001", # Example buyer
        evaluations_complete=True # Set to True to allow collection->eval transition logic to pass first time
    )

    logging.info("Invoking Phase 2 graph...")
    # You would typically call this after Phase 1 completes
    # For a standalone run, ensure DB has clusters in 'Buyer_Assigned' state
    result = app.invoke(initial_state)

    print("\n--- Phase 2 Graph Execution Complete ---")
    if result.get('errors'):
        print(f"\nErrors occurred:")
        for error in result['errors']:
            print(f"- {error}")
    else:
        print("\nExecution finished without critical errors.")
    print("--------------------------------")
