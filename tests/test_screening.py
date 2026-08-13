import unittest

from smartbms.data_quality_reporting import (
    checks_frame,
    issues_frame,
    quality_report_frame,
    readiness_frame,
)
from smartbms.scenarios import run_portfolio_scenarios
from smartbms.screening import screen_trends


class ScreeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = run_portfolio_scenarios()

    def test_healthy_sample_is_eligible_and_has_no_screening_findings(self):
        result = screen_trends(self.bundle.baseline.trends)

        self.assertEqual(result.findings, ())
        self.assertTrue(all(item.eligible for item in result.quality.readiness))

    def test_fault_sample_returns_only_admitted_finding(self):
        frame = self.bundle.fault_runs["stuck_valve"].trends.drop(
            columns=["east_temp_reference_c"]
        )

        result = screen_trends(frame)

        self.assertEqual(
            [item.category for item in result.findings],
            ["stuck_valve"],
        )
        readiness = {item.category: item for item in result.quality.readiness}
        self.assertFalse(readiness["sensor_bias"].eligible)

    def test_critical_timestamp_issue_blocks_all_diagnostics(self):
        frame = self.bundle.fault_runs["stuck_valve"].trends.iloc[::-1]

        result = screen_trends(frame)

        self.assertEqual(result.findings, ())
        self.assertFalse(any(item.eligible for item in result.quality.readiness))

    def test_unknown_preconditioning_state_blocks_after_hours_rule(self):
        for frame in (
            self.bundle.baseline.trends.drop(
                columns=["preconditioning_authorized"]
            ),
            self.bundle.baseline.trends.assign(
                preconditioning_authorized=lambda value: value[
                    "preconditioning_authorized"
                ].mask(value.index == 0)
            ),
        ):
            with self.subTest(columns=tuple(frame.columns)):
                result = screen_trends(frame)
                readiness = {
                    item.category: item for item in result.quality.readiness
                }

                self.assertFalse(readiness["after_hours_operation"].eligible)
                self.assertNotIn(
                    "after_hours_operation",
                    {item.category for item in result.findings},
                )

    def test_export_frames_keep_stable_english_schema(self):
        result = screen_trends(self.bundle.baseline.trends)

        self.assertEqual(
            list(checks_frame(result.quality).columns),
            ["check_code", "status", "weight", "issue_count"],
        )
        self.assertEqual(
            list(issues_frame(result.quality).columns),
            ["issue_code", "severity", "columns", "affected_rows", "detail"],
        )
        self.assertEqual(
            list(quality_report_frame(result.quality).columns),
            [
                "check_code",
                "status",
                "weight",
                "issue_code",
                "severity",
                "columns",
                "affected_rows",
                "detail",
            ],
        )
        self.assertEqual(
            list(readiness_frame(result.quality).columns),
            [
                "category",
                "eligible",
                "required_columns",
                "missing_columns",
                "blocking_issue_codes",
            ],
        )

    def test_export_adapters_return_independent_frames(self):
        result = screen_trends(self.bundle.baseline.trends)
        first = quality_report_frame(result.quality)
        first.loc[0, "status"] = "changed"

        second = quality_report_frame(result.quality)

        self.assertNotEqual(second.loc[0, "status"], "changed")


if __name__ == "__main__":
    unittest.main()
