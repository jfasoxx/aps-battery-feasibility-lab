"""Fetch EIA-930 AZPS hourly demand to the lab's explicit CSV contract.

Requires the user's own EIA_API_KEY. Network adapter is covered by mocked tests;
no authenticated live download was performed when this prototype was authored.
Never writes the key or authenticated request URL to outputs.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd
from lab import validate_frame

ENDPOINT="https://api.eia.gov/v2/electricity/rto/region-data/data/"


def fetch_pages(api_key,start_utc,end_utc,request_json=None):
    def live_request(params):
        url=ENDPOINT+"?"+urlencode(params)
        for attempt in range(3):
            try:
                with urlopen(url,timeout=30) as r:
                    return json.load(r)
            except Exception:
                if attempt==2:
                    raise RuntimeError("EIA request failed; check connectivity, key, API limits, and route metadata.") from None
                time.sleep(2**attempt)
    request_json=request_json or live_request
    rows=[];offset=0;expected_total=None
    while True:
        params={"api_key":api_key,"frequency":"hourly","data[0]":"value",
                "facets[respondent][0]":"AZPS","facets[type][0]":"D",
                "start":start_utc,"end":end_utc,"sort[0][column]":"period",
                "sort[0][direction]":"asc","offset":offset,"length":5000}
        payload=request_json(params)
        response=payload.get("response",{})
        if "data" not in response or "total" not in response:
            raise RuntimeError("EIA response lacks data/total. No partial file written.")
        total=int(response["total"])
        if expected_total is not None and total != expected_total:
            raise RuntimeError("EIA result count changed during pagination; rerun on a stable historical window.")
        expected_total=total
        batch=response["data"]
        if not isinstance(batch,list): raise RuntimeError("EIA returned an invalid data page.")
        rows.extend(batch)
        offset+=len(batch)
        if offset>=total: break
        if not batch: raise RuntimeError("EIA pagination ended before all rows were received.")
    if not rows or len(rows)!=expected_total:
        raise RuntimeError("EIA returned no data or inconsistent pagination.")
    return rows


def normalize_rows(rows):
    output=[]
    for row in rows:
        if row.get("respondent") != "AZPS" or row.get("type") != "D":
            raise ValueError("Unexpected balancing authority or series type.")
        unit=str(row.get("value-units","")).lower()
        if unit not in {"megawatthours","megawatts","mwh","mw"}:
            raise ValueError("Unknown EIA units; inspect metadata before interpreting demand.")
        # EIA-930 uses hour-ending UTC; canonical model labels hour beginning.
        start=pd.to_datetime(row["period"],utc=True)-pd.Timedelta(hours=1)
        # Hourly MWh / 1 hour = hourly average MW; MW is already the average.
        output.append({"timestamp_utc":start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "load_mw":float(row["value"]),"availability":1.0})
    return pd.DataFrame(output)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start",required=True,help="First Phoenix-local date, inclusive: YYYY-MM-DD")
    p.add_argument("--end",required=True,help="Phoenix-local date, exclusive: YYYY-MM-DD")
    p.add_argument("--out",type=Path,default=Path("data/real/azps_hourly.csv"))
    args=p.parse_args()
    key=os.environ.get("EIA_API_KEY")
    if not key: p.error("Set EIA_API_KEY in your environment; do not put keys in source files.")
    start=pd.Timestamp(args.start,tz="America/Phoenix").tz_convert("UTC")
    end=pd.Timestamp(args.end,tz="America/Phoenix").tz_convert("UTC")
    if start>=end or start.hour != 7 or end.hour != 7:
        p.error("Use midnight Phoenix-local dates with end after start.")
    rows=fetch_pages(key,(start+pd.Timedelta(hours=1)).strftime("%Y-%m-%dT%H"),end.strftime("%Y-%m-%dT%H"))
    frame=normalize_rows(rows)
    # Reject gaps, invalid units, duplicates and missing demand; don't fabricate repairs.
    validated=validate_frame(frame)
    stamps=validated.timestamp_utc
    if stamps.iloc[0]!=start or stamps.iloc[-1]!=end-pd.Timedelta(hours=1) or len(frame)!=(end-start)/pd.Timedelta(hours=1):
        raise ValueError("Downloaded coverage differs from the exact requested local-date window.")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    frame.sort_values("timestamp_utc").to_csv(args.out,index=False)
    manifest={"source":"EIA API v2 /electricity/rto/region-data/data/", "respondent":"AZPS","type":"D",
        "start_local_inclusive":args.start,"end_local_exclusive":args.end,"rows":len(frame),
        "downloaded_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),
        "normalization":"Hour-ending UTC converted to hour-start UTC; hourly MWh divided by 1 hour where applicable.",
        "sha256":sha256(args.out.read_bytes()).hexdigest(),
        "caveat":"Latest revised data; no historical as-of vintages. Availability=1 is an assumption."}
    args.out.with_suffix(".provenance.json").write_text(json.dumps(manifest,indent=2))
    print(f"Saved {len(frame)} AZPS hourly rows to {args.out}; no silent imputation.")


if __name__=="__main__": main()
