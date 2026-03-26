# graphs/phase3_graph.py
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.graph import StateGraph, END
from state import S2CState
from agents.neg_11_negotiation_copilot import negotiation_copilot
from agents.neg_12_negotiation_approval import negotiation_approval
from agents.nfa_13_nfa_generation import nfa_generation
from agents.nfa_14_nfa_approval import nfa_approval
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_phase3_graph():
    """Builds the LangGraph StateGraph for Phase 3 (Negotiation & NFA)."""
    graph = StateGraph(S2CState)

    # Add all Phase 3 nodes
    graph.add_node("negotiation_copilot", negotiation_copilot)
    graph.add_node("negotiation_approval", negotiation_approval)
    graph.add_node("nfa_generation", nfa_generation)
    graph.add_node("nfa_approval", nfa_approval)

    # Entry point for Phase 3
    graph.set_entry_point("negotiation_copilot")

    # Routing after negotiation_copilot
    def route_after_negotiation_start(state: S2CState):
        # If a low-value deal was auto-approved, it sets negotiated_price and moves PR status
        if state.get("negotiated_price"):
            logging.info("Routing from co-pilot: Low-value auto-approval detected, proceeding to NFA generation.")
            return "nfa_generation"
        # Otherwise, the process must wait for an external BAFO
        logging.info("Routing from co-pilot: Waiting for vendor BAFO. Ending flow.")
        return END

    graph.add_conditional_edges("negotiation_copilot", route_after_negotiation_start)

    # After a BAFO is (simulated) approved, generate the NFA
    def route_after_negotiation_approval(state: S2CState):
        if state.get("negotiated_price"):
            logging.info("Routing from neg approval: BAFO approved, proceeding to NFA generation.")
            return "nfa_generation"
        logging.info("Routing from neg approval: BAFO not approved/pending. Ending flow.")
        return END

    graph.add_conditional_edges("negotiation_approval", route_after_negotiation_approval)

    # NFA generation is followed by NFA approval
    graph.add_edge("nfa_generation", "nfa_approval")

    # After NFA approval, the phase is complete
    def route_after_nfa_approval(state: S2CState):
        if state.get("nfa_approved"):
            logging.info("Routing from NFA approval: NFA is fully approved. Ending Phase 3.")
        else:
            logging.info("Routing from NFA approval: NFA is pending approval. Ending flow.")
        return END
    
    graph.add_conditional_edges("nfa_approval", route_after_nfa_approval)

    return graph.compile()

if __name__ == "__main__":
    logging.info("Building Phase 3 graph...")
    app = build_phase3_graph()

    # This state assumes Phase 2 has completed, and an RFQ is in 'Evaluation_Complete' status
    initial_state = S2CState(
        current_agent="", errors=[], should_stop=False,
        db_path=config.DB_PATH, dms_root=config.DMS_ROOT, 
        rfq_id=None, negotiated_price=None, nfa_id=None, nfa_approved=False
    )

    logging.info("Invoking Phase 3 graph...")
    result = app.invoke(initial_state)

    print("\n--- Phase 3 Graph Execution Complete ---")
    if result.get('errors'):
        print(f"\nErrors occurred:")
        for error in result['errors']:
            print(f"- {error}")
    else:
        print("\nExecution finished without critical errors.")
    print("--------------------------------")
