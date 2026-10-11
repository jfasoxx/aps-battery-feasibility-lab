# Primary source register

Reviewed October 10, 2026. Facts below frame the research project; numerical
configuration costs and demo load are original illustrative assumptions.

| ID | Source | What it supports / limitation |
|---|---|---|
| S1 | [APS resource planning](https://www.aps.com/en/About/Our-Company/Doing-Business-with-Us/Resource-Planning) | Public planning materials and the ongoing 2026 IRP process; use dated materials rather than treating the 2023 plan as current. |
| S2 | [APS RFP overview](https://www.aps.com/en/About/Our-Company/Doing-Business-with-Us/Resource-Planning/Request-for-Proposals) | Published 2025 solicitation sought at least 1,000 MW; target operation 2029-2031, with earlier/later consideration. This is not an assertion that bids remain open. |
| S3 | [2025 APS All-Source RFP, revised January 6, 2026](https://www.aps.com/-/media/APS/APSCOM-PDFs/About/Our-Company/Doing-business-with-us/Resource-Planning-and-Management/2025_All-Source_RFP.pdf?hash=57E9C2BF07FE23189E8C5062BBFFF795&sc_lang=en) | Printed pp. 4, 12, 37-39: deadline, storage contracts and technical reference. Proprietary platform appendices were not accessed. |
| S4 | [APS RPAC presentation, September 30, 2026](https://www.aps.com/-/media/APS/APSCOM-PDFs/About/Our-Company/Doing-business-with-us/Resource-Planning-and-Management/Sept_26_RPAC_Meeting_Presentation.pdf?hash=CA3C9ECF52D69B2C1A46FABB26B63764&sc_lang=en) | Slide 7: 51 shortlisted proposals and multiple battery durations. Draft planning scenarios are preliminary; not treated as final approvals or a bid recommendation. |
| S5 | [Pinnacle West / APS Q1 2026 filing](https://www.sec.gov/Archives/edgar/data/7286/000076462226000025/pnw-20260331.htm) | 3,606 MW of battery storage contracted through the 2023 procurement, expected in service 2026-2028 at filing. Contracted is not the same as operating; later filings can change status. |
| S6 | [APS Markets+ announcement](https://www.aps.com/en/About/Our-Company/Newsroom/Articles/AZ_Utilities_Plan_to_Join_Markets_Plus_to_Strengthen_Grid_Reliability_and_Resilience) | Participation expected as early as 2027. A plan is not confirmation of live participation. Future market rules require a separately dated adapter. |
| S7 | [CAISO APS EIM implementation agreement library](https://www.caiso.com/library/arizona-public-service-energy-imbalance-market-implementation-agreement) | Historical APS energy imbalance market implementation documentation; does not establish every present-day settlement or future rule. |
| S8 | [EIA AZPS grid monitor](https://www.eia.gov/electricity/gridmonitor/dashboard/electric_overview/balancing_authority/AZPS) | Public AZPS demand, forecast, generation and interchange overview. Measured snapshots in this release come from the public workbook listed in S17. |
| S9 | [EIA-930 instructions](https://www.eia.gov/survey/form/eia_930/instructions.pdf) | pp. 3 and 5: hour-ending UTC reporting and treatment of known energy-storage charging. This is physical grid reporting, not a retail tariff or node price series. |
| S10 | [EIA API technical documentation](https://www.eia.gov/opendata/documentation.php) | API keys, metadata, facets and pagination. The included downloader is mock-tested, not live authenticated end-to-end verified. |
| S11 | [APS FERC generator interconnections](https://www.aps.com/en/About/Our-Company/Doing-Business-with-Us/FERC-Generator-Interconnections) | Public entry point for APS OATT/OASIS and interconnection materials. No queue snapshot, system study or available capacity was inferred. |
| S12 | [Phoenix fire permit forms](https://www.phoenix.gov/administration/departments/fire/safety-prevention/fire-permit-forms.html) | Municipal battery/solar permit resources. Site-specific jurisdiction and current requirements must be confirmed; Phoenix rules do not govern every Arizona parcel. |
| S13 | [NREL/NLR 2024 ATB utility-scale battery framework](https://atb.nrel.gov/electricity/2024/2023/utility-scale_battery_storage) | Search-indexed historical power/energy cost and duration framework only. Full page did not open in this session. No numeric costs in this repository are represented as ATB values or current quotes. |
| S14 | [SciPy MILP reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) | Solver interface, integrality, bounds and linear constraints. The implementation separately checks physical feasibility. |
| S15 | [2025 ATB utility-scale battery storage](https://atb.nlr.gov/electricity/2025/utility-scale_battery_storage) | Reviewed full page October 10, 2026. 85% round-trip efficiency, 15-year lifetime and fixed O&M at 4% of capex including augmentation inform a separate sensitivity. Capital cost numbers remain illustrative and are not extracted ATB values. |
| S16 | [Berkeley Lab Queued Up 2026](https://emp.lbl.gov/queues) | June 2026 report with end-2025 queue data. Provides national interconnection-risk context; national outcomes are not APS-specific completion probabilities or upgrade estimates. No queue dataset is redistributed. |
| S17 | [EIA public AZPS workbook](https://www.eia.gov/electricity/gridmonitor/knownissues/xls/AZPS.xlsx) | Downloaded and inspected including Published Hourly Data and Notes. Canonical summer extracts use Adjusted demand, retain one explicit 2026 EIA adjustment, and include a raw reported-demand sensitivity. Source hashes and timestamp conversions are recorded beside each CSV. |
| S18 | [GitHub Python validation documentation](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) | Official workflow reference for the repository's reproducibility checks. Local scientific tests and audits are distinct from remote workflow status. |

## Evidence boundaries

- APS's confidential bids, detailed system-dispatch inputs, asset-specific
  settlement data, private safety appendices and utility avoided costs are absent.
- No vendor quote, land option, network-upgrade estimate, tax eligibility opinion,
  debt term sheet or negotiated APS fee has been obtained.
- A source's publication date and retrieval date are different. Older filings
  describe their reporting period, not necessarily conditions on October 10, 2026.
- Sources are linked rather than redistributed. This repository does not claim
  APS endorsement or use APS branding.
