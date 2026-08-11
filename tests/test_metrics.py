import unittest

import pandas as pd

from smartbms.config import TariffConfig
from smartbms.metrics import calculate_metrics, comparison_frame


def sample_trends() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hvac_power_kw": [4.0, 8.0, 0.0, 4.0],
            "east_temp_true_c": [24.0, 27.0, 24.0, 21.0],
            "west_temp_true_c": [25.0, 25.0, 24.0, 24.0],
            "occupied": [True, True, False, True],
        }
    )


class MetricTests(unittest.TestCase):
    def test_summary_matches_trend_energy_peak_and_runtime(self):
        summary = calculate_metrics(
            sample_trends(),
            timestep_minutes=15,
            tariff=TariffConfig(energy_hkd_per_kwh=1, demand_hkd_per_kw_week=0),
            scenario="sample",
        )

        self.assertAlmostEqual(summary.energy_kwh, 4.0)
        self.assertAlmostEqual(summary.peak_kw, 8.0)
        self.assertAlmostEqual(summary.runtime_hours, 0.75)
        self.assertAlmostEqual(summary.total_synthetic_cost_hkd, 4.0)

    def test_discomfort_is_counted_only_during_occupancy(self):
        summary = calculate_metrics(sample_trends(), scenario="sample")

        self.assertAlmostEqual(summary.occupied_discomfort_degree_hours, 0.50)
        self.assertLess(summary.occupied_comfort_pct, 100)

    def test_comparison_frame_reports_savings_direction(self):
        baseline = calculate_metrics(sample_trends(), scenario="baseline")
        optimized_frame = sample_trends().copy()
        optimized_frame["hvac_power_kw"] *= 0.8
        optimized = calculate_metrics(optimized_frame, scenario="optimized")

        frame = comparison_frame(baseline, optimized)

        savings = frame.loc[
            frame["scenario"] == "optimized", "energy_savings_pct"
        ].iloc[0]
        self.assertGreater(savings, 0)
        self.assertEqual(set(frame["scenario"]), {"baseline", "optimized"})

    def test_nan_power_is_rejected_instead_of_silently_undercounted(self):
        trends = sample_trends()
        trends.loc[1, "hvac_power_kw"] = float("nan")

        with self.assertRaisesRegex(ValueError, "non-finite"):
            calculate_metrics(trends, scenario="invalid")


if __name__ == "__main__":
    unittest.main()
