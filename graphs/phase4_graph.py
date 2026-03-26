# graphs/phase4_graph.py
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.graph import StateGraph, END
from state import S2CState
from agents.po_15_po_reference_creation import po_reference_creation
from agents.po_16_sap_bapi_call import sap_bapi_call
from agents.po_17_po_document_attach import po_document_attach
from agents.po_18_vendor_dispatch import vendor_dispatch
from agents.po_19_status_update import status_update

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_phase4_graph():
    """Builds the LangGraph StateGraph for Phase 4 (PO Creation)."""
    graph = StateGraph(S2CState)

    graph.add_node("po_reference_creation", po_reference_creation)
    graph.add_node("sap_bapi_call", sap_bapi_call)
    graph.add_node("po_document_attach", po_document_attach)
    graph.add_node("vendor_dispatch", vendor_dispatch)
    graph.add_node("status_update", status_update)

    graph.set_entry_point("po_reference_creation")

    # Define a generic routing function that stops on error or proceeds
    def route_or_stop(state: S2CState, next_node: str):
        if state.get("should_stop"): 
            logging.error(f"Stopping graph execution due to errors: {state.get('errors')}")
            return END
        return next_node

    graph.add_conditional_edges("po_reference_creation", lambda s: route_or_stop(s, "sap_bapi_call"))
    graph.add_conditional_edges("sap_bapi_call", lambda s: route_or_stop(s, "po_document_attach"))
    graph.add_conditional_edges("po_document_attach", lambda s: route_or_stop(s, "vendor_dispatch"))
    graph.add_conditional_edges("vendor_dispatch", lambda s: route_or_stop(s, "status_update"))
    graph.add_edge("status_update", END)

    return graph.compile()

if __name__ == "__main__":
    # This allows running Phase 4 independently
    import config
    logging.info("Building Phase 4 graph...")
    app = build_phase4_graph()

    # This state assumes Phase 3 has set up an approved NFA
    initial_state = S2CState(
        current_agent="", errors=[], should_stop=False,
        db_path=config.DB_PATH, dms_root=config.DMS_ROOT, 
        nfa_approved=True # Needs to be true to trigger the first agent
    )

    logging.info("Invoking Phase 4 graph...")
    result = app.invoke(initial_state)

    print("\n--- Phase 4 Graph Execution Complete ---")
    if result.get('errors'):
        print(f"\nErrors occurred: {result['errors']}")
    else:
        print("\nExecution finished without critical errors.")
    print("--------------------------------")
