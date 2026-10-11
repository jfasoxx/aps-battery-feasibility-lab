# Measured AZPS study and industry review

Research cut: October 10, 2026. Independent research, with no APS affiliation.

## What makes this useful for an energy reviewer

The project serves a specific decision: whether additional storage duration
deserves further diligence for an APS-oriented development case. It connects
the decision to measured demand, physical operating limits and explicit costs.
It reports an operational baseline that can fail, rather than treating foresight
as a forecast. Another reader can reproduce the calculations and trace the
source data. These are project-design judgments, not a claim about any employer's
formal hiring criteria.

For development work, technical output must lead to a concrete next diligence
step. A capacity-shaped chart alone does not establish deliverability, permits,
bankability or the price a buyer will pay. For power markets work, a credible
backtest needs a clear information boundary and an executable settlement model.
This lab implements the dispatch screen and a hypothetical fixed-fee contract
model, while documenting the evidence still required for those broader decisions.

## Recent sources that changed the work

| Evidence | Why it matters | Implementation |
|---|---|---|
| APS 2025 All-Source RFP, January 6, 2026 revision, pp. 37-39 | Four-hour extreme-condition delivery, longer-duration preferences, and availability references | Compare 4/6/8 hours and a 10% power derating scenario. No claim of design certification. [S3] |
| APS September 30, 2026 RPAC presentation, slide 7 | Storage durations remain part of the shortlisted resource discussion | Use current procurement context, with draft planning scenarios identified as preliminary. [S4] |
| NLR 2025 utility-scale storage ATB | Provides a newer performance and O&M benchmark | Add an 85% efficiency, 15-year life, 4%-of-capex O&M scenario with separate augmentation set to zero. [S15] |
| Berkeley Lab Queued Up 2026, June 2026 report using end-2025 queues | Interconnection remains a material development bottleneck | Retain upgrade-cost sensitivity and require site-specific studies before investment selection. [S16] |
| EIA public AZPS workbook, downloaded October 11 UTC / October 10 Phoenix | Contains measured demand and explicit adjustments | Bundle three summer snapshots and preserve hashes, provenance and a reported-value sensitivity. [S17] |

APS's RFP deadline has passed. Its published terms are a research reference,
not an invitation to submit a bid now. The current planning page also lists an
October 14, 2026 stakeholder meeting. Recheck planning materials before using
this project for a later application. [S1-S4]

## Dataset and quality findings

The primary dataset uses EIA's **Adjusted demand** column consistently. It is
reported demand except where EIA applies an adjustment. Each year covers
May 25 through September 30, with May 25-31 reserved for forecast warmup.
Evaluation is June 1 through September 30: 122 complete Phoenix-local days
and 2,928 hourly observations per strategy and duration. The three inputs have
9,288 rows, including warmup. No hours were filled or discarded by this lab.

| Summer | Input rows | Locally filled hours | EIA demand adjustments |
|---|---:|---:|---:|
| 2024 | 3,096 | 0 | 0 |
| 2025 | 3,096 | 0 | 0 |
| 2026 | 3,096 | 0 | 1 |

The adjusted hour is May 27, 2026, 15:00 UTC beginning / 08:00 Phoenix beginning.
The workbook's reported Demand is 20,345 MW; its Adjusted demand is 2,309 MW.
This lies in warmup, so it changes the lag-7 forecast for June 3 rather than the
measured evaluation demand. The raw reported-value case is retained in
`data/public/azps_summer_2026_reported_raw.csv` and `results/measured/2026_reported_raw`.
Correcting it lowers forecast MAE from about 747.07 to 742.09 MW but leaves the
period-peak result unchanged. An unchanged headline does not erase a data issue.

UTC labels in the workbook denote hour endings. They are shifted back one hour,
then grouped in America/Phoenix. A one-hour MWh quantity has the same numerical
value as its average MW. These are revised balancing-authority observations,
not exclusively APS retail sales, a demand forecast vintage, or a reconstruction
of system net load. Existing grid resources already affect the observed history.

## Executed findings

| Summer | 4-hour lag-7 peak reduction proxy (MW) | 4-hour hindsight peak reduction proxy (MW) | Mean daily lag-7 reduction proxy (MW) |
|---|---:|---:|---:|
| 2024 | 99.50 | 99.50 | 54.88 |
| 2025 | -0.50 | 99.50 | 38.69 |
| 2026 | 34.50 | 99.50 | 33.32 |

The nominal power rating is 100 MW before the assumed 0.5 MW auxiliary load.
Thus 99.5 MW is the maximum modeled net support. The reported peak reduction
compares the largest demand value with the largest adjusted load-envelope value
over the same summer. It is not ELCC, avoided utility cost or a dispatch guarantee.

The 6- and 8-hour configurations have the same period-peak results as four hours
in each measured summer. Under hindsight, mean daily reductions also saturate at
the modeled power limit. Under the prior-week forecast, extra energy can change
the schedule and sometimes **lower** realized mean daily peak support. Larger
energy capacity does not guarantee a better outcome when dispatch is based on
the wrong demand shape.

With the illustrative 10% power derating in 2026, the four-hour lag-7 period-peak
reduction is 24.5 MW and hindsight is 89.5 MW. The derating is a stress assumption,
not a measured temperature response curve. The 85% efficiency benchmark keeps
the 2026 period-peak result at 34.5 / 99.5 MW but changes energy throughput and
some daily results. A stable headline metric can coexist with different operating
requirements.

## Cost and benchmark interpretation

The original illustrative financial case requires approximately $14.28, $17.95
and $21.62 per nominal kW-month for 4-, 6- and 8-hour systems. Every capital cost
remains an assumption. The measured demand does not turn those costs into quotes
or those fees into attainable APS contract prices.

The ATB-inspired sensitivity uses published **performance conventions**, not
an extracted ATB capital-cost series. Its 4% O&M rate is applied to this lab's
total illustrative project capex, including its site allowances. That scope is
an analytical choice and differs from a direct mapping of an ATB battery-only
cost boundary. Because the benchmark O&M convention includes augmentation,
the separate year-10 augmentation expense is zero in that case. The original
case retains its separate augmentation. See `config_atb_performance.json`. [S15]

Developer collateral is another omitted financing need: the RFP's storage PPA
table lists development/post-development security of $200/$160 per kW for
four hours and $300/$240 per kW for six-plus hours. At an assumed 100 MW contractual
rating, these correspond to $20/$16 million and $30/$24 million. Actual contractual
rating must use the delivery-meter boundary. These are security amounts, not
automatically lost project expenses. Letter-of-credit fees, posted-cash opportunity
cost and release timing need their own cash-flow schedule before being added to
the model. [S3, pp. 16-18]

## Recommendation and next decision

Use **four hours as the reference case for further diligence**, and keep six/eight
hours as alternatives. This recommendation is limited to the implemented 100 MW,
daily load-envelope screen: measured summer period peaks do not demonstrate an
incremental benefit from longer duration, while the illustrative fees increase.
It does not select a physical project or resolve future APS capacity value.

Before deciding duration for an actual project, obtain the buyer's hourly value
or dispatch requirement, assess future net-load shapes, introduce rolling SOC
across days, measure heat and outage performance, and apply capacity accreditation
with the relevant reliability model. Then evaluate quoted equipment costs and
site-specific upgrades under a complete contract and financing case. Those inputs
could justify longer duration even when this historical demand-only screen does not.

## What is implemented and what remains open

Implemented: three measured summers, an explicit data adjustment sensitivity,
heat-power stress, an ATB-inspired performance/finance sensitivity, independent
export audits, 14 automated tests, and an executed reviewer notebook.

Open: load-growth scenarios, full-year and multi-day energy adequacy, weather-driven
forecasting, nodal flows, ELCC, reserve co-optimization, aging and warranty limits,
stochastic outages, site studies, current tax and tariff analysis, commercial quotes
and financed returns. The model does not schedule existing APS assets or value
the utility's entire portfolio.

All findings above are traceable to included CSVs and manifests. Run `python
run_study.py` to regenerate the measured experiments. The public workbook can be
refreshed with `fetch_public_eia.py`; revisions may change results. The optional
authenticated EIA API adapter remains mock-tested rather than live verified.
