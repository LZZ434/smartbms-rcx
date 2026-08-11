import importlib
import unittest


class DashboardSmokeTests(unittest.TestCase):
    def test_dashboard_module_imports_and_exposes_six_pages(self):
        module = importlib.import_module("app")

        self.assertTrue(callable(module.main))
        self.assertEqual(len(module.PAGE_NAMES), 6)
        self.assertIn("RCx Diagnostics", module.PAGE_NAMES)
        self.assertIn("Learning Lab", module.PAGE_NAMES)

        labels = module._hidden_fault_labels(
            ("sensor_bias", "stuck_valve", "fouled_filter", "after_hours_operation")
        )
        self.assertEqual(len(set(labels.values())), 4)
        self.assertFalse(any(category in labels[category] for category in labels))


if __name__ == "__main__":
    unittest.main()
