import unittest

from smartbms.config import ControllerConfig, ProjectConfig
from smartbms.scenarios import run_portfolio_scenarios, run_scenario


class PortfolioScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = ProjectConfig()
        cls.bundle = run_portfolio_scenarios(cls.config)

    def test_bundle_contains_healthy_controls_and_four_faults(self):
        self.assertEqual(
            set(self.bundle.fault_runs),
            {
                "sensor_bias",
                "stuck_valve",
                "fouled_filter",
                "after_hours_operation",
            },
        )
        self.assertEqual(len(self.bundle.baseline.trends), self.config.simulation.steps)
        self.assertEqual(len(self.bundle.optimized.trends), self.config.simulation.steps)

    def test_every_fault_scenario_detects_its_expected_category(self):
        for category, run in self.bundle.fault_runs.items():
            with self.subTest(category=category):
                self.assertIn(category, {finding.category for finding in run.findings})
                self.assertGreater(run.trends.fault_active.sum(), 0)

    def test_healthy_scenarios_have_no_rcx_fault_findings(self):
        self.assertFalse(self.bundle.baseline.findings)
        self.assertFalse(self.bundle.optimized.findings)

    def test_optimized_control_saves_energy_with_acceptable_comfort(self):
        baseline = self.bundle.baseline.metrics
        optimized = self.bundle.optimized.metrics

        self.assertLess(optimized.energy_kwh, baseline.energy_kwh)
        self.assertGreaterEqual(optimized.occupied_comfort_pct, 95.0)
        self.assertLessEqual(
            optimized.occupied_discomfort_degree_hours,
            baseline.occupied_discomfort_degree_hours + 0.5,
        )

    def test_diagnostic_scorecard_has_full_recall_and_delay(self):
        scorecard = self.bundle.diagnostic_scorecard

        self.assertTrue(scorecard.detected.all())
        self.assertTrue((scorecard.detection_delay_minutes >= 45).all())
        self.assertTrue((scorecard.detection_delay_minutes <= 90).all())

    def test_trends_and_point_registry_are_explicitly_synthetic(self):
        self.assertTrue(self.bundle.baseline.trends.attrs["synthetic"])
        self.assertEqual(
            self.bundle.baseline.trends.attrs["seed"],
            self.config.simulation.seed,
        )
        self.assertIn("bacnet_object_type", self.bundle.point_registry.columns)
        self.assertTrue((self.bundle.point_registry["connection"] == "simulated").all())

    def test_pre_cooling_horizon_changes_when_authorization_begins(self):
        one_hour = run_scenario(
            ProjectConfig(controller=ControllerConfig(pre_cooling_hours=1)),
            name="one-hour",
            strategy="predictive",
        )
        two_hours = run_scenario(
            ProjectConfig(controller=ControllerConfig(pre_cooling_hours=2)),
            name="two-hours",
            strategy="predictive",
        )

        one_start = one_hour.trends.loc[
            one_hour.trends.preconditioning_authorized, "timestamp"
        ].min()
        two_start = two_hours.trends.loc[
            two_hours.trends.preconditioning_authorized, "timestamp"
        ].min()
        self.assertLess(two_start, one_start)


if __name__ == "__main__":
    unittest.main()
