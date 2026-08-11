import unittest
from datetime import datetime

from smartbms.points import build_point_registry, evaluate_alarms


class PointRegistryTests(unittest.TestCase):
    def test_registry_has_protocol_metadata(self):
        points = build_point_registry()
        zone_temp = next(point for point in points if point.point_id == "ZN-E-T")

        self.assertEqual(zone_temp.bacnet_object_type, "analog-input")
        self.assertIsNotNone(zone_temp.modbus_register)
        self.assertEqual(zone_temp.unit, "°C")

    def test_point_ids_and_protocol_addresses_are_unique(self):
        points = build_point_registry()

        self.assertEqual(len({point.point_id for point in points}), len(points))
        self.assertEqual(
            len({point.bacnet_instance for point in points}), len(points)
        )
        self.assertEqual(
            len({point.modbus_register for point in points}), len(points)
        )

    def test_alarm_evaluation_reports_high_temperature_and_after_hours(self):
        alarms = evaluate_alarms(
            {
                "east_temp_measured_c": 29.2,
                "west_temp_measured_c": 24.5,
                "occupied": False,
                "hvac_power_kw": 5.0,
                "cooling_cmd_east": 0.7,
                "valve_east": 0.7,
                "airflow_cmd_east": 0.8,
                "airflow_east": 0.8,
            },
            datetime(2026, 8, 7, 22),
        )

        messages = " ".join(alarm.message for alarm in alarms).lower()
        self.assertIn("temperature", messages)
        self.assertIn("unoccupied", messages)


if __name__ == "__main__":
    unittest.main()
