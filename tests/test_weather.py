import unittest

from smartbms.config import SimulationConfig
from smartbms.weather import HKO_AUGUST_NORMALS, generate_inputs


class WeatherProfileTests(unittest.TestCase):
    def setUp(self):
        self.config = SimulationConfig()
        self.frame = generate_inputs(self.config)

    def test_profile_has_expected_schema_and_length(self):
        required = {
            "timestamp",
            "outdoor_temp_c",
            "humidity_pct",
            "solar_w_m2",
            "occupancy_east",
            "occupancy_west",
            "internal_gain_east_kw",
            "internal_gain_west_kw",
            "solar_gain_east_kw",
            "solar_gain_west_kw",
        }

        self.assertEqual(len(self.frame), self.config.steps)
        self.assertTrue(required.issubset(self.frame.columns))

    def test_generation_is_deterministic(self):
        second = generate_inputs(self.config)

        self.assertTrue(self.frame.equals(second))

    def test_occupied_weekday_profile_is_higher_than_night(self):
        weekday = self.frame.timestamp.dt.dayofweek < 5
        occupied = self.frame[
            weekday
            & (self.frame.timestamp.dt.hour >= 9)
            & (self.frame.timestamp.dt.hour < 18)
        ]
        night = self.frame[self.frame.timestamp.dt.hour < 5]

        self.assertGreater(occupied.occupancy_east.mean(), 0.6)
        self.assertLess(night.occupancy_east.mean(), 0.05)

    def test_weather_is_plausible_and_disclosed_as_synthetic(self):
        self.assertTrue(self.frame.outdoor_temp_c.between(24, 34).all())
        self.assertTrue(self.frame.humidity_pct.between(60, 98).all())
        self.assertGreater(self.frame.solar_w_m2.max(), 400)
        self.assertTrue(self.frame.attrs["synthetic"])
        self.assertIn("Hong Kong Observatory", self.frame.attrs["weather_reference"])
        self.assertAlmostEqual(HKO_AUGUST_NORMALS["mean_temp_c"], 28.7)


if __name__ == "__main__":
    unittest.main()
