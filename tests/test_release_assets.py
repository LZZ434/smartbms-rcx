from pathlib import Path
import unittest


class ReleaseAssetTests(unittest.TestCase):
    def test_cloud_dependencies_are_exactly_pinned(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertEqual(
            requirements.splitlines(),
            [
                "numpy==2.5.2",
                "pandas==3.0.5",
                "streamlit==1.61.1",
            ],
        )

    def test_ci_license_and_data_contract_exist(self):
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn('python-version: ["3.11", "3.12"]', workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn(
            "python scripts/generate_portfolio.py --output generated",
            workflow,
        )
        self.assertIn("MIT License", Path("LICENSE").read_text(encoding="utf-8"))
        self.assertIn(
            "Rule-specific readiness",
            Path("docs/data-contract.md").read_text(encoding="utf-8"),
        )

    def test_streamlit_upload_limit_is_ten_megabytes(self):
        config = Path(".streamlit/config.toml").read_text(encoding="utf-8")

        self.assertIn("maxUploadSize = 10", config)


if __name__ == "__main__":
    unittest.main()
