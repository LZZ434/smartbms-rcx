import json
import unittest
from pathlib import Path

import pandas as pd

from smartbms.reporting import export_portfolio
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


if __name__ == "__main__":
    unittest.main()
