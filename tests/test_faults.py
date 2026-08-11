import unittest
from datetime import datetime

from smartbms.config import FaultConfig
from smartbms.faults import FaultType, apply_fault, fault_is_active


class FaultInjectionTests(unittest.TestCase):
    def test_sensor_bias_changes_measured_not_true_temperature(self):
        result = apply_fault(
            FaultType.SENSOR_BIAS,
            true_temp_c=24,
            command=0.5,
            airflow=0.7,
            power_kw=3,
        )

        self.assertEqual(result.true_temp_c, 24)
        self.assertGreater(result.measured_temp_c, 24)
        self.assertEqual(result.actual_valve_position, 0.5)

    def test_stuck_valve_and_fouled_filter_change_physical_response(self):
        stuck = apply_fault(
            FaultType.STUCK_VALVE, 26, 0.9, 0.8, 4, config=FaultConfig()
        )
        fouled = apply_fault(
            FaultType.FOULED_FILTER, 26, 0.7, 0.8, 4, config=FaultConfig()
        )

        self.assertLess(stuck.actual_valve_position, stuck.command)
        self.assertLess(fouled.actual_airflow, fouled.commanded_airflow)
        self.assertGreater(fouled.fan_power_multiplier, 1)

    def test_after_hours_fault_overrides_command(self):
        result = apply_fault(FaultType.AFTER_HOURS, 27, 0.0, 0.08, 0.1)

        self.assertGreater(result.command, 0.5)
        self.assertGreater(result.commanded_airflow, 0.5)

    def test_fault_windows_are_explicit_and_deterministic(self):
        self.assertTrue(
            fault_is_active(FaultType.SENSOR_BIAS, datetime(2026, 8, 4, 12))
        )
        self.assertFalse(
            fault_is_active(FaultType.SENSOR_BIAS, datetime(2026, 8, 4, 18))
        )


if __name__ == "__main__":
    unittest.main()
