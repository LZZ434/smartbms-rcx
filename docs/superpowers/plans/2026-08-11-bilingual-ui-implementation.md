# SmartBMS-RCx Bilingual Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete Chinese/English switch to the six-page SmartBMS-RCx dashboard, default the app to Chinese, and make dashboard-downloaded HTML/Markdown reports follow the active language without changing any engineering results.

**Architecture:** Add a focused `smartbms/i18n.py` presentation adapter containing validated translation catalogs, stable page IDs, domain-label mappings, and display-only DataFrame/finding localization. Keep scenario objects and CSV schemas canonical, pass the active language into the existing renderers, and make report renderers language-aware while retaining English API defaults.

**Tech Stack:** Python 3.14, Streamlit 1.61, pandas 3, standard-library `unittest`, Streamlit `AppTest`, HTML/Markdown string rendering.

---

## File map

- Create `smartbms/i18n.py`: translation catalog, language validation, page/domain labels, dynamic diagnostic/alarm localization, display-frame localization, day formatting.
- Create `tests/test_i18n.py`: catalog, page-label, domain-text, mutation-safety, and Unicode tests.
- Modify `app.py`: stable page IDs, default-Chinese selector, language-aware page renderers and downloads.
- Modify `smartbms/reporting.py`: language-aware HTML/Markdown renderers and localized report tables.
- Modify `tests/test_app_smoke.py`: source/default-language regression tests and two-language six-page `AppTest` coverage.
- Modify `tests/test_reporting.py`: English/Chinese report content and metric-preservation tests.
- Modify `smartbms/points.py`: repair the corrupted degree symbol in point units only; no point schema or alarm rule changes.
- Modify `README.md` and `README.zh-CN.md`: document the language selector and bilingual report behavior.

### Task 1: Translation core and stable navigation IDs

**Files:**
- Create: `smartbms/i18n.py`
- Create: `tests/test_i18n.py`

- [ ] **Step 1: Write failing catalog and navigation tests**

Create `tests/test_i18n.py` with these first tests:

```python
import unittest

from smartbms.i18n import (
    LANGUAGE_NAMES,
    PAGE_IDS,
    TRANSLATIONS,
    page_label,
    t,
)


class TranslationCoreTests(unittest.TestCase):
    def test_catalogs_have_identical_keys_and_matching_placeholders(self):
        self.assertEqual(set(TRANSLATIONS["zh"]), set(TRANSLATIONS["en"]))
        for key in TRANSLATIONS["en"]:
            self.assertNotEqual(TRANSLATIONS["zh"][key], "")
            self.assertNotEqual(TRANSLATIONS["en"][key], "")

    def test_unsupported_language_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported language"):
            t("fr", "app.title")

    def test_page_labels_are_unique_in_both_languages(self):
        self.assertEqual(len(PAGE_IDS), 6)
        for language in LANGUAGE_NAMES:
            labels = [page_label(page_id, language) for page_id in PAGE_IDS]
            self.assertEqual(len(set(labels)), 6)
        self.assertEqual(page_label("overview", "zh"), "项目概览")
        self.assertEqual(page_label("overview", "en"), "Overview")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_i18n -v
```

Expected: import failure for `smartbms.i18n`, proving the new boundary does not yet exist.

- [ ] **Step 3: Implement the translation boundary**

Create `smartbms/i18n.py` with:

```python
from __future__ import annotations

from string import Formatter
from typing import Any, Literal

Language = Literal["zh", "en"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("zh", "en")
LANGUAGE_NAMES: dict[Language, str] = {"zh": "中文", "en": "English"}
PAGE_IDS = (
    "overview",
    "plant_control",
    "energy_optimization",
    "rcx_diagnostics",
    "bms_points_alarms",
    "learning_lab",
)

TRANSLATIONS: dict[Language, dict[str, str]] = {
    "en": {
        "app.title": "SmartBMS-RCx",
        "page.overview": "Overview",
        "page.plant_control": "Plant & Control",
        "page.energy_optimization": "Energy Optimization",
        "page.rcx_diagnostics": "RCx Diagnostics",
        "page.bms_points_alarms": "BMS Points & Alarms",
        "page.learning_lab": "Learning Lab",
    },
    "zh": {
        "app.title": "SmartBMS-RCx",
        "page.overview": "项目概览",
        "page.plant_control": "设备与控制",
        "page.energy_optimization": "能源优化",
        "page.rcx_diagnostics": "再调试（RCx）诊断",
        "page.bms_points_alarms": "BMS 点表与报警",
        "page.learning_lab": "学习实验室",
    },
}


def _validate_language(language: str) -> Language:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    return language  # type: ignore[return-value]


def _placeholders(value: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(value)
        if field_name is not None
    }


def validate_catalogs() -> None:
    if set(TRANSLATIONS["zh"]) != set(TRANSLATIONS["en"]):
        raise ValueError("translation catalogs must contain identical keys")
    for key in TRANSLATIONS["en"]:
        if _placeholders(TRANSLATIONS["zh"][key]) != _placeholders(
            TRANSLATIONS["en"][key]
        ):
            raise ValueError(f"translation placeholders differ for {key}")


def t(language: str, key: str, **values: Any) -> str:
    selected = _validate_language(language)
    try:
        template = TRANSLATIONS[selected][key]
    except KeyError as exc:
        raise KeyError(f"missing translation key: {key}") from exc
    return template.format(**values)


def page_label(page_id: str, language: str) -> str:
    if page_id not in PAGE_IDS:
        raise ValueError(f"unsupported page: {page_id}")
    return t(language, f"page.{page_id}")


validate_catalogs()
```

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run the same unittest command. Expected: three tests pass.

- [ ] **Step 5: Commit the translation core**

```powershell
git add smartbms\i18n.py tests\test_i18n.py
git commit -m "feat: add bilingual translation core"
```

### Task 2: Engineering-domain and display-frame localization

**Files:**
- Modify: `smartbms/i18n.py`
- Modify: `tests/test_i18n.py`

- [ ] **Step 1: Add failing tests for diagnostics, alarms, frames, and dates**

Add tests that use real scenario output:

```python
import re

from smartbms.i18n import (
    format_day,
    localize_alarm_message,
    localize_findings_frame,
    localize_frame,
)
from smartbms.scenarios import run_portfolio_scenarios


class DomainLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = run_portfolio_scenarios()

    def test_all_four_findings_localize_without_losing_numbers(self):
        for category, run in self.bundle.fault_runs.items():
            finding = next(item for item in run.findings if item.category == category)
            frame = localize_findings_frame([finding], "zh")
            rendered = " ".join(str(value) for value in frame.iloc[0])
            self.assertIn("建议措施", frame.columns)
            self.assertNotIn(finding.recommendation, rendered)
            for number in re.findall(r"[-+]?\d+(?:\.\d+)?", finding.evidence):
                self.assertIn(number, rendered)

    def test_display_frame_is_localized_without_mutating_source(self):
        source = self.bundle.comparison.copy(deep=True)
        localized = localize_frame(source, "zh")
        self.assertIn("场景", localized.columns)
        self.assertEqual(localized.iloc[0]["场景"], "基线控制")
        self.assertEqual(list(source.columns), list(self.bundle.comparison.columns))
        self.assertEqual(source.iloc[0]["scenario"], "baseline")

    def test_known_alarm_messages_and_day_labels_are_bilingual(self):
        self.assertEqual(
            localize_alarm_message("High zone temperature", "zh"),
            "区域温度过高",
        )
        day = self.bundle.baseline.trends.timestamp.dt.date.iloc[0]
        self.assertRegex(format_day(day, "zh"), r"\d+月\d+日")
        self.assertIn(day.strftime("%b"), format_day(day, "en"))
```

- [ ] **Step 2: Run only the new domain tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_i18n.DomainLocalizationTests -v
```

Expected: imports fail for the not-yet-implemented localization functions.

- [ ] **Step 3: Add the complete domain maps and adapters**

Extend `smartbms/i18n.py` with explicit maps for:

```python
SCENARIO_LABELS = {
    "baseline": {"en": "Baseline control", "zh": "基线控制"},
    "optimized": {"en": "Optimized control", "zh": "优化控制"},
}
FAULT_LABELS = {
    "sensor_bias": {"en": "Sensor bias", "zh": "传感器偏置"},
    "stuck_valve": {"en": "Stuck valve", "zh": "阀门卡滞"},
    "fouled_filter": {"en": "Fouled filter", "zh": "过滤器堵塞"},
    "after_hours_operation": {"en": "After-hours operation", "zh": "非工作时段运行"},
}
SEVERITY_LABELS = {
    "low": {"en": "Low", "zh": "低"},
    "medium": {"en": "Medium", "zh": "中"},
    "high": {"en": "High", "zh": "高"},
}
ALARM_MESSAGES_ZH = {
    "High zone temperature": "区域温度过高",
    "Low zone temperature": "区域温度过低",
    "HVAC power detected while building is unoccupied": "建筑无人时检测到 HVAC 用电",
    "East valve feedback does not follow command": "东区阀门反馈未跟随控制指令",
    "East airflow is low relative to command": "东区实际风量低于控制指令",
}
```

Add `FINDING_TITLES_ZH`, `FINDING_RECOMMENDATIONS_ZH`, and four Chinese evidence templates keyed by the canonical fault category. Implement:

```python
def domain_label(mapping, value: str, language: str) -> str:
    selected = _validate_language(language)
    return mapping.get(value, {}).get(selected, value)


def localize_alarm_message(message: str, language: str) -> str:
    selected = _validate_language(language)
    return ALARM_MESSAGES_ZH.get(message, message) if selected == "zh" else message


def localize_evidence(category: str, evidence: str, language: str) -> str:
    selected = _validate_language(language)
    if selected == "en":
        return evidence
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", evidence)
    templates = {
        "sensor_bias": "测量值与参考值的平均偏差为 {0} °C",
        "stuck_valve": "阀门反馈持续比控制指令低 {0}",
        "fouled_filter": "风量/指令比平均为 {0}，同时风机功率高于期望值",
        "after_hours_operation": "检测到 {0} 个无人时段样本的 HVAC 功率高于 {1} kW",
    }
    template = templates.get(category)
    if template is None or len(numbers) < template.count("{"):
        return evidence
    return template.format(*numbers)
```

Implement `localize_findings_frame`, `localize_frame`, and `format_day` as copy-only presentation adapters. `localize_frame` must translate known columns through a complete `COLUMN_LABELS_ZH` map and translate known `scenario`, `expected_fault`, `category`, `severity`, `detected`, `writable`, `description`, and `message` values before renaming columns.

- [ ] **Step 4: Run domain tests and the existing scenario/diagnostic tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_i18n tests.test_diagnostics tests.test_scenarios -v
```

Expected: all selected tests pass; scenario KPIs are unchanged.

- [ ] **Step 5: Commit domain localization**

```powershell
git add smartbms\i18n.py tests\test_i18n.py
git commit -m "feat: localize SmartBMS engineering displays"
```

### Task 3: Bilingual HTML and Markdown reports

**Files:**
- Modify: `smartbms/reporting.py`
- Modify: `tests/test_reporting.py`

- [ ] **Step 1: Write failing bilingual-report tests**

Add imports for `render_html_report` and `render_markdown_report`, then add:

```python
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
```

- [ ] **Step 2: Run the reporting tests and confirm RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_reporting.PortfolioReportingTests.test_dashboard_reports_render_in_both_languages_without_metric_drift tests.test_reporting.PortfolioReportingTests.test_report_rejects_unsupported_language -v
```

Expected: `language` is not accepted yet.

- [ ] **Step 3: Make report renderers language-aware**

Change signatures to:

```python
def render_html_report(bundle: ScenarioBundle, language: str = "en") -> str:
def render_markdown_report(bundle: ScenarioBundle, language: str = "en") -> str:
```

Validate language through `t(language, "report.title")`. Use localized display copies for scenario, scorecard, and findings tables. Keep the HTML layout shared, but resolve the document language, title, disclosure, KPI labels, section headings, explanatory paragraphs, model-boundary bullets, references, and footer from translation keys. Keep `export_portfolio` unchanged so its calls continue to generate the canonical English `rcx-report.html` and `rcx-report.md`.

For Chinese HTML use `lang="zh-CN"`; for English use `lang="en"`. Ensure all interpolation values come from the unchanged bundle.

- [ ] **Step 4: Run all reporting tests and confirm GREEN**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_reporting -v
```

Expected: existing English export tests and new bilingual tests all pass.

- [ ] **Step 5: Commit bilingual reports**

```powershell
git add smartbms\reporting.py tests\test_reporting.py smartbms\i18n.py
git commit -m "feat: render SmartBMS reports bilingually"
```

### Task 4: Default-Chinese shell and localized Overview / Plant pages

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app_smoke.py`

- [ ] **Step 1: Write failing default-language and navigation tests**

Replace the old `PAGE_NAMES` assertions with stable IDs and add source/default tests:

```python
from streamlit.testing.v1 import AppTest


def test_dashboard_exposes_six_stable_page_ids(self):
    module = importlib.import_module("app")
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

def test_dashboard_defaults_to_chinese(self):
    app = AppTest.from_file("app.py", default_timeout=30).run()
    self.assertFalse(app.exception)
    self.assertEqual(app.radio[0].value, "zh")
    self.assertEqual(app.title[0].value, "SmartBMS-RCx")
    self.assertTrue(any("项目概览" in item.value for item in app.radio))
```

- [ ] **Step 2: Run focused AppTest and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_app_smoke.DashboardSmokeTests.test_dashboard_exposes_six_stable_page_ids tests.test_app_smoke.DashboardSmokeTests.test_dashboard_defaults_to_chinese -v
```

Expected: `PAGE_IDS`/language radio do not exist.

- [ ] **Step 3: Implement the bilingual shell**

Import `LANGUAGE_NAMES`, `PAGE_IDS`, `format_day`, `localize_frame`, `page_label`, and `t`. Change the cache decorator to `show_spinner=False`. In `main()`:

```python
language = st.sidebar.radio(
    "语言 / Language",
    tuple(LANGUAGE_NAMES),
    index=0,
    format_func=LANGUAGE_NAMES.__getitem__,
    key="language",
)
page_id = st.sidebar.radio(
    t(language, "sidebar.navigate"),
    PAGE_IDS,
    format_func=lambda value: page_label(value, language),
    key="page_id",
)
with st.spinner(t(language, "app.loading")):
    bundle = load_bundle()
renderers[page_id](bundle, language)
```

Use stable renderer keys. Add explicit widget keys for scenario/day controls so labels changing language do not change widget identity. Localize every visible string in `render_overview` and `render_plant_control`, including selected scenario labels, day format, metrics, equations caption, report button labels, and report filenames (`-zh`/`-en`).

- [ ] **Step 4: Run focused AppTest and full existing app smoke tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_app_smoke -v
```

Expected: shell/default tests pass and no Streamlit exception appears.

- [ ] **Step 5: Commit the shell and first two pages**

```powershell
git add app.py tests\test_app_smoke.py smartbms\i18n.py
git commit -m "feat: default SmartBMS dashboard to Chinese"
```

### Task 5: Localize Optimization, RCx, Points/Alarms, and Learning pages

**Files:**
- Modify: `app.py`
- Modify: `smartbms/i18n.py`
- Modify: `tests/test_app_smoke.py`

- [ ] **Step 1: Write failing two-language six-page rendering tests**

Add a helper that selects language and page by stable values, then assert each page renders language-specific text:

```python
def _run_page(language: str, page_id: str):
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.radio(key="language").set_value(language).run()
    app.radio(key="page_id").set_value(page_id).run()
    return app

def test_all_six_pages_render_in_chinese_and_english(self):
    expected = {
        "overview": {"zh": "项目概览", "en": "Overview"},
        "plant_control": {"zh": "设备与控制", "en": "Plant & Control"},
        "energy_optimization": {"zh": "能源优化", "en": "Energy Optimization"},
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

def test_chinese_rcx_page_localizes_action_and_table(self):
    app = _run_page("zh", "rcx_diagnostics")
    self.assertTrue(any("建议措施" in item.value for item in app.success))
    self.assertIn("预期故障", app.dataframe[0].value.columns)
    self.assertIn("建议措施", app.dataframe[1].value.columns)

def test_report_download_names_follow_the_selected_language(self):
    chinese = _run_page("zh", "overview")
    english = _run_page("en", "overview")
    self.assertEqual(
        {button.file_name for button in chinese.download_button},
        {"smartbms-rcx-report-zh.html", "smartbms-rcx-report-zh.md"},
    )
    self.assertEqual(
        {button.file_name for button in english.download_button},
        {"smartbms-rcx-report-en.html", "smartbms-rcx-report-en.md"},
    )
```

- [ ] **Step 2: Run the new page tests and confirm RED**

Run the two new test methods. Expected: untranslated titles/content fail for the four remaining pages.

- [ ] **Step 3: Localize the four remaining renderers**

Move every visible literal into `TRANSLATIONS`, including:

- optimization table labels, chart headings, explanation, and CSV-download button;
- RCx scorecard/finding table, fault selector, severity/confidence/impact, recommendation, evidence heading, and timestamps;
- points/alarm headers, filters, descriptions, table labels, messages, and downloads;
- five learning experiments, blind evidence-set labels, signal selector, hypothesis prompt, reveal button, and localized revealed answer.

Use `localize_frame` for comparison/scorecard/point/alarm display copies and `localize_findings_frame` for findings. Do not pass localized DataFrames into calculations or CSV downloads. Keep raw engineering signal names in chart legends and CSVs.

- [ ] **Step 4: Run the two-language AppTest suite and all i18n tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_app_smoke tests.test_i18n -v
```

Expected: all six pages pass in both languages and localized diagnostic assertions pass.

- [ ] **Step 5: Commit the remaining pages**

```powershell
git add app.py smartbms\i18n.py tests\test_app_smoke.py
git commit -m "feat: localize all SmartBMS dashboard pages"
```

### Task 6: Unicode cleanup, documentation, and final acceptance

**Files:**
- Modify: `app.py`
- Modify: `smartbms/reporting.py`
- Modify: `smartbms/points.py`
- Modify: `tests/test_app_smoke.py`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Add a failing mojibake regression test**

Add:

```python
def test_user_facing_sources_have_no_known_mojibake(self):
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in ("app.py", "smartbms/reporting.py", "smartbms/points.py")
    )
    for broken in ("鈥", "掳", "馃", "脳", "危", "茅", "攏"):
        self.assertNotIn(broken, sources)
```

- [ ] **Step 2: Run the mojibake test and confirm RED**

Expected: it reports the known corrupted sequences in current user-facing source.

- [ ] **Step 3: Replace broken Unicode and update usage docs**

Replace presentation mojibake with correct UTF-8 punctuation/symbols (`°C`, `–`, `→`, `×`, `Σ`, `🏢`) while leaving calculations unchanged. Add bilingual-selector instructions and the two language-specific report filenames to both READMEs. Update documented automated-test count after the final suite establishes the exact number.

- [ ] **Step 4: Run complete automated and artifact verification**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q smartbms app.py scripts tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
git diff --check
```

Assert the generated comparison remains baseline `844.288`, optimized `796.814`, savings `5.623%`; scorecard remains 4/4 and 45 minutes; canonical generated reports remain English.

- [ ] **Step 5: Run browser acceptance**

Start the feature app on an unused local port. In a real browser verify default Chinese, all six Chinese pages, switch to English, all six English pages, switch back to Chinese, localized RCx evidence/action, both report downloads, no console application errors, and `/_stcore/health` returns `200 / ok`. Stop only the server process started for this verification.

- [ ] **Step 6: Commit the final cleanup**

```powershell
git add app.py smartbms\reporting.py smartbms\points.py tests\test_app_smoke.py README.md README.zh-CN.md
git commit -m "test: verify bilingual SmartBMS experience"
```

- [ ] **Step 7: Review and integrate**

Run the code-quality review against `master...HEAD`, fix any P1/P2 findings with a failing regression test first, rerun the complete verification, merge the feature branch locally into `master`, rerun all tests on merged `master`, remove the temporary worktree, and delete the merged branch. Do not push or deploy.
