import importlib
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _run_page(language: str, page_id: str) -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()
    language_widget = next(item for item in app.radio if item.key == "language")
    language_widget.set_value(language)
    app.run()
    page_widget = next(item for item in app.radio if item.key == "page_id")
    page_widget.set_value(page_id)
    app.run()
    return app


class DashboardSmokeTests(unittest.TestCase):
    def test_dashboard_module_imports_and_exposes_seven_stable_page_ids(self):
        module = importlib.import_module("app")

        self.assertTrue(callable(module.main))
        self.assertEqual(
            module.PAGE_IDS,
            (
                "overview",
                "plant_control",
                "energy_optimization",
                "data_quality",
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

    def test_user_facing_sources_have_no_known_mojibake(self):
        sources = "\n".join(
            Path(path).read_text(encoding="utf-8")
            for path in (
                "app.py",
                "smartbms/i18n.py",
                "smartbms/reporting.py",
                "smartbms/points.py",
            )
        )

        for broken in (
            "鈥?",
            "掳C",
            "馃彚",
            "脳 0.25",
            "危(power",
            "r茅sum茅",
            "攏o BACnet",
            "�",
        ):
            self.assertNotIn(broken, sources)

    def test_all_seven_pages_render_in_chinese_and_english(self):
        expected = {
            "overview": {"zh": "项目概览", "en": "Overview"},
            "plant_control": {"zh": "设备与控制", "en": "Plant & Control"},
            "energy_optimization": {"zh": "能源优化", "en": "Energy Optimization"},
            "data_quality": {"zh": "数据质量与导入", "en": "Data Quality & Import"},
            "rcx_diagnostics": {"zh": "再调试（RCx）诊断", "en": "RCx Diagnostics"},
            "bms_points_alarms": {"zh": "BMS 点表与报警", "en": "BMS Points & Alarms"},
            "learning_lab": {"zh": "学习实验室", "en": "Learning Lab"},
        }
        for page_id, labels in expected.items():
            for language, label in labels.items():
                with self.subTest(page=page_id, language=language):
                    app = _run_page(language, page_id)
                    self.assertFalse(app.exception)
                    self.assertEqual(app.title[0].value, label)

    def test_data_quality_page_renders_sample_analysis_in_both_languages(self):
        expected = {
            "zh": ("数据质量与导入", "内存中处理", "数据质量报告"),
            "en": (
                "Data Quality & Import",
                "processed in memory",
                "Data-quality report",
            ),
        }
        for language, phrases in expected.items():
            with self.subTest(language=language):
                app = _run_page(language, "data_quality")
                self.assertFalse(app.exception)
                rendered = "\n".join(
                    item.value
                    for group in (app.title, app.caption, app.info, app.markdown)
                    for item in group
                    if isinstance(item.value, str)
                )
                button_labels = "\n".join(
                    item.proto.label for item in app.download_button
                )
                combined = f"{rendered}\n{button_labels}"
                for phrase in phrases:
                    self.assertIn(phrase, combined)
                self.assertGreaterEqual(len(app.dataframe), 3)
                self.assertEqual(len(app.metric), 5)
                self.assertTrue(
                    any("2026" in item.value for item in app.metric)
                )

    def test_data_quality_downloads_keep_canonical_filenames(self):
        module = importlib.import_module("app")
        app = _run_page("zh", "data_quality")

        self.assertEqual(
            set(module.QUALITY_DOWNLOAD_FILENAMES.values()),
            {
                "smartbms-sample-trends.csv",
                "smartbms-normalized-trends.csv",
                "smartbms-data-quality-report.csv",
            },
        )
        self.assertEqual(len(app.download_button), 3)

    def test_chinese_rcx_page_localizes_action_and_tables(self):
        app = _run_page("zh", "rcx_diagnostics")

        self.assertTrue(any("建议措施" in item.value for item in app.success))
        self.assertIn("预期故障", app.dataframe[0].value.columns)
        self.assertIn("建议措施", app.dataframe[1].value.columns)

    def test_report_download_buttons_follow_selected_language(self):
        chinese = _run_page("zh", "overview")
        english = _run_page("en", "overview")

        self.assertEqual(
            [button.proto.label for button in chinese.download_button],
            ["下载 HTML 技术报告", "下载 Markdown 摘要"],
        )
        self.assertEqual(
            [button.proto.label for button in english.download_button],
            ["Download HTML technical report", "Download Markdown summary"],
        )

    def test_overview_shows_recruiter_evidence_in_both_languages(self):
        expected = {
            "zh": ("合成工程 PoC", "三分钟演示路线", "版本 1.0.0"),
            "en": ("Synthetic engineering PoC", "Three-minute demo path", "Release 1.0.0"),
        }
        for language, phrases in expected.items():
            with self.subTest(language=language):
                app = _run_page(language, "overview")
                self.assertFalse(app.exception)
                rendered = "\n".join(
                    item.value
                    for group in (
                        app.success,
                        app.subheader,
                        app.markdown,
                        app.caption,
                    )
                    for item in group
                    if isinstance(item.value, str)
                )
                for phrase in phrases:
                    self.assertIn(phrase, rendered)


if __name__ == "__main__":
    unittest.main()
