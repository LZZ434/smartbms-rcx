import unittest

from smartbms.config import ProjectConfig
from smartbms.plant import TwoZonePlant


class TwoZonePlantTests(unittest.TestCase):
    def setUp(self):
        self.config = ProjectConfig()

    def test_cooling_command_lowers_next_zone_temperature(self):
        free_plant = TwoZonePlant(self.config)
        cooled_plant = TwoZonePlant(self.config)

        free = free_plant.step(
            outdoor_temp_c=31,
            internal_gains_kw=(7, 7),
            solar_gains_kw=(2, 2),
            cooling_commands=(0, 0),
            airflow_commands=(0.3, 0.3),
        )
        cooled = cooled_plant.step(
            outdoor_temp_c=31,
            internal_gains_kw=(7, 7),
            solar_gains_kw=(2, 2),
            cooling_commands=(1, 1),
            airflow_commands=(1, 1),
        )

        self.assertLess(cooled.east_temp_c, free.east_temp_c)
        self.assertLess(cooled.west_temp_c, free.west_temp_c)
        self.assertGreater(cooled.chiller_power_kw, 0)

    def test_snapshot_exposes_explainable_energy_balance(self):
        snapshot = TwoZonePlant(self.config).step(
            outdoor_temp_c=30,
            internal_gains_kw=(5, 6),
            solar_gains_kw=(1, 2),
            cooling_commands=(0.5, 0.7),
            airflow_commands=(0.6, 0.8),
        )

        self.assertAlmostEqual(
            snapshot.hvac_power_kw,
            snapshot.chiller_power_kw + snapshot.fan_power_kw,
        )
        self.assertTrue(0 <= snapshot.airflow_east <= 1)
        self.assertTrue(0 <= snapshot.valve_west <= 1)

    def test_fan_power_follows_cubic_law(self):
        low = TwoZonePlant(self.config).step(
            30, (0, 0), (0, 0), (0, 0), (0.3, 0.3)
        )
        high = TwoZonePlant(self.config).step(
            30, (0, 0), (0, 0), (0, 0), (0.9, 0.9)
        )

        self.assertGreater(high.fan_power_kw, low.fan_power_kw * 5)

    def test_external_fault_effects_can_change_actual_equipment(self):
        snapshot = TwoZonePlant(self.config).step(
            outdoor_temp_c=31,
            internal_gains_kw=(7, 7),
            solar_gains_kw=(2, 2),
            cooling_commands=(1, 1),
            airflow_commands=(1, 1),
            actual_valve_positions=(0.15, 1.0),
            airflow_multipliers=(0.5, 1.0),
            fan_power_multiplier=1.4,
        )

        self.assertAlmostEqual(snapshot.valve_east, 0.15)
        self.assertAlmostEqual(snapshot.airflow_east, 0.5)
        self.assertGreater(snapshot.cooling_west_kw, snapshot.cooling_east_kw)


if __name__ == "__main__":
    unittest.main()
