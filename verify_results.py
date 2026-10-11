"""Independently audit exported dispatch and finance records, without rerunning MILP."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd


def audit_results(outdir):
    outdir = Path(outdir)
    manifest = json.loads((outdir / "run_manifest.json").read_text())
    config = manifest["config"]
    hourly = pd.read_csv(outdir / "hourly_dispatch.csv.gz")
    summary = pd.read_csv(outdir / "dispatch_summary.csv")
    financial = pd.read_csv(outdir / "finance_screen.csv")
    tolerance = 1e-4

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    numeric = ["load_mw", "forecast_mw", "availability", "charge_mw", "discharge_mw",
               "soc_start_mwh", "soc_end_mwh", "adjusted_load_proxy_mw"]
    require(np.isfinite(hourly[numeric].to_numpy()).all(), "Nonfinite hourly records")
    require(not hourly.duplicated(["duration_hours", "strategy", "timestamp_utc"]).any(),
            "Duplicate comparison intervals")
    expected = {(h, strategy) for h in config["durations_hours"]
                for strategy in ["lag7_dispatch", "hindsight_daily_bound"]}
    groups = hourly.groupby(["duration_hours", "strategy"])
    require(set(groups.groups) == expected, "Missing or unexpected comparison")
    require(set(zip(summary.duration_hours, summary.strategy)) == expected
            and len(summary) == len(expected), "Summary comparison mismatch")
    reference_times = None
    for (hours, strategy), group in groups:
        group = group.sort_values("timestamp_utc")
        times = tuple(group.timestamp_utc)
        if reference_times is None:
            reference_times = times
        require(times == reference_times, "Comparisons use different evaluation periods")
        parsed = pd.to_datetime(group.timestamp_utc, utc=True)
        require((parsed.diff().dropna() == pd.Timedelta(hours=1)).all(), "Interval gaps")
        require(len(group) == manifest["data_quality"]["input_rows"] - 168,
                "Evaluation row count mismatch")
        c, d = group.charge_mw.to_numpy(), group.discharge_mw.to_numpy()
        start, end = group.soc_start_mwh.to_numpy(), group.soc_end_mwh.to_numpy()
        power = config["power_mw"] * config["power_factor"] * group.availability.to_numpy()
        energy = config["power_mw"] * hours
        require((c >= -tolerance).all() and (d >= -tolerance).all(), "Negative dispatch")
        require((c <= power + tolerance).all() and (d <= power + tolerance).all(),
                "Dispatch exceeds available power")
        require((np.minimum(c, d) <= tolerance).all(), "Simultaneous charge/discharge")
        require((start >= -tolerance).all() and (end >= -tolerance).all()
                and (start <= energy + tolerance).all() and (end <= energy + tolerance).all(),
                "State of charge outside bounds")
        require(np.allclose(end - start, config["round_trip_efficiency"] * c - d,
                            atol=tolerance, rtol=0), "Energy is not conserved")
        require(np.allclose(start[1:], end[:-1], atol=tolerance, rtol=0),
                "Discontinuous state of charge")
        for _, day in group.groupby("local_date"):
            require(len(day) == 24 and list(day.hour_local) == list(range(24)),
                    "Incomplete local day")
            require(abs(day.soc_start_mwh.iloc[0] - energy * config["initial_soc_fraction"])
                    <= tolerance, "Incorrect initial state")
            require(abs(day.soc_end_mwh.iloc[-1] - day.soc_start_mwh.iloc[0]) <= tolerance,
                    "Daily schedule consumes free initial energy")
        proxy = group.load_mw.to_numpy() + c - d + config["auxiliary_mw"]
        require(np.allclose(proxy, group.adjusted_load_proxy_mw, atol=tolerance, rtol=0),
                "Load proxy does not reconcile")
        row = summary[(summary.duration_hours == hours) & (summary.strategy == strategy)].iloc[0]
        require(abs(group.load_mw.max() - proxy.max() - row.period_peak_reduction_proxy_mw)
                <= tolerance, "Period peak summary does not reconcile")
        require(abs(d.sum() - row.discharging_mwh) <= tolerance,
                "Discharge energy summary does not reconcile")

    require(set(financial.duration_hours) == set(config["durations_hours"])
            and len(financial) == len(config["durations_hours"]), "Finance duration mismatch")
    # Reconstruct discounted cash flow independently of lab.finance.
    years = np.arange(1, config["life_years"] + 1)
    discount = (1 + config["real_discount_rate"]) ** (-years.astype(float))
    for row in financial.itertuples():
        cash = np.full(len(years), row.required_fixed_fee_usd_per_kw_month
                       * config["power_mw"] * 1000 * 12 * config["paid_availability_fraction"]
                       - row.annual_fixed_om_usd)
        cash[config["augmentation_year"] - 1] -= row.augmentation_usd
        require(abs(-row.capex_usd + np.dot(cash, discount)) < 0.01,
                "Required fee does not break even under modeled cash flow")
    if manifest["data_mode"] == "synthetic-demo":
        require(sha256((outdir / "synthetic_input.csv").read_bytes()).hexdigest()
                == manifest["input_sha256"], "Synthetic input hash mismatch")
    if manifest.get("input_path"):
        source = Path(__file__).resolve().parent / manifest["input_path"]
        require(sha256(source.read_bytes()).hexdigest() == manifest["input_sha256"],
                "Measured input hash mismatch")
    return {"data_mode": manifest["data_mode"], "comparisons": len(expected),
            "hourly_records": len(hourly), "evaluated_days": len(reference_times) // 24,
            "physics_and_finance": "passed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outdir", type=Path)
    print(json.dumps(audit_results(parser.parse_args().outdir), indent=2))
