import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from lab import Battery, finance, forecast_day, solve_day, synthetic_data, validate_frame
from fetch_eia import fetch_pages, normalize_rows
from fetch_public_eia import normalize_public_rows
from verify_results import audit_results
import tempfile
from lab import run


class BatteryPhysicsTests(unittest.TestCase):
    def test_physics_and_recharge(self):
        load=np.array([500]*8+[600]*6+[1000]*6+[600]*4,dtype=float)
        b=Battery(100,4)
        c,d,s=solve_day(load,b)
        self.assertTrue(np.allclose(np.diff(s),b.rte*c-d,atol=1e-6))
        self.assertLessEqual(np.max(np.minimum(c,d)),1e-6)
        self.assertAlmostEqual(s[0],s[-1],places=6)
        self.assertGreater(c.sum(),d.sum())
        self.assertLess((load+c-d+b.auxiliary_mw).max(),load.max())

    def test_outage_disables_all_dispatch(self):
        c,d,s=solve_day(np.linspace(500,900,24),Battery(100,4),np.zeros(24))
        self.assertTrue(np.allclose(c,0));self.assertTrue(np.allclose(d,0))
        self.assertTrue(np.allclose(s,200))

    def test_no_free_flat_load_peak_benefit(self):
        load=np.ones(24)*500
        c,d,_=solve_day(load,Battery(100,4,auxiliary_mw=0))
        self.assertGreaterEqual((load+c-d).max(),500-1e-6)

    def test_heat_factor_limits_power(self):
        c,d,_=solve_day([500]*12+[1200]*4+[500]*8,Battery(100,4,power_factor=.7))
        self.assertLessEqual(max(c.max(),d.max()),70+1e-6)

    def test_duration_cannot_worsen_hindsight_objective(self):
        load=np.array([500]*8+[800]*10+[500]*6,dtype=float)
        peaks=[]
        for h in [4,6,8]:
            b=Battery(100,h,auxiliary_mw=0);c,d,_=solve_day(load,b)
            peaks.append((load+c-d).max())
        self.assertTrue(all(b<=a+1e-4 for a,b in zip(peaks,peaks[1:])))

    def test_invalid_physics_rejected(self):
        with self.assertRaises(ValueError): Battery(100,4,rte=1.1)
        with self.assertRaises(ValueError): solve_day([500]*24,Battery(100,4),[float('nan')]*24)


class DataAndFinanceTests(unittest.TestCase):
    def test_reject_gaps_duplicates_naive_dates(self):
        f=synthetic_data(9)
        with self.assertRaises(ValueError): validate_frame(f.drop(index=30))
        with self.assertRaises(ValueError): validate_frame(pd.concat([f,f.iloc[:1]]))
        naive=f.copy();naive.timestamp_utc=naive.timestamp_utc.str.replace('Z','',regex=False)
        with self.assertRaises(ValueError): validate_frame(naive)

    def test_forecast_no_target_day_lookahead(self):
        f=validate_frame(synthetic_data(10));a=forecast_day(f,192)
        f.loc[192:215,"load_mw"]=1e9
        self.assertTrue(np.array_equal(a,forecast_day(f,192)))

    def test_finance_break_even_and_upgrade_direction(self):
        c=json.loads((Path(__file__).parent/"config.json").read_text())
        base=finance(c,4)
        self.assertAlmostEqual(base["npv_at_required_fee_usd"],0,places=4)
        high=finance(dict(c,interconnection_usd=40e6),4)
        self.assertGreater(high["required_fixed_fee_usd_per_kw_month"],base["required_fixed_fee_usd_per_kw_month"])

    def test_eia_pagination_and_timestamps(self):
        calls=[]
        def mocked(params):
            calls.append(params["offset"])
            batch=[{"respondent":"AZPS","type":"D","period":"2025-06-01T08","value":"5000","value-units":"megawatthours"}]
            return {"response":{"total":"2","data":batch}}
        rows=fetch_pages("dummy", "start","end",request_json=mocked)
        self.assertEqual(calls,[0,1]);self.assertEqual(len(rows),2)
        f=normalize_rows(rows[:1])
        self.assertEqual(f.timestamp_utc.iloc[0],"2025-06-01T07:00:00Z")
        self.assertEqual(f.load_mw.iloc[0],5000)
        bad=dict(rows[0],respondent="SRP")
        with self.assertRaises(ValueError): normalize_rows([bad])

    def test_incomplete_pagination_fails(self):
        calls=[0]
        def mocked(params):
            calls[0]+=1
            return {"response":{"total":"2","data":[{}] if calls[0]==1 else []}}
        with self.assertRaises(RuntimeError): fetch_pages("dummy","start","end",request_json=mocked)

    def test_public_reported_demand_and_hour_ending(self):
        columns = ["BA", "UTC time", "Demand", "Adjusted demand", "Imputed demand"]
        endings = pd.date_range("2025-06-01T08:00:00", periods=192, freq="h")
        rows = [("AZPS", dt.to_pydatetime(), 5000, 5001, None) for dt in endings]
        frame, quality = normalize_public_rows(rows, columns, "2025-06-01", "2025-06-09")
        self.assertEqual(frame.timestamp_utc.iloc[0], "2025-06-01T07:00:00+00:00")
        self.assertTrue((frame.load_mw == 5000).all())
        self.assertEqual(quality["reported_vs_adjusted_differences"], 192)
        adjusted, _ = normalize_public_rows(rows, columns, "2025-06-01", "2025-06-09", "Adjusted demand")
        self.assertTrue((adjusted.load_mw == 5001).all())
        with self.assertRaises(ValueError):
            normalize_public_rows(rows[:-1], columns, "2025-06-01", "2025-06-09")
        rows[0] = ("AZPS", endings[0].to_pydatetime(), None, 5001, 5001)
        with self.assertRaises(ValueError):
            normalize_public_rows(rows, columns, "2025-06-01", "2025-06-09")

    def test_benchmark_om_and_invalid_finance(self):
        config = json.loads((Path(__file__).parent / "config.json").read_text())
        config.pop("annual_fixed_om_usd_per_kw")
        config.update(annual_fixed_om_fraction_of_capex=0.04,
                      augmentation_usd_per_usable_ac_kwh=0)
        row = finance(config, 4)
        self.assertAlmostEqual(row["annual_fixed_om_usd"], 0.04 * row["capex_usd"])
        self.assertAlmostEqual(row["npv_at_required_fee_usd"], 0, places=4)
        for change in [{"power_mw": 0}, {"life_years": 15.5},
                       {"annual_fixed_om_usd_per_kw": 20}]:
            with self.assertRaises(ValueError): finance(dict(config, **change), 4)

    def test_export_audit_detects_tampering(self):
        config = json.loads((Path(__file__).parent / "config.json").read_text())
        config["durations_hours"] = [4]
        with tempfile.TemporaryDirectory() as temp:
            run(synthetic_data(8), config, temp, {"data_mode": "test", "source_label": "test"})
            self.assertEqual(audit_results(temp)["hourly_records"], 48)
            path = Path(temp) / "hourly_dispatch.csv.gz"
            records = pd.read_csv(path)
            records.loc[0, "soc_end_mwh"] += 10
            records.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Energy is not conserved"):
                audit_results(temp)


if __name__=="__main__": unittest.main()
