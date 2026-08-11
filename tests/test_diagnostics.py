import unittest

import numpy as np
import pandas as pd

from smartbms.diagnostics import findings_to_frame, run_diagnostics


def diagnostic_fixture(category: str) -> pd.DataFrame:
    rows = 16
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-07 20:00", periods=rows, freq="15min"),
            "east_temp_measured_c": np.full(rows, 25.0),
            "east_temp_reference_c": np.full(rows, 25.0),
            "cooling_cmd_east": np.full(rows, 0.65),
            "valve_east": np.full(rows, 0.65),
            "airflow_cmd_east": np.full(rows, 0.75),
            "airflow_east": np.full(rows, 0.75),
            "fan_power_kw": np.full(rows, 2.5),
            "expected_fan_power_kw": np.full(rows, 2.5),
            "hvac_power_kw": np.full(rows, 5.0),
            "occupied": np.full(rows, True),
        }
    )
    if category == "sensor_bias":
        frame["east_temp_measured_c"] = 27.2
    elif category == "stuck_valve":
        frame["valve_east"] = 0.10
    elif category == "fouled_filter":
        frame["airflow_east"] = 0.35
        frame["fan_power_kw"] = 3.8
    elif category == "after_hours_operation":
        frame["occupied"] = False
    return frame


class DiagnosticRuleTests(unittest.TestCase):
    def test_each_fault_rule_returns_actionable_finding(self):
        categories = {
            "sensor_bias",
            "stuck_valve",
            "fouled_filter",
            "after_hours_operation",
        }

        for category in categories:
            with self.subTest(category=category):
                findings = run_diagnostics(diagnostic_fixture(category))
                finding = next(item for item in findings if item.category == category)
                self.assertTrue(finding.recommendation)
                self.assertTrue(finding.evidence_columns)
                self.assertGreaterEqual(finding.estimated_waste_kwh, 0)

    def test_after_hours_finding_mentions_schedule_and_waste(self):
        findings = run_diagnostics(diagnostic_fixture("after_hours_operation"))
        finding = next(
            item for item in findings if item.category == "after_hours_operation"
        )

        self.assertIn("schedule", finding.recommendation.lower())
        self.assertGreater(finding.estimated_waste_kwh, 0)

    def test_healthy_fixture_has_no_findings(self):
        self.assertEqual(run_diagnostics(diagnostic_fixture("healthy")), [])

    def test_findings_convert_to_stable_frame_schema(self):
        frame = findings_to_frame(
            run_diagnostics(diagnostic_fixture("sensor_bias"))
        )

        self.assertIn("category", frame.columns)
        self.assertIn("detected_at", frame.columns)
        self.assertIn("recommendation", frame.columns)

    def test_stuck_valve_impact_uses_configured_nominal_capacity(self):
        trends = diagnostic_fixture("stuck_valve")
        low = next(
            finding
            for finding in run_diagnostics(
                trends, nominal_zone_cooling_kw=12
            )
            if finding.category == "stuck_valve"
        )
        high = next(
            finding
            for finding in run_diagnostics(
                trends, nominal_zone_cooling_kw=24
            )
            if finding.category == "stuck_valve"
        )

        self.assertAlmostEqual(
            high.estimated_waste_kwh,
            low.estimated_waste_kwh * 2,
            delta=0.002,
        )


if __name__ == "__main__":
    unittest.main()
