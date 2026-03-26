# S2C Agent Flow Map — Input/Output Entity Reference

> **How to read this:** Each row is one workflow agent. "Input Tables" = entities the agent reads from. "Output Tables" = entities the agent writes to or updates.
> Color key: 🔵 MDM · 🟢 ERP/SAP · 🟣 STM · 🟡 DMS · 🔴 Compliance

---

| # | Agent | Process | Input Tables | Output Tables |
|---|-------|---------|--------------|---------------|
| PR.01 | PR Initiator | User raises a purchase request; agent validates requester, material, and budget | 🔵 Material_Master · 🔵 UOM_Master · 🔵 Designation_Master | 🟣 Master_PR · 🟣 Consolidated_PRs |
| PR.02 | PR Enrichment | Pulls historical price, vendor history, and demand patterns to enrich the PR with baseline cost and urgency data | 🔵 Material_Master · 🔵 Vendor_Master · 🟣 Historical_Prices · 🟣 Demand_Offload_Profile · 🟣 Vendor_History | 🟣 Consolidated_PRs (enriched fields) |
| PR.03 | PR Approval Router | Routes PR to approver based on designation hierarchy; logs approval event | 🔵 Designation_Master · 🟣 Consolidated_PRs | 🟣 Approval_Log · 🟣 SVJ_Log · 🟣 Process_Events_Log |
| RFQ.04 | Vendor Shortlisting | Identifies eligible vendors for the category; applies historical performance filter | 🔵 Vendor_Master · 🔵 Supplier_Onboarding · 🟣 Monthly_Performance · 🟣 Vendor_History · 🟣 Consolidated_PRs | 🟣 Vendor_Shortlist |
| RFQ.05 | RFQ Creation | Generates RFQ document, sets evaluation criteria and submission deadline | 🔵 Material_Master · 🟣 Consolidated_PRs · 🟣 Vendor_Shortlist | 🟣 RFQ_Log · 🟡 DMS_Documents |
| RFQ.06 | Spec & Compliance Attach | Attaches technical specifications and compliance requirements to RFQ | 🔵 Material_Specs_Refs · 🟣 RFQ_Log | 🟣 Special_Requisitions · 🔴 Compliance_Log |
| RFQ.07 | Vendor Submission Portal | Vendors submit bids; agent captures and validates submission structure | 🟣 RFQ_Log · 🟣 Vendor_Shortlist | 🟣 Submissions · 🟣 Process_Events_Log |
| EVAL.08 | Technical Evaluation | Scores each submission against technical specs | 🟣 Submissions · 🟣 Special_Requisitions · 🔵 Material_Specs_Refs | 🟣 Technical_Evaluation |
| EVAL.09 | Commercial Evaluation | Scores price, payment terms, lead time; references historical prices | 🟣 Submissions · 🟣 Historical_Prices · 🟣 Vendor_History | 🟣 Commercial_Evaluation |
| EVAL.10 | Overall Evaluation & Ranking | Combines tech + commercial scores into weighted overall rank | 🟣 Technical_Evaluation · 🟣 Commercial_Evaluation | 🟣 Overall_Evaluation |
| NEG.11 | Negotiation Initiation | Opens negotiation with shortlisted vendor(s); logs negotiation rounds | 🟣 Overall_Evaluation · 🟣 Consolidated_PRs | 🟣 Negotiation_Log · 🟣 Process_Events_Log |
| NEG.12 | Negotiation Approval | Routes final negotiated terms for internal approval | 🔵 Designation_Master · 🟣 Negotiation_Log | 🟣 Negotiation_Approval · 🟣 Approval_Log |
| NFA.13 | NFA Document Generation | Generates Note for Approval (NFA) from evaluation + negotiation outcome | 🟣 Overall_Evaluation · 🟣 Negotiation_Approval · 🟣 Consolidated_PRs | 🟣 NFA_Log · 🟡 DMS_Documents |
| NFA.14 | NFA Approval Routing | Routes NFA through multi-level approver chain per designation hierarchy | 🔵 Designation_Master · 🟣 NFA_Log | 🟣 NFA_Approval_Log · 🟣 Approval_Log · 🟣 Process_Events_Log |
| PO.15 | PO Reference Creation | On NFA approval, creates a PO reference record in STM linking NFA to the forthcoming SAP PO | 🟣 NFA_Approval_Log · 🟣 NFA_Log · 🟣 Consolidated_PRs | 🟣 PO_Reference |
| PO.16 | SAP BAPI Call (PO Creation) | Calls BAPI_PO_CREATE1 via n8n; creates PO in SAP ERP using vendor/material master data | 🟣 PO_Reference · 🔵 Vendor_Master · 🔵 Material_Master · 🟢 SAP_PO_Data (read-back) | 🟢 SAP_PO_Data (written by ERP) · 🟣 PO_Reference (updated with EBELN) |
| PO.17 | PO Document Attach | Attaches signed PO document to DMS and links to PO Reference | 🟣 PO_Reference · 🟢 SAP_PO_Data | 🟡 DMS_Documents · 🔴 Compliance_Log |
| PO.18 | Vendor Dispatch Notification | Sends PO to vendor; records dispatch confirmation | 🟣 PO_Reference · 🟢 SAP_PO_Data · 🔵 Vendor_Master | 🟣 Dispatch_Log · 🟣 Process_Events_Log |
| PO.19 | Consolidated PR Status Update | Marks Consolidated_PRs record as PO-issued; stamps final timestamp | 🟣 PO_Reference · 🟢 SAP_PO_Data | 🟣 Consolidated_PRs (po_issued_date, po_number) |

---

## Entity System Legend

| System | Tag | Tables |
|--------|-----|--------|
| Master Data (MDM) | 🔵 | Material_Master, Vendor_Master, Buyer_Master, Supplier_Onboarding, Designation_Master, UOM_Master, Material_Specs_Refs |
| SAP ERP | 🟢 | SAP_PO_Data (EKKO/EKPO), Vendor_History (MM60), Monthly_Performance, Historical_Prices |
| S2C STM (Transaction) | 🟣 | Consolidated_PRs, Master_PR, RFQ_Log, Vendor_Shortlist, Special_Requisitions, Submissions, Technical_Evaluation, Commercial_Evaluation, Overall_Evaluation, Negotiation_Log, Negotiation_Approval, NFA_Log, NFA_Approval_Log, PO_Reference, SVJ_Log, Dispatch_Log, Approval_Log, Process_Events_Log |
| DMS | 🟡 | DMS_Documents |
| Compliance | 🔴 | Compliance_Log |

---

## Key Data Hub

**`Consolidated_PRs`** is the central lifecycle record — every agent either reads from it or writes back to it.
It carries 15+ timestamp fields tracking the PR from creation → approval → RFQ → evaluation → negotiation → NFA → PO issued.

*Generated: 2026-03-20 | S2C Process Architecture v3*
