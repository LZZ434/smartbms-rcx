# SmartBMS-RCx Public Portfolio Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested BMS trend-data quality and rule-admission workflow, improve recruiter-facing evidence, automate verification, and publish SmartBMS-RCx as a public GitHub/Streamlit portfolio application.

**Architecture:** Keep the deterministic simulation and verified KPI bundle unchanged. Add strict CSV ingestion, a pure data-quality engine, rule-selective diagnostic execution, and stable export adapters beneath one new bilingual Streamlit page; release metadata, CI, documentation, and hosting remain separate boundaries.

**Tech Stack:** Python 3.11/3.12, dataclasses, pandas, NumPy, Streamlit 1.61, standard-library unittest, Streamlit AppTest, GitHub Actions, GitHub CLI, Streamlit Community Cloud.

---

## File map

- Create smartbms/trend_io.py — strict in-memory CSV and DataFrame canonicalization.
- Create smartbms/data_quality.py — pure checks, score, and per-rule readiness.
- Create smartbms/screening.py — quality-gated calls into selected diagnostic rules.
- Create smartbms/data_quality_reporting.py — stable English-schema export frames.
- Create smartbms/release.py — public repository and release/build metadata.
- Modify smartbms/diagnostics.py — backward-compatible category selection and required-column contracts.
- Modify smartbms/i18n.py — seventh page and quality/release presentation strings.
- Modify app.py — Data Quality page and recruiter evidence on Overview.
- Create tests/test_trend_io.py, tests/test_data_quality.py, tests/test_screening.py, tests/test_release.py.
- Modify tests/test_diagnostics.py, tests/test_i18n.py, tests/test_app_smoke.py.
- Create .github/workflows/ci.yml, LICENSE, docs/data-contract.md.
- Modify .streamlit/config.toml, pyproject.toml, requirements.txt, README.md, README.zh-CN.md, docs/demo-script.md, docs/resume-bullets.md.

### Task 1: Make diagnostic execution selectable by rule

**Files:**
- Modify: smartbms/diagnostics.py
- Modify: tests/test_diagnostics.py

- [ ] **Step 1: Write failing tests for rule-specific execution**

Add these methods to DiagnosticRuleTests:

    def test_selected_rule_requires_only_its_own_columns(self):
        trends = diagnostic_fixture("sensor_bias")[
            ["timestamp", "east_temp_measured_c", "east_temp_reference_c"]
        ]

        findings = run_diagnostics(trends, categories=("sensor_bias",))

        self.assertEqual([item.category for item in findings], ["sensor_bias"])

    def test_unselected_fault_rule_does_not_run(self):
        findings = run_diagnostics(
            diagnostic_fixture("stuck_valve"),
            categories=("sensor_bias",),
        )

        self.assertEqual(findings, [])

    def test_empty_rule_selection_returns_no_findings(self):
        self.assertEqual(run_diagnostics(pd.DataFrame(), categories=()), [])

    def test_unknown_rule_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported diagnostic categories"):
            run_diagnostics(
                diagnostic_fixture("healthy"),
                categories=("unknown",),
            )

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

    .\.venv\Scripts\python.exe -m unittest tests.test_diagnostics.DiagnosticRuleTests.test_selected_rule_requires_only_its_own_columns tests.test_diagnostics.DiagnosticRuleTests.test_unselected_fault_rule_does_not_run tests.test_diagnostics.DiagnosticRuleTests.test_empty_rule_selection_returns_no_findings tests.test_diagnostics.DiagnosticRuleTests.test_unknown_rule_selection_is_rejected -v

Expected: failures because run_diagnostics does not accept categories.

- [ ] **Step 3: Add stable category and required-column contracts**

In smartbms/diagnostics.py import Iterable and define:

    DIAGNOSTIC_CATEGORIES = (
        "sensor_bias",
        "stuck_valve",
        "fouled_filter",
        "after_hours_operation",
    )

    REQUIRED_COLUMNS_BY_CATEGORY = {
        "sensor_bias": frozenset(
            {"timestamp", "east_temp_measured_c", "east_temp_reference_c"}
        ),
        "stuck_valve": frozenset(
            {
                "timestamp",
                "cooling_cmd_east",
                "valve_east",
                "east_temp_measured_c",
            }
        ),
        "fouled_filter": frozenset(
            {
                "timestamp",
                "airflow_cmd_east",
                "airflow_east",
                "fan_power_kw",
                "expected_fan_power_kw",
            }
        ),
        "after_hours_operation": frozenset(
            {"timestamp", "occupied", "cooling_cmd_east", "hvac_power_kw"}
        ),
    }

Add:

    def _select_categories(categories: Iterable[str] | None) -> tuple[str, ...]:
        selected = (
            DIAGNOSTIC_CATEGORIES
            if categories is None
            else tuple(dict.fromkeys(categories))
        )
        unknown = sorted(set(selected).difference(DIAGNOSTIC_CATEGORIES))
        if unknown:
            raise ValueError(f"unsupported diagnostic categories: {unknown}")
        return selected

Extend run_diagnostics with categories: Iterable[str] | None = None. Validate only the union of REQUIRED_COLUMNS_BY_CATEGORY for selected categories. Wrap each of the four existing rule blocks in an if-category-selected condition. Keep parameter validation and default behavior unchanged.

- [ ] **Step 4: Run diagnostic tests and confirm GREEN**

Run:

    .\.venv\Scripts\python.exe -m unittest tests.test_diagnostics tests.test_scenarios -v

Expected: all existing and new diagnostic/scenario tests pass with unchanged 4/4 regression behavior.

- [ ] **Step 5: Commit**

    git add smartbms\diagnostics.py tests\test_diagnostics.py
    git commit -m "refactor: admit RCx rules independently"

### Task 2: Add strict trend ingestion

**Files:**
- Create: smartbms/trend_io.py
- Create: tests/test_trend_io.py

- [ ] **Step 1: Write failing ingestion tests**

Create tests/test_trend_io.py with tests using the real baseline frame:

    import unittest

    import pandas as pd

    from smartbms.scenarios import run_portfolio_scenarios
    from smartbms.trend_io import (
        MAX_UPLOAD_BYTES,
        TrendIngestionError,
        canonicalize_trend_frame,
        ingest_csv_bytes,
    )


    class TrendIngestionTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.baseline = run_portfolio_scenarios().baseline.trends

        def test_valid_csv_round_trip_preserves_rows_and_canonical_types(self):
            result = ingest_csv_bytes(
                self.baseline.to_csv(index=False).encode("utf-8")
            )

            self.assertEqual(len(result.frame), len(self.baseline))
            self.assertTrue(pd.api.types.is_datetime64_any_dtype(result.frame["timestamp"]))
            self.assertEqual(result.frame["occupied"].dtype, bool)
            self.assertEqual(result.frame["scenario"].iloc[0], "baseline")

        def test_utf8_bom_csv_is_accepted(self):
            payload = b"\xef\xbb\xbf" + self.baseline.head(4).to_csv(index=False).encode("utf-8")

            result = ingest_csv_bytes(payload)

            self.assertIn("timestamp", result.frame.columns)

        def test_canonicalization_does_not_mutate_input_or_sort_rows(self):
            source = self.baseline.head(8).iloc[::-1].copy()
            original = source.copy(deep=True)

            result = canonicalize_trend_frame(source)

            pd.testing.assert_frame_equal(source, original)
            self.assertEqual(result.frame["timestamp"].tolist(), original["timestamp"].tolist())

        def test_empty_oversized_and_missing_timestamp_inputs_are_rejected(self):
            cases = (
                (b"", "empty_file"),
                (b"x" * (MAX_UPLOAD_BYTES + 1), "file_too_large"),
                (b"value\n1\n", "missing_timestamp"),
            )
            for payload, code in cases:
                with self.subTest(code=code):
                    with self.assertRaises(TrendIngestionError) as caught:
                        ingest_csv_bytes(payload)
                    self.assertEqual(caught.exception.code, code)

        def test_invalid_timestamp_numeric_and_boolean_values_are_rejected(self):
            frames = (
                (pd.DataFrame({"timestamp": ["bad"]}), "invalid_timestamp"),
                (
                    pd.DataFrame(
                        {"timestamp": ["2026-08-01"], "hvac_power_kw": ["bad"]}
                    ),
                    "invalid_numeric",
                ),
                (
                    pd.DataFrame(
                        {"timestamp": ["2026-08-01"], "occupied": ["maybe"]}
                    ),
                    "invalid_boolean",
                ),
            )
            for frame, code in frames:
                with self.subTest(code=code):
                    with self.assertRaises(TrendIngestionError) as caught:
                        canonicalize_trend_frame(frame)
                    self.assertEqual(caught.exception.code, code)


    if __name__ == "__main__":
        unittest.main()

- [ ] **Step 2: Run and confirm RED**

    .\.venv\Scripts\python.exe -m unittest tests.test_trend_io -v

Expected: import failure because smartbms.trend_io does not exist.

- [ ] **Step 3: Implement the ingestion boundary**

Create smartbms/trend_io.py with:

    MAX_UPLOAD_BYTES = 10 * 1024 * 1024

    @dataclass(frozen=True)
    class IngestionNotice:
        code: str
        column: str | None = None
        affected_rows: int = 0

    @dataclass(frozen=True)
    class TrendIngestionResult:
        frame: pd.DataFrame
        notices: tuple[IngestionNotice, ...] = ()

    class TrendIngestionError(ValueError):
        def __init__(self, code: str, detail: str):
            self.code = code
            self.detail = detail
            super().__init__(detail)

Define explicit BOOLEAN_COLUMNS for synthetic, occupied, preconditioning_authorized, controller_fallback, and fault_active. Define NUMERIC_COLUMNS from the known simulation trend schema. Implement strict scalar boolean parsing for actual booleans, 0/1, and case-insensitive true/false/yes/no only.

canonicalize_trend_frame must copy deeply, reject empty data or duplicate column names, require and parse timestamp, coerce only known numeric/boolean columns, reject invalid non-null values with stable error codes, preserve unknown columns, preserve input row order, and return TrendIngestionResult.

ingest_csv_bytes must enforce MAX_UPLOAD_BYTES before pandas parsing, read UTF-8-sig through BytesIO, convert pandas parser errors to malformed_csv, and delegate to canonicalize_trend_frame.

- [ ] **Step 4: Run ingestion tests and confirm GREEN**

    .\.venv\Scripts\python.exe -m unittest tests.test_trend_io -v

Expected: all ingestion tests pass.

- [ ] **Step 5: Commit**

    git add smartbms\trend_io.py tests\test_trend_io.py
    git commit -m "feat: add strict BMS trend ingestion"

### Task 3: Build the deterministic data-quality engine

**Files:**
- Create: smartbms/data_quality.py
- Create: tests/test_data_quality.py

- [ ] **Step 1: Write failing quality and readiness tests**

Create tests/test_data_quality.py. Use a deep copy of the first 96 baseline rows and add independent tests that assert:

    class DataQualityTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.baseline = run_portfolio_scenarios().baseline.trends.head(96)

        def test_healthy_baseline_scores_100_and_admits_all_rules(self):
            report = assess_trend_quality(self.baseline)

            self.assertEqual(report.score, 100.0)
            self.assertEqual(report.sampling_interval_minutes, 15.0)
            self.assertTrue(all(item.eligible for item in report.readiness))

        def test_assessment_does_not_mutate_source(self):
            source = self.baseline.copy(deep=True)
            original = source.copy(deep=True)

            assess_trend_quality(source)

            pd.testing.assert_frame_equal(source, original)

        def test_duplicate_unsorted_and_irregular_timestamps_are_critical(self):
            variants = {}
            duplicated = self.baseline.copy()
            duplicated.loc[1, "timestamp"] = duplicated.loc[0, "timestamp"]
            variants["timestamp_duplicate"] = duplicated
            variants["timestamp_unsorted"] = self.baseline.iloc[::-1]
            irregular = self.baseline.copy()
            irregular.loc[10:, "timestamp"] += pd.Timedelta(minutes=5)
            variants["timestamp_irregular"] = irregular
            for code, frame in variants.items():
                with self.subTest(code=code):
                    report = assess_trend_quality(frame)
                    self.assertIn(code, {issue.code for issue in report.issues})
                    self.assertFalse(any(item.eligible for item in report.readiness))

        def test_missing_columns_block_only_affected_rules(self):
            frame = self.baseline.drop(
                columns=["east_temp_reference_c", "airflow_east"]
            )

            report = assess_trend_quality(frame)
            readiness = {item.category: item for item in report.readiness}

            self.assertFalse(readiness["sensor_bias"].eligible)
            self.assertFalse(readiness["fouled_filter"].eligible)
            self.assertTrue(readiness["stuck_valve"].eligible)
            self.assertTrue(readiness["after_hours_operation"].eligible)

        def test_missing_frozen_out_of_range_and_rate_issues_are_detected(self):
            variants = {}
            missing = self.baseline.copy()
            missing.loc[10:20, "east_temp_measured_c"] = np.nan
            variants["missing_values"] = missing
            frozen = self.baseline.copy()
            frozen.loc[10:25, "east_temp_measured_c"] = 24.0
            variants["frozen_signal"] = frozen
            bounded = self.baseline.copy()
            bounded.loc[10, "cooling_cmd_east"] = 1.5
            variants["engineering_bounds"] = bounded
            rate = self.baseline.copy()
            rate.loc[10, "east_temp_measured_c"] += 5.0
            variants["temperature_rate"] = rate
            for code, frame in variants.items():
                with self.subTest(code=code):
                    report = assess_trend_quality(frame)
                    self.assertIn(code, {issue.code for issue in report.issues})
                    self.assertLess(report.score, 100.0)

- [ ] **Step 2: Run and confirm RED**

    .\.venv\Scripts\python.exe -m unittest tests.test_data_quality -v

Expected: import failure because smartbms.data_quality does not exist.

- [ ] **Step 3: Implement quality dataclasses and checks**

Create immutable QualityIssue, QualityCheckResult, DiagnosticReadiness, and DataQualityReport dataclasses exactly as specified by the design. DataQualityReport exposes an issues property that flattens check issues.

Use these stable check weights, totaling 100:

    CHECK_WEIGHTS = {
        "timestamps": 20,
        "history": 10,
        "coverage": 15,
        "missing": 15,
        "frozen": 10,
        "bounds": 15,
        "temperature_rate": 10,
        "cross_point": 5,
    }

Status is pass, warning, or fail. A pass earns full weight, warning earns half, and fail earns zero. Score is the rounded sum. The 16-row minimum supports four-sample persistence with meaningful context.

Implement:

- duplicate, monotonic, and regular timestamp checks; any defect is critical;
- inferred median interval in minutes;
- missing required-column coverage from REQUIRED_COLUMNS_BY_CATEGORY;
- missing-value issues, critical for diagnostic-required columns and warning otherwise;
- a frozen run of at least eight unchanged samples in measured/reference temperature signals;
- bounds: outdoor -20..55 °C, zone/reference/target 5..45 °C, humidity 0..100%, normalized command/valve/airflow 0..1, non-negative power, COP 0.5..10;
- zone-temperature step over 2 °C as critical;
- HVAC power below fan power or non-positive expected fan power during active airflow as cross-point critical.

Build readiness from REQUIRED_COLUMNS_BY_CATEGORY. Global timestamp/history critical issues block every rule. Other critical issues block a rule only when affected columns intersect that rule's requirements. Missing columns are listed explicitly and never synthesized.

- [ ] **Step 4: Run quality, diagnostic, and scenario tests**

    .\.venv\Scripts\python.exe -m unittest tests.test_data_quality tests.test_diagnostics tests.test_scenarios -v

Expected: all pass; fixed KPI and diagnostic results remain unchanged.

- [ ] **Step 5: Commit**

    git add smartbms\data_quality.py tests\test_data_quality.py
    git commit -m "feat: assess BMS trend data quality"

### Task 4: Add quality-gated screening and stable exports

**Files:**
- Create: smartbms/screening.py
- Create: smartbms/data_quality_reporting.py
- Create: tests/test_screening.py

- [ ] **Step 1: Write failing admission/export tests**

Create tests/test_screening.py:

    class ScreeningTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.bundle = run_portfolio_scenarios()

        def test_healthy_sample_is_eligible_and_has_no_screening_findings(self):
            result = screen_trends(self.bundle.baseline.trends)

            self.assertEqual(result.findings, ())
            self.assertTrue(all(item.eligible for item in result.quality.readiness))

        def test_fault_sample_returns_only_admitted_finding(self):
            frame = self.bundle.fault_runs["stuck_valve"].trends.drop(
                columns=["east_temp_reference_c"]
            )

            result = screen_trends(frame)

            self.assertEqual(
                [item.category for item in result.findings],
                ["stuck_valve"],
            )
            readiness = {item.category: item for item in result.quality.readiness}
            self.assertFalse(readiness["sensor_bias"].eligible)

        def test_critical_timestamp_issue_blocks_all_diagnostics(self):
            frame = self.bundle.fault_runs["stuck_valve"].trends.iloc[::-1]

            result = screen_trends(frame)

            self.assertEqual(result.findings, ())
            self.assertFalse(any(item.eligible for item in result.quality.readiness))

        def test_export_frames_keep_stable_english_schema(self):
            result = screen_trends(self.bundle.baseline.trends)

            self.assertEqual(
                list(quality_report_frame(result.quality).columns),
                [
                    "check_code",
                    "status",
                    "weight",
                    "issue_code",
                    "severity",
                    "columns",
                    "affected_rows",
                    "detail",
                ],
            )
            self.assertEqual(
                list(readiness_frame(result.quality).columns),
                [
                    "category",
                    "eligible",
                    "required_columns",
                    "missing_columns",
                    "blocking_issue_codes",
                ],
            )

- [ ] **Step 2: Run and confirm RED**

    .\.venv\Scripts\python.exe -m unittest tests.test_screening -v

Expected: imports fail because screening/reporting modules do not exist.

- [ ] **Step 3: Implement screening**

Create ScreeningResult with canonical frame, DataQualityReport, and a tuple of DiagnosticFinding. screen_trends copies the input, assesses quality, then calls run_diagnostics once per eligible category with categories=(category,) and timestep_minutes equal to the validated inferred interval. Concatenate findings in DIAGNOSTIC_CATEGORIES order. Catch no programming errors; admission must prevent expected schema/data errors.

Create checks_frame, issues_frame, readiness_frame, and quality_report_frame in smartbms/data_quality_reporting.py. Every adapter returns a new DataFrame with the exact stable English columns asserted above. A passing check produces one quality-report row with blank issue fields so the exported report always documents every check.

- [ ] **Step 4: Run screening and regression tests**

    .\.venv\Scripts\python.exe -m unittest tests.test_screening tests.test_data_quality tests.test_diagnostics -v

Expected: all pass.

- [ ] **Step 5: Commit**

    git add smartbms\screening.py smartbms\data_quality_reporting.py tests\test_screening.py
    git commit -m "feat: gate RCx screening on data quality"

### Task 5: Localize and render the seventh Data Quality page

**Files:**
- Modify: smartbms/i18n.py
- Modify: app.py
- Modify: tests/test_i18n.py
- Modify: tests/test_app_smoke.py

- [ ] **Step 1: Write failing i18n and AppTest coverage**

Update PAGE_IDS expectations to insert data_quality between energy_optimization and rcx_diagnostics. Change six-page names/counts to seven. Add:

    def test_quality_labels_are_bilingual_and_exports_remain_canonical(self):
        self.assertEqual(page_label("data_quality", "zh"), "数据质量与导入")
        self.assertEqual(page_label("data_quality", "en"), "Data Quality & Import")
        self.assertEqual(quality_label("timestamp_duplicate", "zh"), "重复时间戳")
        self.assertEqual(quality_label("timestamp_duplicate", "en"), "Duplicate timestamps")

Add AppTest assertions:

    def test_data_quality_page_renders_sample_analysis_in_both_languages(self):
        expected = {
            "zh": ("数据质量与导入", "内存中处理", "数据质量报告"),
            "en": ("Data Quality & Import", "processed in memory", "Data-quality report"),
        }
        for language, phrases in expected.items():
            app = _run_page(language, "data_quality")
            self.assertFalse(app.exception)
            rendered = "\n".join(
                item.value
                for group in (app.title, app.caption, app.info, app.markdown)
                for item in group
                if isinstance(item.value, str)
            )
            for phrase in phrases:
                self.assertIn(phrase, rendered)
            self.assertGreaterEqual(len(app.dataframe), 3)

    def test_data_quality_downloads_keep_canonical_filenames(self):
        app = _run_page("zh", "data_quality")
        names = {item.file_name for item in app.download_button}
        self.assertEqual(
            names,
            {
                "smartbms-sample-trends.csv",
                "smartbms-normalized-trends.csv",
                "smartbms-data-quality-report.csv",
            },
        )

- [ ] **Step 2: Run focused tests and confirm RED**

    .\.venv\Scripts\python.exe -m unittest tests.test_i18n.TranslationCoreTests.test_quality_labels_are_bilingual_and_exports_remain_canonical tests.test_app_smoke.DashboardSmokeTests.test_data_quality_page_renders_sample_analysis_in_both_languages tests.test_app_smoke.DashboardSmokeTests.test_data_quality_downloads_keep_canonical_filenames -v

Expected: missing data_quality page/labels and page renderer.

- [ ] **Step 3: Extend the catalog and display adapters**

Add page.data_quality and these key families in both languages with matching placeholders:

- quality.subtitle, quality.disclosure, quality.privacy, quality.sample_download, quality.upload, quality.upload_help;
- quality.source_sample, quality.source_upload, quality.rows, quality.interval, quality.score, quality.ready_rules;
- quality.checks, quality.issues, quality.no_issues, quality.readiness, quality.findings, quality.no_findings;
- quality.preview, quality.normalized_download, quality.report_download, quality.screening_disclosure;
- quality.error.empty_file, file_too_large, malformed_csv, missing_timestamp, invalid_timestamp, invalid_numeric, invalid_boolean, duplicate_columns;
- quality.status.pass/warning/fail, quality.severity.critical/warning/info;
- labels for all eight check codes and all emitted issue codes.

Add quality_label(code, language), status/severity value maps, and column labels for check_code, status, weight, issue_code, severity, columns, affected_rows, detail, category, eligible, required_columns, missing_columns, and blocking_issue_codes. Enhance localize_frame to translate known quality codes/status/severity/category and actual boolean eligible values only.

- [ ] **Step 4: Implement the page**

Add pure helpers in app.py:

    def _csv_bytes(frame: pd.DataFrame) -> bytes:
        return frame.to_csv(index=False).encode("utf-8-sig")

    def _quality_error_message(error: TrendIngestionError, language: str) -> str:
        return t(language, f"quality.error.{error.code}")

render_data_quality loads the baseline through canonicalize_trend_frame by default or ingest_csv_bytes for an uploaded file. It shows the privacy/disclosure text before st.file_uploader(type=["csv"]). It passes the canonical frame to screen_trends, renders four metrics, localized copies of checks/issues/readiness, localized screening findings, and a 100-row preview. The three downloads use canonical raw schemas and exact filenames. Ingestion errors render st.error and return without traceback.

Add data_quality to renderer dispatch and PAGE_IDS. Keep the fixed ScenarioBundle and Overview KPIs unchanged.

- [ ] **Step 5: Run all i18n and app tests**

    .\.venv\Scripts\python.exe -m unittest tests.test_i18n tests.test_app_smoke tests.test_screening -v

Expected: seven pages render in both languages; quality sample and downloads pass.

- [ ] **Step 6: Commit**

    git add app.py smartbms\i18n.py tests\test_i18n.py tests\test_app_smoke.py
    git commit -m "feat: add bilingual BMS data-quality workspace"

### Task 6: Add recruiter evidence and release metadata

**Files:**
- Create: smartbms/release.py
- Create: tests/test_release.py
- Modify: smartbms/__init__.py
- Modify: pyproject.toml
- Modify: app.py
- Modify: smartbms/i18n.py
- Modify: tests/test_app_smoke.py

- [ ] **Step 1: Write failing release tests**

Create tests/test_release.py:

    import os
    import unittest
    from unittest.mock import patch

    from smartbms.release import PUBLIC_REPOSITORY_URL, release_info


    class ReleaseInfoTests(unittest.TestCase):
        def test_public_repository_and_release_version_are_stable(self):
            info = release_info()
            self.assertEqual(info.version, "1.0.0")
            self.assertEqual(
                PUBLIC_REPOSITORY_URL,
                "https://github.com/LZZ434/smartbms-rcx",
            )

        def test_host_commit_is_shortened_without_breaking_local_fallback(self):
            with patch.dict(os.environ, {"GITHUB_SHA": "1234567890abcdef"}):
                self.assertEqual(release_info().commit, "1234567")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(release_info().commit, "local")

Add an AppTest that checks the Chinese Overview contains “合成工程 PoC”, “三分钟演示路线”, and version 1.0.0; English contains “Synthetic engineering PoC” and “Three-minute demo path.”

- [ ] **Step 2: Run and confirm RED**

    .\.venv\Scripts\python.exe -m unittest tests.test_release tests.test_app_smoke.DashboardSmokeTests.test_overview_shows_recruiter_evidence_in_both_languages -v

Expected: missing release module/evidence.

- [ ] **Step 3: Implement metadata and Overview evidence**

Create ReleaseInfo(version, commit, repository_url) and release_info() in smartbms/release.py. Read GITHUB_SHA, then STREAMLIT_GIT_COMMIT, otherwise local; expose only seven characters. Set __version__ and pyproject project version to 1.0.0.

Add bilingual translation keys for:

- overview.badge;
- overview.demo_title and overview.demo.1/2/3;
- overview.evidence_title, overview.evidence.tests, overview.evidence.seed, overview.evidence.boundary;
- overview.repository and overview.release.

Render a compact badge/disclosure, numbered three-step demo, test/seed/boundary evidence, repository link button, and version/commit caption above the existing report downloads. Do not change KPI calculations.

- [ ] **Step 4: Run release, app, and KPI tests**

    .\.venv\Scripts\python.exe -m unittest tests.test_release tests.test_app_smoke tests.test_scenarios tests.test_reporting -v

Expected: all pass and fixed KPI strings remain unchanged.

- [ ] **Step 5: Commit**

    git add smartbms\release.py tests\test_release.py smartbms\__init__.py pyproject.toml app.py smartbms\i18n.py tests\test_app_smoke.py
    git commit -m "feat: present recruiter-ready release evidence"

### Task 7: Add reproducible public-release assets and documentation

**Files:**
- Create: .github/workflows/ci.yml
- Create: LICENSE
- Create: docs/data-contract.md
- Modify: .streamlit/config.toml
- Modify: requirements.txt
- Modify: README.md
- Modify: README.zh-CN.md
- Modify: docs/demo-script.md
- Modify: docs/resume-bullets.md
- Create: tests/test_release_assets.py

- [ ] **Step 1: Write failing release-asset tests**

Create tests/test_release_assets.py to assert:

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
            self.assertIn("python scripts/generate_portfolio.py --output generated", workflow)
            self.assertIn("MIT License", Path("LICENSE").read_text(encoding="utf-8"))
            self.assertIn(
                "Rule-specific readiness",
                Path("docs/data-contract.md").read_text(encoding="utf-8"),
            )

        def test_streamlit_upload_limit_is_ten_megabytes(self):
            config = Path(".streamlit/config.toml").read_text(encoding="utf-8")
            self.assertIn("maxUploadSize = 10", config)

- [ ] **Step 2: Run and confirm RED**

    .\.venv\Scripts\python.exe -m unittest tests.test_release_assets -v

Expected: missing assets and unpinned requirements.

- [ ] **Step 3: Add exact CI and runtime configuration**

Pin requirements exactly as asserted. Add maxUploadSize = 10 under [server].

Create .github/workflows/ci.yml:

    name: CI

    on:
      push:
      pull_request:

    permissions:
      contents: read

    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          fail-fast: false
          matrix:
            python-version: ["3.11", "3.12"]
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: \${{ matrix.python-version }}
              cache: pip
          - run: python -m pip install --upgrade pip
          - run: python -m pip install -r requirements.txt
          - run: python -m pip install -e . --no-deps
          - run: python -m unittest discover -s tests -v
          - run: python -m compileall -q app.py smartbms scripts tests
          - run: python -m pip check
          - run: python scripts/generate_portfolio.py --output generated

- [ ] **Step 4: Add license, data contract, and truthful docs**

Add the standard MIT License with “Copyright (c) 2026 LZZ434.”

docs/data-contract.md documents the exact canonical timestamp, numeric, boolean, contextual, and rule-required fields; the eight checks and thresholds; rule-specific readiness; English export contracts; upload in-memory privacy; and synthetic/field-validation boundary.

Update both READMEs with the public repository URL, preferred live URL https://smartbms-rcx-hk.streamlit.app, CI badge, seven-page quick start, CSV workflow, privacy note, Community Cloud sleep note, and public-deployment limitations. If the preferred subdomain is unavailable at deployment, replace it with the confirmed live URL before final release.

Update docs/demo-script.md to demonstrate the Data Quality page between Energy Optimization and RCx. Update docs/resume-bullets.md with a truthful bullet covering strict ingestion, eight deterministic checks, rule-specific admission, and public CI/deployment. Replace the documented test number after the final suite by using the exact “Ran N tests” output.

- [ ] **Step 5: Run release assets and complete suite**

    .\.venv\Scripts\python.exe -m unittest tests.test_release_assets -v
    .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    .\.venv\Scripts\python.exe -m compileall -q app.py smartbms scripts tests
    .\.venv\Scripts\python.exe -m pip check
    .\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
    git diff --check

Expected: all commands exit 0; generated results remain 5.623%, 100% comfort, 4/4, and 45 minutes.

- [ ] **Step 6: Commit**

    git add .github\workflows\ci.yml LICENSE docs\data-contract.md .streamlit\config.toml requirements.txt README.md README.zh-CN.md docs\demo-script.md docs\resume-bullets.md tests\test_release_assets.py
    git commit -m "chore: prepare SmartBMS public release"

### Task 8: Review and local acceptance

**Files:**
- Modify only files required by review findings, with a failing regression test first.

- [ ] **Step 1: Run full fresh verification**

    .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    .\.venv\Scripts\python.exe -m compileall -q app.py smartbms scripts tests
    .\.venv\Scripts\python.exe -m pip check
    .\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
    git diff --check

Record the exact test count and update every README/demo/resume reference to that count with apply_patch. Rerun the full suite after changing docs.

- [ ] **Step 2: Verify regression values by independent assertions**

Run a Python assertion command against ScenarioBundle and generated CSVs confirming baseline 844.288 kWh, optimized 796.814 kWh, 5.623%, 100%, 4/4, 45 minutes, canonical English reports, and stable raw schemas.

- [ ] **Step 3: Perform code-quality review**

Review master...HEAD for correctness, data-loss risk, misleading claims, i18n boundaries, upload safety, deployment behavior, and maintainability. Fix every high/medium issue by adding a failing regression test, watching RED, applying the minimal fix, and rerunning GREEN.

- [ ] **Step 4: Run local browser acceptance**

Start only the feature app on an unused port. Verify:

- default Chinese and switch to English/back;
- all seven pages;
- healthy bundled sample, valid CSV upload, malformed CSV error;
- canonical download filenames;
- desktop and narrow viewport;
- no application console errors;
- /_stcore/health returns HTTP 200.

Stop only the verification server.

- [ ] **Step 5: Secret and publication scan**

Check tracked files, ignored files, Git history names, and staged changes for common token/private-key patterns without printing any secret value. Confirm .venv, generated logs, .streamlit/secrets.toml, local uploads, and browser artifacts are untracked/ignored.

- [ ] **Step 6: Commit final review fixes**

    git add app.py smartbms tests README.md README.zh-CN.md docs .streamlit requirements.txt pyproject.toml .github LICENSE
    git commit -m "test: complete SmartBMS release acceptance"

Skip this commit only when there are no changes after review.

### Task 9: Integrate, publish, deploy, and accept production

**Files:**
- Modify README.md and README.zh-CN.md only if the confirmed live URL differs from the preferred URL.

- [ ] **Step 1: Integrate the verified feature branch**

Fast-forward merge the feature branch into master. On merged master rerun the complete unittest suite and generation command. Remove the clean temporary worktree and delete the merged branch only after merged-master verification succeeds.

- [ ] **Step 2: Reauthenticate GitHub safely**

Run gh auth status. The currently cached login is invalid, so use GitHub's browser/device authorization flow. The user enters credentials/2FA directly in GitHub; never request or display a password, token, private key, or recovery code.

- [ ] **Step 3: Create and publish the repository**

After checking that https://github.com/LZZ434/smartbms-rcx does not already contain unrelated work:

    gh repo create smartbms-rcx --public --source . --remote origin --push

If the repository already exists and is empty/intended for this project, add it as origin and push master. Never overwrite an unrelated remote.

- [ ] **Step 4: Verify GitHub publication and CI**

Confirm repository visibility is public, default branch points to the verified commit, source links resolve, and GitHub Actions CI is green for both Python 3.11 and 3.12. Do not proceed from a failing CI run.

- [ ] **Step 5: Deploy Streamlit Community Cloud**

Use the user's authenticated browser to deploy owner LZZ434, repository smartbms-rcx, branch master, entry point app.py, Python 3.12, no secrets, and preferred subdomain smartbms-rcx-hk. If OAuth/2FA appears, pause only for the user-controlled authentication step.

- [ ] **Step 6: Accept the public application**

Verify the confirmed HTTPS URL, health endpoint, default Chinese, English switching, all seven pages, sample data quality, downloads, mobile/narrow layout, disclosures, repository link, and no application console errors. Confirm a fresh anonymous browser can access it.

- [ ] **Step 7: Correct final links when necessary**

If the live URL differs from https://smartbms-rcx-hk.streamlit.app, patch both READMEs with the confirmed URL, run tests, commit, push, wait for CI and Streamlit redeployment, and repeat production acceptance.

- [ ] **Step 8: Final handoff**

Deliver the live URL, GitHub URL, green CI evidence, exact test count, unchanged KPI evidence, deployment sleep limitation, resume bullets, three-minute demo route, and the single authentication action the user performed. Do not claim a live BMS connection or real-building saving.
