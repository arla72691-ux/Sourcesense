#!/usr/bin/env python3
"""
Sourcesense S2C Platform — Main entry point.
"""
import argparse
import logging
from graphs.master_graph import build_master_graph
from state import S2CState
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Run the Sourcesense S2C platform.")
    parser.add_argument("--phase", type=str, help="Run a specific phase (1, 2, 3, 4, or all)")
    # Add more arguments for other commands as needed

    args = parser.parse_args()

    initial_state = S2CState(
        cluster_id=None, rfq_id=None, nfa_id=None, po_ref_id=None,
        current_agent="", next_agent=None, pr_status=None,
        consolidated_clusters=[], specs_extracted=False, buyer_assigned=None,
        vendors_shortlisted=[], rfq_created=False, evaluations_complete=False,
        negotiated_price=None, nfa_approved=False, po_created=False,
        sap_po_number=None, errors=[], compliance_results={}, should_stop=False,
        db_path=config.DB_PATH, dms_root=config.DMS_ROOT
    )

    if args.phase:
        if args.phase == 'all':
            logging.info("Building and running the full master graph.")
            app = build_master_graph()
            result = app.invoke(initial_state)
            logging.info(f"Master graph finished with final state: {result}")
        else:
            # Logic to run individual phase graphs
            logging.info(f"Running Phase {args.phase} only.")
            # Example: if args.phase == '1': build_phase1_graph().invoke(initial_state)
            pass
    else:
        logging.info("No action specified. Use --phase all to run the full pipeline.")

if __name__ == "__main__":
    main()
