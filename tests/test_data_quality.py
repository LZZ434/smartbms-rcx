import unittest

import numpy as np
import pandas as pd

from smartbms.data_quality import assess_trend_quality
from smartbms.scenarios import run_portfolio_scenarios


class DataQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = run_portfolio_scenarios().baseline.trends.head(96)

    def test_healthy_baseline_scores_100_and_admits_all_rules(self):
        report = assess_trend_quality(self.baseline)

        self.assertEqual(report.score, 100.0)
        self.assertEqual(report.sampling_interval_minutes, 15.0)
        self.assertTrue(all(item.eligible for item in report.readiness))

    def test_assessment_does_not_mutate_source(self):
        source = self.baseline.copy(deep=True)
        original = source.copy(deep=True)

        assess_trend_quality(source)

        pd.testing.assert_frame_equal(source, original)

    def test_duplicate_unsorted_and_irregular_timestamps_are_critical(self):
        variants = {}
        duplicated = self.baseline.copy()
        duplicated.loc[1, "timestamp"] = duplicated.loc[0, "timestamp"]
        variants["timestamp_duplicate"] = duplicated
        variants["timestamp_unsorted"] = self.baseline.iloc[::-1]
        irregular = self.baseline.copy()
        irregular.loc[10:, "timestamp"] += pd.Timedelta(minutes=5)
        variants["timestamp_irregular"] = irregular

        for code, frame in variants.items():
            with self.subTest(code=code):
                report = assess_trend_quality(frame)
                self.assertIn(code, {issue.code for issue in report.issues})
                self.assertFalse(any(item.eligible for item in report.readiness))

    def test_missing_columns_block_only_affected_rules(self):
        frame = self.baseline.drop(
            columns=["east_temp_reference_c", "airflow_east"]
        )

        report = assess_trend_quality(frame)
        readiness = {item.category: item for item in report.readiness}

        self.assertFalse(readiness["sensor_bias"].eligible)
        self.assertFalse(readiness["fouled_filter"].eligible)
        self.assertTrue(readiness["stuck_valve"].eligible)
        self.assertTrue(readiness["after_hours_operation"].eligible)

    def test_missing_frozen_out_of_range_and_rate_issues_are_detected(self):
        variants = {}
        missing = self.baseline.copy()
        missing.loc[10:20, "east_temp_measured_c"] = np.nan
        variants["missing_values"] = missing
        frozen = self.baseline.copy()
        frozen.loc[10:25, "east_temp_measured_c"] = 24.0
        variants["frozen_signal"] = frozen
        bounded = self.baseline.copy()
        bounded.loc[10, "cooling_cmd_east"] = 1.5
        variants["engineering_bounds"] = bounded
        rate = self.baseline.copy()
        rate.loc[10, "east_temp_measured_c"] += 5.0
        variants["temperature_rate"] = rate

        for code, frame in variants.items():
            with self.subTest(code=code):
                report = assess_trend_quality(frame)
                self.assertIn(code, {issue.code for issue in report.issues})
                self.assertLess(report.score, 100.0)

    def test_too_short_history_and_cross_point_failure_are_critical(self):
        short = assess_trend_quality(self.baseline.head(8))
        inconsistent_frame = self.baseline.copy()
        inconsistent_frame.loc[10, "hvac_power_kw"] = 0.0
        inconsistent_frame.loc[10, "fan_power_kw"] = 2.0
        inconsistent = assess_trend_quality(inconsistent_frame)

        self.assertIn("history_too_short", {item.code for item in short.issues})
        self.assertFalse(any(item.eligible for item in short.readiness))
        self.assertIn(
            "cross_point_power",
            {item.code for item in inconsistent.issues},
        )


if __name__ == "__main__":
    unittest.main()
