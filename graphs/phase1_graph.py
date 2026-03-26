# graphs/phase1_graph.py
import sys
import os
import logging

# Add project root to path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.graph import StateGraph, END
from state import S2CState
from agents.pr_01_consolidation import pr_consolidation
from agents.pr_02_spec_extraction import spec_extraction
from agents.pr_03_buyer_assignment import buyer_assignment
from agents.pr_03b_commercial_terms import commercial_terms_finalisation
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_phase1_graph():
    """Builds the LangGraph StateGraph for Phase 1 of the S2C process."""
    graph = StateGraph(S2CState)

    # Add the four agent nodes to the graph
    graph.add_node("pr_consolidation", pr_consolidation)
    graph.add_node("spec_extraction", spec_extraction)
    graph.add_node("buyer_assignment", buyer_assignment)
    graph.add_node("commercial_terms_finalisation", commercial_terms_finalisation)

    # The entry point of the graph is the PR consolidation agent
    graph.set_entry_point("pr_consolidation")

    # Conditional routing after the consolidation step
    def route_after_consolidation(state: S2CState):
        logging.debug(f"Routing after consolidation. Stop flag: {state.get('should_stop')}, Clusters: {len(state.get('consolidated_clusters', []))}")
        if state.get("should_stop"): 
            return END
        # If any clusters were created, proceed to spec extraction
        if state.get("consolidated_clusters"): 
            return "spec_extraction"
        # Otherwise, if no PRs were found to process, end the flow
        return END

    graph.add_conditional_edges("pr_consolidation", route_after_consolidation)

    # Conditional routing after the spec extraction step
    def route_after_specs(state: S2CState):
        logging.debug(f"Routing after spec extraction. Stop flag: {state.get('should_stop')}, Specs extracted: {state.get('specs_extracted')}")
        if state.get("should_stop"):
            return END
        # If specs were successfully extracted for any cluster, move to buyer assignment
        if state.get("specs_extracted"): 
            return "buyer_assignment"
        # If no specs were ready (e.g., all are pending), end the flow for now.
        # A separate trigger might re-evaluate pending specs later.
        return END

    graph.add_conditional_edges("spec_extraction", route_after_specs)
    
    # Buyer assignment feeds into commercial terms finalisation
    graph.add_edge("buyer_assignment", "commercial_terms_finalisation")

    # Commercial terms is the last step in Phase 1
    graph.add_edge("commercial_terms_finalisation", END)

    return graph.compile()

# Main execution block to run the graph
if __name__ == "__main__":
    logging.info("Building Phase 1 graph...")
    app = build_phase1_graph()

    # Define the initial state for the graph
    # This state is passed to the entry point node
    initial_state = S2CState(
        cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
        current_agent="", next_agent=None,
        pr_status=None, 
        consolidated_clusters=[], 
        specs_extracted=False,
        buyer_assigned=None,
        comm_terms_received=False,
        vendors_shortlisted=[],
        rfq_created=False,
        evaluations_complete=False, 
        negotiated_price=None, 
        nfa_approved=False,
        po_created=False, 
        sap_po_number=None, 
        errors=[], 
        compliance_results={},
        should_stop=False,
        db_path=config.DB_PATH, # Get path from config
        dms_root=config.DMS_ROOT # Get path from config
    )

    logging.info("Invoking Phase 1 graph...")
    # The .invoke method runs the graph from the entry point until it reaches an END state
    result = app.invoke(initial_state)

    print("\n--- Graph Execution Complete ---")
    print(f"Final State: {result}")
    if result.get('errors'):
        print(f"\nErrors occurred during execution:")
        for error in result['errors']:
            print(f"- {error}")
    else:
        print("\nExecution finished without critical errors.")
    print("--------------------------------")
