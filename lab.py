"""Independent APS-oriented battery research prototype. No APS affiliation.

Dispatch minimizes a single-node daily load-envelope proxy. It does NOT compute
APS procurement savings, accredited capacity, nodal flows, or merchant revenue.
Energy state is USABLE AC-deliverable MWh, not raw cell nameplate MWh.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Battery:
    power_mw: float
    duration_hours: float
    rte: float = 0.88
    power_factor: float = 1.0
    auxiliary_mw: float = 0.5
    initial_soc_fraction: float = 0.5

    def __post_init__(self):
        vals = [self.power_mw, self.duration_hours, self.rte,
                self.power_factor, self.auxiliary_mw, self.initial_soc_fraction]
        if not all(np.isfinite(vals)) or self.power_mw <= 0 or self.duration_hours <= 0:
            raise ValueError("Battery inputs must be finite with positive power/duration.")
        if not 0 < self.rte <= 1 or not 0 <= self.power_factor <= 1:
            raise ValueError("Efficiency must be (0,1]; power factor must be [0,1].")
        if self.auxiliary_mw < 0 or not 0 <= self.initial_soc_fraction <= 1:
            raise ValueError("Invalid auxiliary consumption or initial SOC.")

    @property
    def energy_mwh(self):
        return self.power_mw * self.duration_hours


def solve_day(load, battery: Battery, availability=None):
    """24-hour MILP with equal initial/terminal SOC and exclusive modes.

    Variables: charge[n], discharge[n], SOC[n+1], binary charge-mode[n], peak.
    SOC uses an AC-deliverable energy coordinate: SOC[t+1]=SOC[t]+rte*C-D.
    Constant auxiliaries are accounted for in the load envelope separately.
    Availability is assumed known at scheduling time; stochastic outages are
    outside this first version. Bounds and conservation are checked after solve.
    """
    load = np.asarray(load, dtype=float)
    n = len(load)
    if n != 24 or not np.isfinite(load).all() or (load < 0).any():
        raise ValueError("solve_day requires 24 finite nonnegative hourly loads.")
    avail = np.ones(n) if availability is None else np.asarray(availability, dtype=float)
    if avail.shape != load.shape or not np.isfinite(avail).all() or ((avail < 0) | (avail > 1)).any():
        raise ValueError("availability must contain 24 finite values in [0,1].")
    p = battery.power_mw * battery.power_factor * avail
    e = battery.energy_mwh
    # Index offsets: C=0, D=n, SOC=2n, mode=3n+1, peak=4n+1.
    s0, u0, z = 2*n, 3*n+1, 4*n+1
    size = z+1
    low = np.zeros(size)
    high = np.full(size, np.inf)
    high[:n] = p
    high[n:2*n] = p
    high[s0:s0+n+1] = e
    high[u0:u0+n] = 1
    low[s0] = high[s0] = battery.initial_soc_fraction * e
    low[s0+n] = high[s0+n] = battery.initial_soc_fraction * e
    integrality = np.zeros(size)
    integrality[u0:u0+n] = 1
    objective = np.zeros(size)
    objective[z] = 1
    objective[:2*n] = 1e-5  # Tie-breaker to avoid unnecessary energy throughput.
    rows, lbs, ubs = [], [], []
    for t in range(n):
        row = np.zeros(size)
        row[s0+t+1], row[s0+t] = 1, -1
        row[t], row[n+t] = -battery.rte, 1
        rows.append(row); lbs.append(0); ubs.append(0)
        row = np.zeros(size)
        row[t], row[u0+t] = 1, -p[t]
        rows.append(row); lbs.append(-np.inf); ubs.append(0)
        row = np.zeros(size)
        row[n+t], row[u0+t] = 1, p[t]
        rows.append(row); lbs.append(-np.inf); ubs.append(p[t])
        row = np.zeros(size)
        row[t], row[n+t], row[z] = 1, -1, -1
        rows.append(row); lbs.append(-np.inf)
        ubs.append(-load[t] - battery.auxiliary_mw)
    result = milp(objective, integrality=integrality,
                  bounds=Bounds(low, high),
                  constraints=LinearConstraint(np.array(rows), np.array(lbs), np.array(ubs)),
                  options={"mip_rel_gap": 1e-8, "time_limit": 20})
    if not result.success:
        raise RuntimeError(f"Dispatch solver failed: {result.message}")
    c = result.x[:n].clip(min=0)
    d = result.x[n:2*n].clip(min=0)
    soc = result.x[s0:s0+n+1]
    tol = 1e-5
    if (c > p+tol).any() or (d > p+tol).any() or (soc < -tol).any() or (soc > e+tol).any():
        raise RuntimeError("Post-solve physical bound violation.")
    if not np.allclose(np.diff(soc), battery.rte*c-d, atol=tol, rtol=0):
        raise RuntimeError("Post-solve energy balance violation.")
    if (np.minimum(c,d) > tol).any() or abs(soc[-1]-soc[0]) > tol:
        raise RuntimeError("Simultaneous modes or terminal energy violation.")
    return c, d, soc


def validate_frame(frame):
    required = {"timestamp_utc", "load_mw"}
    if not required.issubset(frame.columns):
        raise ValueError("CSV requires timestamp_utc and load_mw columns.")
    f = frame.copy()
    # Require an explicit UTC offset rather than silently assigning UTC to local data.
    if not f.timestamp_utc.astype(str).str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True).all():
        raise ValueError("timestamp_utc must include Z or an explicit timezone offset.")
    f["timestamp_utc"] = pd.to_datetime(f.timestamp_utc, utc=True, errors="raise")
    f = f.sort_values("timestamp_utc").reset_index(drop=True)
    f["load_mw"] = pd.to_numeric(f.load_mw, errors="raise")
    if len(f) < 24*8 or f.timestamp_utc.duplicated().any():
        raise ValueError("Need at least eight full days and no duplicate timestamps.")
    if not np.isfinite(f.load_mw).all() or (f.load_mw < 0).any():
        raise ValueError("Load must be finite and nonnegative; no silent imputation.")
    diff = f.timestamp_utc.diff().dropna()
    if not (diff == pd.Timedelta(hours=1)).all():
        raise ValueError("Missing or non-hourly interval: repair and document the input first.")
    if not ((f.timestamp_utc.dt.minute == 0) & (f.timestamp_utc.dt.second == 0)
            & (f.timestamp_utc.dt.microsecond == 0)).all():
        raise ValueError("All input timestamps must lie on hour boundaries.")
    local = f.timestamp_utc.dt.tz_convert("America/Phoenix")
    if local.iloc[0].hour != 0 or local.iloc[-1].hour != 23 or len(f) % 24:
        raise ValueError("Input must span complete Phoenix-local days (hour-start labels).")
    f["local_date"] = local.dt.strftime("%Y-%m-%d")
    f["hour_local"] = local.dt.hour
    if "availability" not in f:
        f["availability"] = 1.0
    f["availability"] = pd.to_numeric(f.availability, errors="raise")
    if not np.isfinite(f.availability).all() or ((f.availability < 0) | (f.availability > 1)).any():
        raise ValueError("Availability must be finite in [0,1].")
    return f


def synthetic_data(days=42, seed=42):
    """Fabricated Phoenix-style summer shape; zero actual APS observations."""
    rng = np.random.default_rng(seed)
    local = pd.date_range("2025-06-01", periods=days*24, freq="h", tz="America/Phoenix")
    h = local.hour.to_numpy()
    day = np.arange(days*24)//24
    evening = 1450*np.exp(-((h-18)/4.2)**2)
    broad = 350*np.exp(-((h-13)/5.5)**2)
    # Broad heat-event plateaus make duration matter in the demo.
    heat_event = (day % 17 >= 10) & (day % 17 <= 13)
    heatwave = np.where(heat_event, 500, 0)
    evening = np.where(heat_event & (h >= 13) & (h <= 22), 1450, evening)
    daily_shift = np.repeat(rng.normal(0, 90, days), 24)
    load = 4900 + evening + broad + heatwave + daily_shift + rng.normal(0,35,days*24)
    plateau = heat_event & (h >= 12) & (h <= 20)
    load = np.where(plateau, 7300+daily_shift, load)
    return pd.DataFrame({"timestamp_utc": local.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "load_mw": np.round(load,3), "availability": 1.0})


def forecast_day(frame, start):
    """Same hours seven days earlier, all known before target-day midnight.

    Historical revised data can contain revision leakage. This avoids target
    day lookahead only; true as-of replay requires archived data vintages.
    """
    if start < 168:
        raise ValueError("Need seven days of warmup history.")
    return frame.iloc[start-168:start-144].load_mw.to_numpy().copy()


def finance(config, hours):
    """Pre-tax unlevered real-dollar fixed-fee screen, no energy revenue stack.

    Model contract: buyer pays charging energy and variable dispatch costs;
    seller pays fixed O&M and one augmentation. No tax credits, debt, salvage,
    working capital, collateral carrying cost or transaction costs in v1.
    """
    p = float(config["power_mw"])*1000
    if not np.isfinite(p) or p <= 0 or not np.isfinite(hours) or hours <= 0:
        raise ValueError("Finance power and duration must be finite and positive.")
    kwh = p*hours
    r, life = float(config["real_discount_rate"]), int(config["life_years"])
    availability = float(config["paid_availability_fraction"])
    aug_year = int(config["augmentation_year"])
    if (not 0 <= r < 1 or life < 1 or not 0 < availability <= 1
            or not 1 <= aug_year <= life or life != config["life_years"]
            or aug_year != config["augmentation_year"]):
        raise ValueError("Invalid finance horizon, discount rate, availability or augmentation year.")
    cost_keys = ["power_cost_usd_per_kw", "energy_cost_usd_per_usable_ac_kwh",
                 "interconnection_usd", "development_usd", "contingency_fraction",
                 "augmentation_usd_per_usable_ac_kwh"]
    om_fraction = config.get("annual_fixed_om_fraction_of_capex")
    if om_fraction is not None:
        if "annual_fixed_om_usd_per_kw" in config:
            raise ValueError("Choose either fraction-of-capex or per-kW O&M, not both.")
        cost_keys.append("annual_fixed_om_fraction_of_capex")
    else:
        cost_keys.append("annual_fixed_om_usd_per_kw")
    if any(not np.isfinite(float(config[k])) or float(config[k]) < 0 for k in cost_keys):
        raise ValueError("Finance cost assumptions must be finite and nonnegative.")
    capex = (p*config["power_cost_usd_per_kw"] + kwh*config["energy_cost_usd_per_usable_ac_kwh"]
             + config["interconnection_usd"] + config["development_usd"])*(1+config["contingency_fraction"])
    fixed = capex*om_fraction if om_fraction is not None else p*config["annual_fixed_om_usd_per_kw"]
    augmentation = kwh*config["augmentation_usd_per_usable_ac_kwh"]
    annuity = sum((1+r)**(-t) for t in range(1,life+1))
    pv_cost = capex + fixed*annuity + augmentation/(1+r)**aug_year
    fee = pv_cost/(p*12*availability*annuity)
    return {"duration_hours": hours, "capex_usd": capex,
            "annual_fixed_om_usd": fixed, "augmentation_usd": augmentation,
            "required_fixed_fee_usd_per_kw_month": fee,
            "npv_at_required_fee_usd": -capex + (fee*p*12*availability-fixed)*annuity
                    - augmentation/(1+r)**aug_year}


def run(frame, config, outdir, provenance):
    frame = validate_frame(frame)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    hourly, summary = [], []
    for hours in config["durations_hours"]:
        b = Battery(config["power_mw"], hours, config["round_trip_efficiency"],
                    config["power_factor"], config["auxiliary_mw"], config["initial_soc_fraction"])
        for strategy in ["lag7_dispatch", "hindsight_daily_bound"]:
            pieces = []
            for start in range(168,len(frame),24):
                day = frame.iloc[start:start+24]
                actual = day.load_mw.to_numpy()
                forecast = forecast_day(frame,start)
                schedule = forecast if strategy == "lag7_dispatch" else actual
                c,d,s = solve_day(schedule,b,day.availability.to_numpy())
                piece = day[["timestamp_utc","local_date","hour_local","load_mw","availability"]].copy()
                piece["forecast_mw"] = forecast
                piece["charge_mw"], piece["discharge_mw"] = c,d
                piece["soc_start_mwh"],piece["soc_end_mwh"] = s[:-1],s[1:]
                piece["adjusted_load_proxy_mw"] = actual+c-d+b.auxiliary_mw
                piece["duration_hours"],piece["strategy"] = hours,strategy
                pieces.append(piece)
            data = pd.concat(pieces,ignore_index=True)
            hourly.append(data)
            daily = data.groupby("local_date").agg(base=("load_mw","max"),
                adjusted=("adjusted_load_proxy_mw","max"))
            top = data.nlargest(min(100,len(data)),"load_mw")
            discharge = float(data.discharge_mw.sum())
            summary.append({"data_mode": provenance["data_mode"], "duration_hours": hours,
                "strategy": strategy, "evaluated_days": len(daily),
                "baseline_period_peak_mw": float(data.load_mw.max()),
                "adjusted_period_peak_proxy_mw": float(data.adjusted_load_proxy_mw.max()),
                "period_peak_reduction_proxy_mw": float(data.load_mw.max()-data.adjusted_load_proxy_mw.max()),
                "mean_daily_peak_reduction_proxy_mw": float((daily.base-daily.adjusted).mean()),
                "worst_daily_peak_reduction_proxy_mw": float((daily.base-daily.adjusted).min()),
                "top100_hour_mean_net_support_mw": float((top.discharge_mw-top.charge_mw-b.auxiliary_mw).mean()),
                "forecast_mae_mw": float(np.abs(data.forecast_mw-data.load_mw).mean()),
                "charging_mwh": float(data.charge_mw.sum()), "discharging_mwh": discharge,
                "equivalent_cycles_usable_ac": discharge/b.energy_mwh,
                "auxiliary_mwh": b.auxiliary_mw*len(data),
                "power_factor": b.power_factor,
                "max_net_output_after_auxiliary_mw": b.power_mw*b.power_factor-b.auxiliary_mw,
                "capacity_credit_mw": None, "merchant_revenue_usd": None})
    all_hourly = pd.concat(hourly,ignore_index=True)
    all_hourly.to_csv(outdir/"hourly_dispatch.csv.gz", index=False,
                      compression={"method": "gzip", "mtime": 0})
    summaries = pd.DataFrame(summary)
    summaries.to_csv(outdir/"dispatch_summary.csv",index=False)
    pd.DataFrame([finance(config,h) for h in config["durations_hours"]]).to_csv(outdir/"finance_screen.csv",index=False)
    sensitivities=[]
    for h in config["durations_hours"]:
        for upgrades in [5e6,15e6,40e6]:
            for multiplier in [0.8,1.0,1.25]:
                c = dict(config,interconnection_usd=upgrades,
                         energy_cost_usd_per_usable_ac_kwh=config["energy_cost_usd_per_usable_ac_kwh"]*multiplier)
                sensitivities.append(dict(finance(c,h), upgrade_cost_usd=upgrades,energy_cost_multiplier=multiplier))
    pd.DataFrame(sensitivities).to_csv(outdir/"cost_sensitivity.csv",index=False)
    manifest = dict(provenance, config=config, python=platform.python_version(),
        package_versions={"numpy":np.__version__,"pandas":pd.__version__,"scipy":scipy.__version__},
        generated_at_utc=pd.Timestamp.now(tz="UTC").isoformat(),
        exclusions=["nodal flows","APS avoided costs","accredited capacity/ELCC","retail bill savings",
                    "merchant trading revenue","taxes/credits/debt","stochastic forced outages", "real-time controller"],
        data_quality={"input_rows":len(frame), "imputed_rows":0, "warmup_hours":168,
                      "timestamp_convention":"hour-start UTC; grouped America/Phoenix"})
    (outdir/"run_manifest.json").write_text(json.dumps(manifest,indent=2))
    make_plots(all_hourly,summaries,outdir,provenance["data_mode"],config["power_mw"])
    print(summaries[["duration_hours","strategy","period_peak_reduction_proxy_mw"]].to_string(index=False))
    print(f"Outputs: {outdir.resolve()} | {provenance['data_mode']}")


def make_plots(hourly, summary, outdir, mode, power_mw):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    example_duration=float(hourly.duration_hours.min())
    selected=hourly[(hourly.duration_hours==example_duration)&(hourly.strategy=="lag7_dispatch")]
    peak_day=selected.loc[selected.load_mw.idxmax(),"local_date"]
    day=selected[selected.local_date==peak_day]
    fig,(ax,ax2)=plt.subplots(2,1,figsize=(10,7),sharex=True,gridspec_kw={"height_ratios":[2,1]})
    ax.plot(day.hour_local,day.load_mw,label="Input demand",color="#172f42")
    ax.plot(day.hour_local,day.adjusted_load_proxy_mw,label="Load-envelope proxy with battery",color="#008781")
    ax.set_ylabel("Hourly average MW");ax.legend();ax.grid(alpha=.2)
    ax2.bar(day.hour_local,day.discharge_mw,label="Discharge",color="#008781")
    ax2.bar(day.hour_local,-day.charge_mw,label="Charge",color="#d89540")
    ax2.set_ylabel("Battery MW");ax2.set_xlabel("Phoenix local hour beginning");ax2.legend()
    fig.suptitle(f"{mode.upper()} - {power_mw:g} MW / {example_duration:g}-hour example, {peak_day}\nSingle-node screening proxy; no APS savings or capacity accreditation")
    fig.tight_layout();fig.savefig(outdir/"dispatch_example.png",dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5))
    for strategy,label in [("lag7_dispatch","Prior-week forecast"),("hindsight_daily_bound","Daily hindsight comparator")]:
        s=summary[summary.strategy==strategy]
        ax.plot(s.duration_hours,s.period_peak_reduction_proxy_mw,marker="o",label=label)
    ax.set_xlabel("Usable AC duration (hours)");ax.set_ylabel("Period peak reduction proxy (MW)")
    ax.set_xticks([4,6,8]);ax.grid(alpha=.2);ax.legend()
    ax.set_title(f"{mode.upper()} - duration comparison\nProxy output, not ELCC or an APS procurement result")
    fig.tight_layout();fig.savefig(outdir/"duration_comparison.png",dpi=160);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=ROOT/"config.json")
    parser.add_argument("--input",type=Path)
    parser.add_argument("--out",type=Path,default=ROOT/"results"/"demo")
    parser.add_argument("--demo-days",type=int,default=42)
    parser.add_argument("--source-label",help="Required with --input; explicit provenance.")
    parser.add_argument("--power-factor",type=float,help="Illustrative heat derating factor, e.g. 0.9")
    args=parser.parse_args()
    config=json.loads(args.config.read_text())
    if args.power_factor is not None: config["power_factor"]=args.power_factor
    if args.input:
        if not args.source_label: parser.error("--input requires --source-label")
        frame=pd.read_csv(args.input)
        provenance={"data_mode":"user-supplied", "source_label":args.source_label,
                    "input_sha256":sha256(args.input.read_bytes()).hexdigest()}
    else:
        if args.demo_days < 8: parser.error("--demo-days must be at least 8")
        frame=synthetic_data(args.demo_days)
        args.out.mkdir(parents=True,exist_ok=True)
        frame.to_csv(args.out/"synthetic_input.csv",index=False)
        provenance={"data_mode":"synthetic-demo", "source_label":"Fabricated summer shapes; no actual APS data", "seed":42,
                    "input_sha256":sha256((args.out/"synthetic_input.csv").read_bytes()).hexdigest()}
    run(frame,config,args.out,provenance)


if __name__=="__main__": main()
