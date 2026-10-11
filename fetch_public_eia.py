"""Refresh key-free AZPS demand from EIA's public balancing-authority workbook.

The value column is explicit: reported Demand or EIA Adjusted demand. EIA may
revise this history. A snapshot does not establish the historical as-of vintage.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import urllib.request

import openpyxl
import pandas as pd
from lab import validate_frame

SOURCE_URL = "https://www.eia.gov/electricity/gridmonitor/knownissues/xls/AZPS.xlsx"


def normalize_public_rows(rows, columns, start, end, value_column="Demand"):
    if value_column not in ["Demand", "Adjusted demand"]:
        raise ValueError("Choose Demand or Adjusted demand explicitly")
    indices = {k: columns.index(k) for k in ["BA", "UTC time", "Demand", "Adjusted demand", "Imputed demand"]}
    first = pd.Timestamp(start, tz="America/Phoenix").tz_convert("UTC")
    last = pd.Timestamp(end, tz="America/Phoenix").tz_convert("UTC")
    records = []
    adjusted_count = imputed_count = 0
    for row in rows:
        ending = row[indices["UTC time"]]
        if ending is None:
            continue
        beginning = pd.Timestamp(ending, tz="UTC") - pd.Timedelta(hours=1)
        if first <= beginning < last:
            if row[indices["BA"]] != "AZPS":
                raise ValueError("Unexpected balancing authority in requested period")
            demand = row[indices[value_column]]
            adjusted_count += int(row[indices["Demand"]] != row[indices["Adjusted demand"]])
            imputed_count += int(row[indices["Imputed demand"]] is not None)
            records.append({"timestamp_utc": beginning.isoformat(), "load_mw": demand})
    frame = pd.DataFrame(records)
    validated = validate_frame(frame)
    expected = pd.date_range(first, last, freq="h", inclusive="left")
    if not validated.timestamp_utc.reset_index(drop=True).equals(pd.Series(expected)):
        raise ValueError("Requested period is not fully covered")
    return frame, {"rows": len(frame), "missing_rows": 0, "filled_rows": 0,
                   "reported_vs_adjusted_differences": adjusted_count,
                   "source_imputed_demand_cells": imputed_count}


def extract_workbook(workbook_path, start, end, out, value_column="Demand"):
    workbook_path, out = Path(workbook_path), Path(out)
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        iterator = workbook["Published Hourly Data"].iter_rows(values_only=True)
        columns = list(next(iterator))
        frame, checks = normalize_public_rows(iterator, columns, start, end, value_column)
    finally:
        workbook.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    provenance = {"source_url": SOURCE_URL, "publisher": "U.S. Energy Information Administration",
                  "balancing_authority": "AZPS", "sheet": "Published Hourly Data",
                  "value_column": value_column, "units": "MWh per one-hour interval; numeric average MW",
                  "timestamp_conversion": "UTC time is hour-ending; subtract one hour for hour-start",
                  "start_phoenix_inclusive": start, "end_phoenix_exclusive": end,
                  "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
                  "raw_workbook_sha256": sha256(workbook_path.read_bytes()).hexdigest(),
                  "canonical_csv_sha256": sha256(out.read_bytes()).hexdigest(),
                  "quality": checks, "revision_warning": "Revised published history, not an as-of operational replay"}
    out.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2))
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="Inclusive Phoenix-local date")
    parser.add_argument("--end", required=True, help="Exclusive Phoenix-local date")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workbook", type=Path, help="Reuse an already-downloaded public AZPS workbook")
    parser.add_argument("--value-column", choices=["Demand", "Adjusted demand"], default="Demand")
    args = parser.parse_args()
    if args.workbook:
        result = extract_workbook(args.workbook, args.start, args.end, args.out, args.value_column)
    else:
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "AZPS.xlsx"
            request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "APS-Battery-Research/0.2"})
            with urllib.request.urlopen(request, timeout=120) as response, raw.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            result = extract_workbook(raw, args.start, args.end, args.out, args.value_column)
    print(json.dumps(result, indent=2))
