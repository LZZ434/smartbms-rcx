import unittest
from datetime import datetime

from smartbms.config import (
    ControllerConfig,
    FaultConfig,
    PlantConfig,
    ProjectConfig,
    SimulationConfig,
    ZoneConfig,
)


class SimulationConfigTests(unittest.TestCase):
    def test_default_config_represents_seven_days_at_fifteen_minutes(self):
        config = SimulationConfig()

        self.assertEqual(config.steps, 7 * 24 * 4)
        self.assertEqual(config.dt_hours, 0.25)
        self.assertEqual(config.start, datetime(2026, 8, 3))

    def test_invalid_timestep_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timestep_minutes"):
            SimulationConfig(timestep_minutes=0)

    def test_timestep_must_evenly_divide_a_day(self):
        with self.assertRaisesRegex(ValueError, "divide"):
            SimulationConfig(timestep_minutes=17)


class EngineeringConfigTests(unittest.TestCase):
    def test_default_project_has_two_named_zones(self):
        config = ProjectConfig()

        self.assertEqual(config.plant.east.name, "East")
        self.assertEqual(config.plant.west.name, "West")
        self.assertLess(config.controller.comfort_min_c, config.controller.comfort_max_c)

    def test_zone_physics_must_be_positive(self):
        with self.assertRaises(ValueError):
            ZoneConfig(name="Bad", capacitance_kwh_per_c=0)

    def test_controller_setpoint_must_be_inside_comfort_band(self):
        with self.assertRaisesRegex(ValueError, "setpoint"):
            ControllerConfig(occupied_setpoint_c=30)

    def test_plant_cop_and_fault_multipliers_are_validated(self):
        with self.assertRaisesRegex(ValueError, "cop"):
            PlantConfig(chiller_cop=0)
        with self.assertRaisesRegex(ValueError, "multiplier"):
            FaultConfig(fouled_airflow_multiplier=1.2)


if __name__ == "__main__":
    unittest.main()
