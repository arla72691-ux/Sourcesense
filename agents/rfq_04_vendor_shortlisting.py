# agents/rfq_04_vendor_shortlisting.py
import logging
import json
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google import genai
from state import S2CState
from db import get_db
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
client = genai.Client(api_key=config.GEMINI_API_KEY)

def vendor_shortlisting(state: S2CState) -> S2CState:
    """
    LangGraph node: RFQ.04 — Vendor Shortlisting
    """
    logging.info("Entering RFQ.04 - Vendor Shortlisting agent.")
    state['current_agent'] = "rfq_04_vendor_shortlisting"
    errors = state.get('errors', [])

    try:
        with get_db(state['db_path']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Consolidated_PRs WHERE PR_Status = 'Buyer_Assigned'")
            clusters_to_process = cursor.fetchall()

            if not clusters_to_process:
                logging.info("No clusters ready for vendor shortlisting.")
                return state

            for cluster in clusters_to_process:
                cluster_id = cluster['Consolidation_Cluster_ID']
                material_code = cluster['Material_Code']
                logging.info(f"Processing cluster {cluster_id} for material {material_code}")

                # Steps 1-5: Query and score vendors
                # This is a complex query joining multiple tables as per requirements.
                # Note: This query is illustrative and assumes schema details.
                # Performance in a real DB would require indexed tables.
                sql = '''
                    SELECT
                        vm.Vendor_Code, vm.GSTIN, sm.Overall_Score,
                        COALESCE(mp.avg_delivery_pct, 0) as avg_delivery_pct,
                        COALESCE(mp.total_quality_incidents, 0) as total_quality_incidents,
                        COALESCE(vh.Total_POs_12M, 0) as Total_POs_12M,
                        vm.MSME_Category
                    FROM Vendor_Master vm
                    JOIN Supplier_Master sm ON vm.Vendor_Code = sm.Supplier_Code
                    LEFT JOIN (
                        SELECT Supplier_Code, AVG(Delivery_On_Time_Pct) as avg_delivery_pct, SUM(Quality_Incidents) as total_quality_incidents
                        FROM Monthly_Performance
                        WHERE date(Month || '-01') >= date('now', '-3 months')
                        GROUP BY Supplier_Code
                    ) mp ON vm.Vendor_Code = mp.Supplier_Code
                    LEFT JOIN (
                        SELECT Vendor_Code, SUM(Total_POs_12M) as Total_POs_12M
                        FROM Vendor_History
                        WHERE Material_Code = ? AND date(Last_PO_Date) >= date('now', '-12 months')
                        GROUP BY Vendor_Code
                    ) vh ON vm.Vendor_Code = vh.Vendor_Code
                    WHERE vm.Active_Status = 'Active' AND vm.Blacklisted = 0
                '''
                cursor.execute(sql, (material_code,))
                potential_vendors = cursor.fetchall()

                scored_vendors = []
                for vendor in potential_vendors:
                    # CTRL-008: Check Onboarding_Tracker
                    cursor.execute("SELECT Finance_Decision FROM Onboarding_Tracker WHERE GST_Number = ?", (vendor['GSTIN'],))
                    onboarding = cursor.fetchone()
                    if not onboarding or onboarding['Finance_Decision'] != 'Approved':
                        cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?, ?, ?, ?, ?, ?)",
                                       ('CTRL-008', 'Vendor', vendor['Vendor_Code'], 'Fail', 'Vendor not fully onboarded or approved.', datetime.datetime.now().isoformat()))
                        continue # Exclude vendor
                    else:
                         cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?, ?, ?, ?, ?, ?)",
                                       ('CTRL-008', 'Vendor', vendor['Vendor_Code'], 'Pass', 'Vendor onboarding approved.', datetime.datetime.now().isoformat()))

                    # Step 8: Scoring Logic
                    material_experience_score = 0
                    if vendor['Total_POs_12M'] > 5:
                        material_experience_score = 100
                    elif vendor['Total_POs_12M'] > 0:
                        material_experience_score = 60
                    else:
                        material_experience_score = 30
                    
                    score = (vendor['Overall_Score'] * 0.4) + (vendor['avg_delivery_pct'] * 0.3) + (material_experience_score * 0.3)
                    scored_vendors.append(dict(vendor) | {"calculated_score": round(score, 2)})
                
                # CTRL-007 Log (Blacklist check is in the initial SQL WHERE clause)
                cursor.execute("INSERT INTO Compliance_Log (Control_ID, Entity_Type, Entity_ID, Result, Details, Checked_At) VALUES (?, ?, ?, ?, ?, ?)",
                               ('CTRL-007', 'Cluster', cluster_id, 'Pass', 'Blacklisted vendors excluded from query.', datetime.datetime.now().isoformat()))

                # Step 9: Call Gemini to recommend final shortlist
                prompt = f"""Review these vendor scores for material {material_code}. 
                Recommend 3-5 vendors considering: compliance history, material-specific experience, and MSME diversity (prefer including at least 1 MSME vendor if available).
                Vendors:
                {json.dumps(scored_vendors, indent=2)}

                Output JSON: [{{"vendor_code": "...", "reason": "...", "recommended_rank": ...}}]"""

                response = client.models.generate_content(model="gemini-2.5-pro", contents=prompt)
                cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
                shortlist = json.loads(cleaned_json)

                # Step 10 & 11: Update DB with shortlist
                # RFQ_ID is NULL at this stage — backfilled by RFQ.05 once RFQ is generated
                for vendor in shortlist:
                    cursor.execute(
                        "INSERT INTO Vendor_Shortlist (RFQ_ID, Vendor_Code, Shortlist_Reason, Historical_Score, Added_At) VALUES (?, ?, ?, ?, ?)",
                        (None, vendor['vendor_code'], vendor['reason'],
                         vendor.get('calculated_score', 0), datetime.datetime.now().isoformat())
                    )
                
                cursor.execute("UPDATE Consolidated_PRs SET PR_Status = 'Vendors_Shortlisted' WHERE Consolidation_Cluster_ID = ?", (cluster_id,))
                logging.info(f"Final shortlist for {cluster_id} created with {len(shortlist)} vendors.")

                # Step 13: Log Process Event
                cursor.execute("INSERT INTO Process_Events_Log (Process_ID, Entity_Type, Entity_ID, Event_Type, Event_Description, Actor, Created_At) VALUES (?,?,?,?,?,?,?)",
                               ('S2C.RFQ.04', 'Cluster', cluster_id, 'VendorShortlist', f'{len(shortlist)} vendors shortlisted by AI.', 'Agent:RFQ.04', datetime.datetime.now().isoformat()))

    except Exception as e:
        logging.error(f"An error occurred in Vendor Shortlisting: {e}", exc_info=True)
        errors.append(str(e))

    state['errors'] = errors
    logging.info("Exiting RFQ.04.")
    return state
