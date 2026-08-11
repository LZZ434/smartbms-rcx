import json
import unittest
from pathlib import Path

import pandas as pd

from smartbms.config import ProjectConfig, SimulationConfig
from smartbms.reporting import export_portfolio, render_html_report, render_markdown_report
from smartbms.scenarios import run_portfolio_scenarios


class PortfolioReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = run_portfolio_scenarios()

    def output_dir(self, case: str) -> Path:
        path = Path.cwd() / "generated" / "test-reporting" / case
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_export_writes_expected_report_and_csv_files(self):
        directory = self.output_dir("files")
        paths = export_portfolio(self.bundle, directory)
        names = {path.name for path in paths}

        self.assertTrue((directory / "rcx-report.html").exists())
        self.assertTrue((directory / "rcx-report.md").exists())
        self.assertTrue((directory / "scenario-comparison.csv").exists())
        self.assertIn("trends-baseline.csv", names)
        self.assertIn("trends-optimized.csv", names)
        self.assertIn("diagnostic-findings.csv", names)

    def test_report_discloses_synthetic_data_and_verified_metrics(self):
        directory = self.output_dir("disclosure")
        export_portfolio(self.bundle, directory)
        html = (directory / "rcx-report.html").read_text(encoding="utf-8")

        savings = self.bundle.comparison.loc[
            self.bundle.comparison.scenario == "optimized", "energy_savings_pct"
        ].iloc[0]
        self.assertIn("Synthetic", html)
        self.assertIn(f"{savings:.3f}%", html)
        self.assertIn("not measured building performance", html)

    def test_csv_and_manifest_are_machine_readable(self):
        directory = self.output_dir("machine-readable")
        export_portfolio(self.bundle, directory)
        comparison = pd.read_csv(directory / "scenario-comparison.csv")
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(set(comparison.scenario), {"baseline", "optimized"})
        self.assertEqual(manifest["data_classification"], "synthetic")
        self.assertIn("rcx-report.html", manifest["files"])

    def test_manifest_uses_the_scenario_seed_instead_of_a_hard_coded_value(self):
        bundle = run_portfolio_scenarios(
            ProjectConfig(simulation=SimulationConfig(seed=99))
        )
        directory = self.output_dir("custom-seed")
        export_portfolio(bundle, directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["deterministic_seed"], 99)

    def test_dashboard_reports_render_in_both_languages_without_metric_drift(self):
        savings = self.bundle.comparison.loc[
            self.bundle.comparison.scenario == "optimized", "energy_savings_pct"
        ].iloc[0]

        html_zh = render_html_report(self.bundle, language="zh")
        html_en = render_html_report(self.bundle, language="en")
        markdown_zh = render_markdown_report(self.bundle, language="zh")
        markdown_en = render_markdown_report(self.bundle, language="en")

        self.assertIn('<html lang="zh-CN">', html_zh)
        self.assertIn("技术报告", html_zh)
        self.assertIn("合成数据声明", markdown_zh)
        self.assertIn('<html lang="en">', html_en)
        self.assertIn("Technical Report", html_en)
        self.assertIn("Synthetic-data disclosure", markdown_en)
        for report in (html_zh, html_en, markdown_zh, markdown_en):
            self.assertIn(f"{savings:.3f}%", report)

    def test_report_rejects_unsupported_language(self):
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            render_html_report(self.bundle, language="fr")


if __name__ == "__main__":
    unittest.main()
