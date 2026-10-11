# Application and interview notes

Project: **APS Battery Feasibility Lab**  
Repository: https://github.com/jfasoxx/aps-battery-feasibility-lab

## Project description

An independent Python research prototype for APS-oriented battery development.
It compares 100 MW batteries with 4-, 6-, and 8-hour usable AC duration using
physically constrained dispatch, a prior-week demand forecast, a daily hindsight
comparator, and a fixed-contract-fee financial screen. The primary experiments
use measured EIA AZPS demand for summers 2024-2026 and illustrative costs. A
separate synthetic demo is retained. Public APS planning documents frame
the questions; the project does not claim utility endorsement or project approval.

## Suggested application paragraph

I developed an AI-assisted battery storage research prototype focused on Arizona
Public Service. The project combines mixed-integer dispatch optimization, data
validation, and a transparent financial screen to compare 4-, 6-, and 8-hour
batteries. Its measured-demand experiments show why additional battery energy alone
does not solve poor dispatch timing: the prior-week schedule misses the highest
2025 summer demand hour even when hindsight can use the same battery effectively. The repository
includes an executed notebook, auditable CSV results, 14 tests, and a documented
path to evaluating future net load and site-specific development evidence.

Use this after you have run the project and can explain the model. Adapt the
wording to the work you actually performed; this repository was prepared with
AI assistance and should not be described as entirely unaided work.

## Suggested resume entry

**APS Battery Feasibility Lab | Python, SciPy, pandas, MILP**

- Developed an AI-assisted storage research prototype comparing three battery
  durations across forecast and hindsight dispatch on three measured AZPS summers.
- Implemented energy conservation, power and state-of-charge constraints,
  exclusive operating modes, timezone validation, and discounted cash-flow checks.
- Documented forecast failures, cost sensitivities, and the measured data and
  interconnection evidence needed before drawing investment conclusions.

## Five-minute reviewer path

1. Read the README's result table and evidence boundary.
2. Open `notebooks/APS_Battery_Review.ipynb` for executed comparisons and figures.
3. Inspect `lab.py` and `verify_results.py` for optimization and independent audits.
4. Review `PROJECT_GUIDE.md` or `docs/APS_Project_Guide.pdf` for development context.
5. Run the quick-start commands to reproduce the demo.

## Interview rehearsal

| Question | Answer to understand |
|---|---|
| Why Arizona and APS? | Their published planning and storage procurement documents give a concrete context for duration, summer performance and development questions. |
| What does the optimizer minimize? | The maximum of a single-node daily load-envelope proxy, with a small throughput tie-breaker. It does not minimize utility production cost. |
| Where do losses enter? | In usable AC energy: next SOC equals current SOC plus 0.88 times charging energy minus discharged energy. Auxiliaries separately increase the load proxy. |
| Why are the modes exclusive? | A binary variable prevents simultaneous charging and discharging in one hourly interval. |
| Why return to the starting SOC? | It prevents borrowing energy from the initial battery state and calling that repeatable benefit. Daily resets also limit realism for multi-day events. |
| Why did the forecast fail? | Prior-week timing does not match the actual highest-demand 2025 hour. More battery energy cannot help when the schedule misses the critical hours. |
| Why show hindsight? | It separates scheduling error from battery constraints within the same daily problem. It is not an achievable operational forecast. |
| What is the fixed fee? | A hypothetical payment per nominal kW-month that gives zero modeled project NPV at an assumed real discount rate. It is not an APS price quote. |
| What establishes real feasibility? | Measured grid data, site control, interconnection studies, permits, equipment quotes, commercial terms and a complete financing model. |
| What would you improve first? | Validate several measured years, then introduce archived forecasts, rolling SOC carryover, manufacturer heat curves and outage scenarios. |

## Evidence you can cite

The measured study evaluates 122 days per summer after seven days of forecast
warmup. Each of six comparisons in each summer has 2,928 hourly records. Four-hour
prior-week period-peak reductions are 99.5 MW in 2024, -0.5 MW in 2025 and 34.5 MW
in 2026. Hindsight reaches 99.5 MW in all three. Costs remain illustrative, and
these responses are model output rather than measured savings or ELCC.

## Before you submit

Run the demo, explain one day's SOC calculation, reconstruct one financial fee,
and inspect the worst forecast day in the notebook. Check that your application
matches the implemented scope. The public workbook route was downloaded and validated for the bundled periods.
The separate authenticated EIA API route remains mock-tested rather than live verified.
