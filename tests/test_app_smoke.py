import importlib
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class DashboardSmokeTests(unittest.TestCase):
    def test_dashboard_module_imports_and_exposes_six_stable_page_ids(self):
        module = importlib.import_module("app")

        self.assertTrue(callable(module.main))
        self.assertEqual(
            module.PAGE_IDS,
            (
                "overview",
                "plant_control",
                "energy_optimization",
                "rcx_diagnostics",
                "bms_points_alarms",
                "learning_lab",
            ),
        )

        labels = module._hidden_fault_labels(
            ("sensor_bias", "stuck_valve", "fouled_filter", "after_hours_operation")
        )
        self.assertEqual(len(set(labels.values())), 4)
        self.assertFalse(any(category in labels[category] for category in labels))

    def test_dashboard_defaults_to_chinese(self):
        app = AppTest.from_file(APP_PATH, default_timeout=30).run()

        self.assertFalse(app.exception)
        self.assertEqual(app.radio[0].value, "zh")
        self.assertEqual(app.radio[0].options, ["中文", "English"])
        self.assertEqual(app.radio[1].value, "overview")
        self.assertIn("项目概览", app.radio[1].options)
        self.assertEqual(app.title[0].value, "项目概览")

    def test_dashboard_avoids_removed_streamlit_width_api(self):
        source = Path("app.py").read_text(encoding="utf-8")

        self.assertNotIn("use_container_width", source)


if __name__ == "__main__":
    unittest.main()
