"""Reproduce the measured-data study from the included public EIA snapshots."""
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
from lab import ROOT, run
from verify_results import audit_results


def study_case(name, data_name, config):
    data = ROOT / "data" / "public" / data_name
    source = json.loads(data.with_suffix(".provenance.json").read_text())
    digest = sha256(data.read_bytes()).hexdigest()
    if digest != source["canonical_csv_sha256"]:
        raise ValueError("Public data snapshot hash differs from its provenance")
    out = ROOT / "results" / "measured" / name
    provenance = {"data_mode": "measured-eia-demand", "source_label":
                  f'EIA-930 AZPS {source["value_column"]}; {source["start_phoenix_inclusive"]} to {source["end_phoenix_exclusive"]}; revised snapshot',
                  "input_path": str(data.relative_to(ROOT)), "input_sha256": digest,
                  "provenance_path": str(data.with_suffix(".provenance.json").relative_to(ROOT)),
                  "source_quality": source["quality"], "case": name}
    run(pd.read_csv(data), config, out, provenance)
    return dict(case=name, **audit_results(out))


if __name__ == "__main__":
    base = json.loads((ROOT / "config.json").read_text())
    cases = []
    for year in [2024, 2025, 2026]:
        cases.append(study_case(str(year), f"azps_summer_{year}.csv", base))
    cases.append(study_case("2026_reported_raw", "azps_summer_2026_reported_raw.csv", base))
    cases.append(study_case("2026_derated", "azps_summer_2026.csv", dict(base, power_factor=0.9)))
    benchmark = json.loads((ROOT / "config_atb_performance.json").read_text())
    cases.append(study_case("2026_atb_performance", "azps_summer_2026.csv", benchmark))
    (ROOT / "results" / "measured" / "study_validation.json").write_text(json.dumps(cases, indent=2))
    print("All six measured-data cases passed independent export audits.")
