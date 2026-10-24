#!/usr/bin/env python3
"""Focused checks for the audit's concrete classification and time-boundary risks."""
import tempfile
import unittest
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

import audit_monitoring as audit

HOURLY_DIR = audit.REPO / "data/interim/03A04_multiyear"

class AuditChecks(unittest.TestCase):
    def test_exact_labels_keep_mixed_separate(self):
        values = ["Measured", " Measured and Substitute ", "Substitute", "Calculated", None, "Unmeasured"]
        self.assertEqual([audit.indicator_category(v) for v in values],
                         ["measured_only", "mixed_measured_substitute", "substitute_only", "calculated", "missing", "other"])

    def test_end_hour_inclusive_and_adjacent_transition(self):
        records = []
        for begin, bh, end, eh in [("2024-09-18", 0, "2024-09-18", 9), ("2024-09-18", 10, None, None)]:
            start, stop, status, note = audit.interval({"beginDate": begin, "beginHour": bh, "endDate": end, "endHour": eh})
            records.append({"begin": start, "end": stop, "interval_status": status})
        times = pd.Series(pd.date_range("2024-09-18 08:00", periods=4, freq="h"))
        first = audit.mask_for_intervals(times, records[:1])
        second = audit.mask_for_intervals(times, records[1:])
        self.assertEqual(first.tolist(), [True, True, False, False])
        self.assertEqual(second.tolist(), [False, False, True, True])
        self.assertFalse((first & second).any())
        self.assertTrue((first | second).all())

    def test_leap_calendar_gap_duplicate_and_input_preservation(self):
        ts = pd.date_range("2012-01-01", "2012-12-31 23:00", freq="h")
        frame = pd.DataFrame({
            "Facility ID": 6065, "Unit ID": "2", "Date": ts.normalize(), "Hour": ts.hour,
            "Operating Time": 1.0, "Gross Load (MW)": 500.0, "CO2 Mass (short tons)": 500.0,
            "CO2 Mass Measure Indicator": "Measured",
        })
        # Remove the leap-day hour and duplicate a different hour, so row count
        # alone cannot conceal the missing calendar record.
        frame = frame.drop(index=1416)
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "iatan_unit2_2012.parquet"
            frame.to_parquet(path, index=False)
            _, summary, gaps, manifest = audit.load_year(path, 2012, "6065", "2")
            self.assertEqual(summary["expected_calendar_hours"], 8784)
            self.assertEqual(summary["calendar_gap_hours"], 1)
            self.assertEqual(summary["duplicate_extra_rows"], 1)
            self.assertEqual(sum(g["n_hours"] for g in gaps), 1)
            self.assertEqual(manifest["sha256_before"], manifest["sha256_after"])

    def test_preserved_original_xml_and_current_json_agree(self):
        xml_rows, _ = audit.flatten_plan(audit.BASE / "sources/original_plan_unit2.xml", "6065", "2")
        json_rows, _ = audit.flatten_plan(audit.BASE / "sources/current_plan_unit2.json", "6065", "2")
        comparison = audit.snapshot_comparison(xml_rows + json_rows, ["original_plan_unit2", "current_plan_unit2"])[0]
        self.assertEqual(comparison["common_rows"], 24)
        self.assertTrue(comparison["equivalent_on_compared_fields"])
        self.assertTrue(any(r.get("parameterCode") == "CO2" and r.get("monitoringMethodCode") == "CEM" for r in xml_rows))

    def test_2025_original_indicator_counts(self):
        path = HOURLY_DIR / "iatan_unit2_2025.parquet"
        _, summary, _, _ = audit.load_year(path, 2025, "6065", "2")
        self.assertEqual(summary["n_on"], 6249)
        self.assertEqual(summary["n_measured_only_on"], 6209)
        self.assertEqual(summary["n_mixed_measured_substitute_on"], 40)
        self.assertEqual(summary["n_substitute_only_on"], 0)
        self.assertEqual(summary["n_missing_on"], 0)
        self.assertEqual(summary["n_legacy_contains_measured_on"], 6249)

    def test_public_json_extracts_omit_administrative_identifiers(self):
        forbidden = {"userid", "email", "phone", "contact", "monitoringplancomment", "monitoringplancommentdata"}
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(audit.norm_key(key), forbidden)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        for path in (audit.BASE / "sources").glob("*.json"):
            walk(json.loads(path.read_text()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--hourly-dir", type=Path, default=HOURLY_DIR)
    args, rest = parser.parse_known_args()
    HOURLY_DIR = args.hourly_dir.resolve()
    unittest.main(argv=[sys.argv[0]] + rest, verbosity=2)
