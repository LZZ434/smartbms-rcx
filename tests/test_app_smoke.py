import importlib
from pathlib import Path
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

    def test_dashboard_avoids_removed_streamlit_width_api(self):
        source = Path("app.py").read_text(encoding="utf-8")

        self.assertNotIn("use_container_width", source)


if __name__ == "__main__":
    unittest.main()
