import unittest

from smartbms.config import ControllerConfig
from smartbms.controllers import BaselineController, ZoneObservation


class BaselineControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = BaselineController(ControllerConfig())

    def test_actions_respect_normalized_bounds(self):
        action = self.controller.act(ZoneObservation(35, 33, True, 36, 14))

        for value in (
            action.cooling_east,
            action.cooling_west,
            action.airflow_east,
            action.airflow_west,
        ):
            self.assertTrue(0 <= value <= 1)

    def test_hot_occupied_zone_receives_more_cooling(self):
        action = self.controller.act(ZoneObservation(27, 24, True, 31, 10))

        self.assertGreater(action.cooling_east, action.cooling_west)
        self.assertEqual(action.target_east_c, 24.0)

    def test_unoccupied_setback_reduces_airflow_and_cooling(self):
        occupied = self.controller.act(ZoneObservation(27, 27, True, 31, 10))
        unoccupied = self.controller.act(ZoneObservation(27, 27, False, 31, 22))

        self.assertLess(unoccupied.cooling_east, occupied.cooling_east)
        self.assertLess(unoccupied.airflow_east, occupied.airflow_east)


if __name__ == "__main__":
    unittest.main()
