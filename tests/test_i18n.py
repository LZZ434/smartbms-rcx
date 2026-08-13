import re
import unittest

import pandas as pd

from smartbms.i18n import (
    LANGUAGE_NAMES,
    PAGE_IDS,
    TRANSLATIONS,
    format_day,
    localize_alarm_message,
    localize_findings_frame,
    localize_frame,
    page_label,
    quality_label,
    report_filename,
    scenario_label,
    t,
)
from smartbms.scenarios import run_portfolio_scenarios


class TranslationCoreTests(unittest.TestCase):
    def test_catalogs_have_identical_keys_and_nonempty_values(self):
        self.assertEqual(set(TRANSLATIONS["zh"]), set(TRANSLATIONS["en"]))
        for key in TRANSLATIONS["en"]:
            self.assertNotEqual(TRANSLATIONS["zh"][key], "")
            self.assertNotEqual(TRANSLATIONS["en"][key], "")

    def test_unsupported_language_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            t("fr", "app.title")
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            scenario_label("custom-scenario", "fr")

    def test_page_labels_are_unique_in_both_languages(self):
        self.assertEqual(len(PAGE_IDS), 7)
        for language in LANGUAGE_NAMES:
            labels = [page_label(page_id, language) for page_id in PAGE_IDS]
            self.assertEqual(len(set(labels)), 7)
        self.assertEqual(page_label("overview", "zh"), "项目概览")
        self.assertEqual(page_label("overview", "en"), "Overview")

    def test_quality_labels_are_bilingual_and_exports_remain_canonical(self):
        self.assertEqual(page_label("data_quality", "zh"), "数据质量与导入")
        self.assertEqual(page_label("data_quality", "en"), "Data Quality & Import")
        self.assertEqual(quality_label("timestamp_duplicate", "zh"), "重复时间戳")
        self.assertEqual(
            quality_label("timestamp_duplicate", "en"),
            "Duplicate timestamps",
        )

        source = pd.DataFrame(
            {
                "check_code": ["timestamps"],
                "status": ["fail"],
                "issue_code": ["timestamp_duplicate"],
                "severity": ["critical"],
                "category": ["sensor_bias"],
                "eligible": [True],
            }
        )
        localized = localize_frame(source, "zh")

        self.assertEqual(source.iloc[0]["status"], "fail")
        self.assertEqual(localized.iloc[0]["检查状态"], "未通过")
        self.assertEqual(localized.iloc[0]["问题代码"], "重复时间戳")
        self.assertEqual(localized.iloc[0]["严重程度"], "严重")
        self.assertEqual(localized.iloc[0]["可运行"], "是")

    def test_report_filenames_identify_the_selected_language(self):
        self.assertEqual(report_filename("zh", "html"), "smartbms-rcx-report-zh.html")
        self.assertEqual(report_filename("en", "md"), "smartbms-rcx-report-en.md")
        with self.assertRaisesRegex(ValueError, "unsupported report format"):
            report_filename("zh", "pdf")


class DomainLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = run_portfolio_scenarios()

    def test_all_four_findings_localize_without_losing_numbers(self):
        for category, run in self.bundle.fault_runs.items():
            with self.subTest(category=category):
                finding = next(item for item in run.findings if item.category == category)
                frame = localize_findings_frame([finding], "zh")
                rendered = " ".join(str(value) for value in frame.iloc[0])

                self.assertIn("建议措施", frame.columns)
                self.assertNotIn(finding.recommendation, rendered)
                for number in re.findall(r"[-+]?\d+(?:\.\d+)?", finding.evidence):
                    self.assertIn(number, rendered)

    def test_display_frame_is_localized_without_mutating_source(self):
        source = self.bundle.comparison.copy(deep=True)
        original_columns = list(source.columns)
        localized = localize_frame(source, "zh")

        self.assertIn("场景", localized.columns)
        self.assertEqual(localized.iloc[0]["场景"], "基线控制")
        self.assertEqual(list(source.columns), original_columns)
        self.assertEqual(source.iloc[0]["scenario"], "baseline")

    def test_boolean_display_translation_does_not_coerce_unknown_values(self):
        source = pd.DataFrame({"writable": [True, False, "unknown", None]})

        localized = localize_frame(source, "zh")

        self.assertEqual(localized["可写"].iloc[:3].tolist(), ["是", "否", "unknown"])
        self.assertTrue(pd.isna(localized["可写"].iloc[3]))

    def test_known_alarm_messages_and_day_labels_are_bilingual(self):
        self.assertEqual(
            localize_alarm_message("High zone temperature", "zh"),
            "区域温度过高",
        )
        day = self.bundle.baseline.trends.timestamp.dt.date.iloc[0]
        self.assertRegex(format_day(day, "zh"), r"\d+月\d+日")
        self.assertIn(day.strftime("%b"), format_day(day, "en"))


if __name__ == "__main__":
    unittest.main()
