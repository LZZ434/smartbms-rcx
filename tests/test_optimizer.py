import math
import unittest

from smartbms.config import ControllerConfig, PlantConfig, ZoneConfig
from smartbms.controllers import PredictiveController, ZoneObservation


class PredictiveControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = PredictiveController(ControllerConfig())

    def test_controller_uses_pre_cooling_before_occupancy(self):
        action = self.controller.act(
            ZoneObservation(27, 27, False, 31, 8),
            occupancy_next_hour=0.9,
            outdoor_temp_next_hour_c=32,
        )

        self.assertGreater(action.cooling_east, 0)
        self.assertLess(action.target_east_c, 28)
        self.assertFalse(action.fallback_used)

    def test_optimizer_actions_stay_bounded(self):
        action = self.controller.act(
            ZoneObservation(35, 34, True, 36, 14),
            occupancy_next_hour=1,
        )

        self.assertTrue(0 <= action.cooling_west <= 1)
        self.assertTrue(0 <= action.airflow_west <= 1)
        self.assertEqual(action.strategy, "predictive")

    def test_invalid_observation_uses_safe_baseline_fallback(self):
        action = self.controller.act(
            ZoneObservation(math.nan, 27, True, 31, 14),
            occupancy_next_hour=1,
        )

        self.assertTrue(action.fallback_used)
        self.assertEqual(action.strategy, "predictive-fallback")
        self.assertTrue(0 <= action.cooling_east <= 1)

    def test_projected_power_uses_configured_plant_capacity(self):
        observation = ZoneObservation(27, 27, True, 31, 14)
        default = PredictiveController(
            ControllerConfig(), PlantConfig()
        ).act(observation, occupancy_next_hour=1)
        low_capacity = PredictiveController(
            ControllerConfig(),
            PlantConfig(
                east=ZoneConfig(name="East", max_cooling_kw=12),
                west=ZoneConfig(name="West", max_cooling_kw=12),
            ),
        ).act(observation, occupancy_next_hour=1)

        self.assertNotEqual(default.projected_power_kw, low_capacity.projected_power_kw)


if __name__ == "__main__":
    unittest.main()
