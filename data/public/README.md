# Public AZPS demand snapshots

Source: U.S. Energy Information Administration, EIA-930 public AZPS workbook:
https://www.eia.gov/electricity/gridmonitor/knownissues/xls/AZPS.xlsx

The source workbook was downloaded October 11, 2026 UTC / October 10 Phoenix.
Its raw SHA-256 hash is recorded in each `.provenance.json` file. The large original
workbook is linked rather than bundled. The extracts use `Published Hourly Data`.

Each input covers May 25–September 30 of the named year. May 25–31 is forecast
warmup; the evaluated days are June 1–September 30. Source hour-ending UTC labels
are shifted back one hour. Source one-hour MWh quantities become numeric average
MW in the canonical CSV. Grouping uses America/Phoenix.

The main snapshots consistently select **Adjusted demand**. The 2024 and 2025
values equal reported Demand throughout these windows. EIA adjusts one 2026
warmup hour: reported 20,345 MW becomes 2,309 MW at the May 27 08:00 Phoenix
hour beginning. The `2026_reported_raw` snapshot preserves reported Demand as a
separate sensitivity. Neither source column is silently substituted by the lab.

All three windows have 3,096 rows, full hourly coverage, no duplicate timestamps,
and no locally imputed observations. A complete window does not prove that every
reported value is accurate. EIA describes submitted data as preliminary, and the
history can be revised. These observations do not establish the historical as-of
information set for a forecast or exactly match APS retail demand.

To refresh a snapshot with the same value-column choice:

```bash
python fetch_public_eia.py --start 2026-05-25 --end 2026-10-01 --value-column "Adjusted demand" --out data/real/azps_summer_2026.csv
```

The optional authenticated API adapter retrieves reported `D`, which can differ
from this adjusted-workbook input. Compare definitions and quality flags before
mixing those routes. Provenance is part of the input, not optional documentation.
