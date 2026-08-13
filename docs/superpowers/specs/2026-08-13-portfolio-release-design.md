# SmartBMS-RCx Public Portfolio Release Design

**Date:** 2026-08-13  
**Status:** Approved in conversation  
**Release target:** Public GitHub repository and public Streamlit Community Cloud application

## 1. Goal

Turn the existing deterministic bilingual SmartBMS-RCx prototype into a recruiter-ready public engineering portfolio release. The release must add a realistic, read-only BMS trend-data quality and diagnostic-admission workflow, improve first-time demonstration clarity, automate regression verification, and provide a publicly shareable application URL.

The release must preserve the project's current strengths and verified synthetic baseline:

- two-zone RC thermal simulation;
- schedule/P-control baseline and bounded one-hour predictive supervision;
- four injected RCx fault scenarios;
- BMS point and alarm semantics;
- Chinese-default / English-switch user interface and reports;
- 844.288 kWh baseline energy, 796.814 kWh optimized energy, 5.623% simulated saving, 100% optimized occupied comfort, 4/4 detected injected faults, and 45-minute detection delay in the fixed portfolio scenario.

The additional engineering claim is deliberately narrow: the project will demonstrate how trend data is parsed, checked, qualified, and admitted to read-only diagnostic rules. It will not claim a live building connection or field validation.

## 2. Why this scope

Three upgrade paths were considered:

1. **Engineering data-readiness workflow and public release.** This is selected because it closes the largest credibility gap between a fixed simulation and BMS/RCx/Digital Solutions work.
2. **A deeper MPC or AI controller.** This could increase algorithmic complexity, but it would not have credible field calibration or validation within the release window.
3. **Visual redesign only.** This would improve presentation but add little engineering evidence.

The selected path gives interviewers a coherent end-to-end story: deterministic source data, canonical point schema, quality gates, rule-specific diagnostic eligibility, explainable findings, reproducible tests, and a live bilingual demonstration.

## 3. Public-release boundary

The repository and hosted application are public and may be indexed by search engines. Before publication, tracked files and Git history must be scanned for secrets, private identifiers, credentials, personal documents, and generated local logs.

The release uses an MIT license. The application stores no uploaded file, uses no database, has no authentication, and requires no application secret. Uploaded CSV content exists only in the active Streamlit process/session and is discarded when the session or process ends. The UI must state this behavior before the upload control.

The public app must prominently state that:

- the bundled data and verified KPI results are synthetic;
- an uploaded file is processed read-only and in memory;
- a successful diagnostic-admission result does not prove sensor calibration, field commissioning, or deployability;
- no BACnet, Modbus, MQTT, BMS write path, or cloud telemetry connection is implemented.

## 4. Architecture

### 4.1 Trend ingestion

Create `smartbms/trend_io.py` as the only boundary that turns CSV bytes or a DataFrame into a canonical trend frame.

It will:

- reject empty input and files above the application limit;
- decode UTF-8 and UTF-8-with-BOM CSV data;
- require a parseable `timestamp` column;
- preserve canonical English engineering column names;
- coerce known numeric and boolean fields without truthiness shortcuts;
- preserve input row order so timestamp-ordering defects remain observable;
- return a structured result containing the canonical frame and ingestion notices;
- raise a domain-specific, user-safe exception for unrecoverable schema or parsing failures.

The ingestion boundary must never mutate the original DataFrame supplied by a caller.

### 4.2 Data-quality model

Create `smartbms/data_quality.py` with focused immutable dataclasses:

- `QualityIssue`: stable code, severity, affected columns, affected-row count, and canonical evidence values;
- `QualityCheckResult`: check code, status, weight, and issues;
- `DiagnosticReadiness`: diagnostic category, required columns, missing columns, blocking issue codes, and eligibility;
- `DataQualityReport`: row count, inferred sampling interval, time range, transparent score, check results, and per-rule readiness.

`assess_trend_quality(frame)` will run deterministic checks:

1. timestamp parsing, ordering, duplicates, and regularity;
2. minimum history length;
3. required/core point coverage;
4. missing-value ratio by point;
5. frozen measured-temperature signals over a sustained run;
6. engineering bounds for temperatures, humidity, normalized commands/feedback, airflow, and non-negative power;
7. implausible zone-temperature rate of change;
8. cross-point consistency needed by each existing diagnostic rule.

Severity levels are `critical`, `warning`, and `info`. The displayed score is a transparent weighted pass percentage for navigation; it must not override safety logic. Diagnostic eligibility is rule-specific and is true only when:

- all columns required by that rule are present;
- timestamps and history length meet the rule's persistence needs;
- no critical issue affects a required column;
- the frame can be passed to the existing diagnostic function without inventing values.

The four readiness column groups align with the current rules:

- sensor bias: measured temperature plus an explicit reference value;
- stuck valve: cooling command and valve feedback;
- fouled filter: airflow command/feedback plus fan-power evidence;
- after-hours operation: occupancy/preconditioning state plus HVAC power.

Unknown columns are retained in normalized downloads but ignored by known quality rules. Missing columns are never synthesized.

### 4.3 Diagnostic admission

Extend `run_diagnostics` with an optional stable `categories` argument. Its default remains all four rules for backward compatibility. When categories are supplied, it validates only the union of columns needed by those rules and executes only those rules. This creates a testable admission boundary without duplicating diagnostic formulas.

Eligible uploaded or bundled data may then be passed to `run_diagnostics` one admitted category at a time in read-only mode. Ineligible rules must show the exact missing columns or blocking quality issues instead of producing a finding. The canonicalized frame retains input row order; an unsorted timestamp issue is critical and therefore blocks diagnostic execution instead of being silently repaired.

Findings from uploaded data are labeled “screening findings” / “筛查结果.” They reuse the existing explainable evidence and recommendation pipeline but include an additional disclaimer that technician review and field context are required.

The fixed synthetic scenario remains the source of portfolio KPI regression claims. Uploaded data never changes the Overview KPI cards, cached `ScenarioBundle`, or canonical generated portfolio report.

### 4.4 Streamlit presentation

Add a seventh stable page ID, `data_quality`, positioned before RCx Diagnostics. The page is fully bilingual and follows the existing translation-catalog rules.

On first load it analyzes the bundled healthy baseline trend set. The page contains:

1. synthetic/sample-data disclosure and in-memory upload privacy note;
2. download button for the canonical sample CSV;
3. optional CSV upload control;
4. source badge, row/time-span/sampling-interval cards, quality score, and overall readiness summary;
5. check-result and issue tables;
6. rule-specific RCx readiness table;
7. screening findings only for eligible rules;
8. preview of normalized data;
9. downloads for the quality report and normalized canonical CSV.

Errors are rendered as concise bilingual guidance with no raw traceback. Switching languages must retain the selected source and must not mutate or reparse the underlying canonical frame unnecessarily.

### 4.5 Recruiter demonstration layer

Improve the Overview without turning it into a marketing landing page:

- add a visible “Synthetic engineering PoC” status badge;
- add a three-step guided demo: verified scenario, data-quality gate, explainable RCx action;
- add a compact evidence panel linking test count, deterministic seed, model boundary, and public repository;
- retain the existing detailed engineering pages and download buttons;
- include release version and build commit when supplied by the hosting environment, with a safe local fallback.

The visual style remains the existing restrained engineering dashboard. No decorative animation, stock imagery, or unsupported sustainability claims are added.

## 5. Internationalization

All new page labels, help text, check names, issue messages, readiness reasons, disclosures, buttons, tables, and export labels are added to the existing English/Chinese catalog.

Stable machine contracts remain English:

- CSV column names;
- quality and issue codes;
- diagnostic category IDs;
- point IDs, BACnet object identifiers, and Modbus registers;
- JSON/CSV export field names.

Known professional abbreviations and units remain recognizable: BMS, RCx, FDD, AHU, HVAC, BACnet, Modbus, kW, kWh, and °C.

## 6. Export contracts

The data-quality page provides:

- `smartbms-sample-trends.csv`: raw bundled baseline trend data;
- `smartbms-normalized-trends.csv`: parsed canonical uploaded/sample data;
- `smartbms-data-quality-report.csv`: one row per quality check/issue with stable English field names.

Display tables are localized copies. Downloads keep canonical English schemas for engineering interoperability. Export helpers live outside `app.py` and are tested without Streamlit.

## 7. Release engineering

### 7.1 Reproducible environment

- Keep package constraints in `pyproject.toml` compatible with Python 3.11+.
- Pin the cloud runtime dependencies in `requirements.txt` to versions verified locally and in CI.
- Target Python 3.12 on Streamlit Community Cloud.
- Keep browser telemetry disabled and set a conservative upload size in `.streamlit/config.toml`.

### 7.2 Continuous integration

Add `.github/workflows/ci.yml` triggered on pushes and pull requests. The workflow runs on Python 3.11 and 3.12 and must:

1. install `requirements.txt` and the local package;
2. run the complete unittest suite;
3. run `compileall`;
4. run `pip check`;
5. generate the canonical portfolio artifacts;
6. verify the fixed KPI and diagnostic regression contracts through tests.

No credential or deployment secret is placed in the workflow.

### 7.3 Documentation and license

Update both READMEs with:

- live app and CI links;
- a 60-second quick start and three-minute recruiter demo path;
- sample/upload schema and privacy behavior;
- local and cloud execution instructions;
- exact synthetic-data and non-deployment boundaries;
- current automated-test count after implementation.

Add `LICENSE` with the MIT license and `docs/data-contract.md` describing canonical fields, rule readiness, and quality checks.

## 8. Deployment

The preferred host is Streamlit Community Cloud because it directly supports the existing Python/Streamlit architecture, deploys from GitHub, provides a shareable `streamlit.app` URL, and automatically updates from the selected branch.

Deployment coordinates:

- owner: the user's authenticated GitHub account;
- repository: `smartbms-rcx`, public;
- branch: `master` unless GitHub requires a later rename decision;
- entry point: `app.py`;
- Python: 3.12;
- secrets: none;
- preferred subdomain: `smartbms-rcx-hk` if available, otherwise the clearest available deterministic alternative.

Community Cloud inactivity sleep is accepted for this free portfolio release and must be disclosed in handoff notes. A paid always-on host is outside this release unless Community Cloud cannot run the verified application.

Publishing steps may require one user-controlled GitHub/Streamlit OAuth or two-factor-authentication interaction. The assistant may prepare and validate everything else but must not request or handle the user's password, private key, recovery code, or full access token.

## 9. Error handling and safety

- CSV parsing and schema failures produce user-safe bilingual messages.
- Oversized or empty files are rejected before analysis.
- Quality checks operate on copies and cannot alter the fixed scenario bundle.
- No uploaded data is logged, committed, persisted, or included in analytics.
- No quality failure is silently replaced with a default value.
- Diagnostic exceptions are contained at the admission boundary and reported as ineligible screening, not as an empty “healthy” result.
- Public-release scanning checks both tracked content and commit metadata available locally without printing secret values.

## 10. Testing strategy

Implementation follows red-green-refactor TDD.

Automated coverage includes:

1. valid UTF-8 and UTF-8-BOM CSV parsing;
2. empty, malformed, oversized, and missing-timestamp rejection;
3. non-mutating canonicalization and strict boolean coercion;
4. duplicate, unsorted, irregular, missing, frozen, out-of-range, and excessive-rate detection;
5. deterministic score and severity behavior;
6. all four rule-specific readiness gates;
7. diagnostics run only for eligible rules;
8. localized display copies and stable English exports;
9. all seven pages in Chinese and English through Streamlit AppTest;
10. upload errors with no Streamlit exception;
11. existing simulation, KPI, reporting, Unicode, and localization regression tests;
12. CI execution on Python 3.11 and 3.12.

Browser acceptance covers desktop and narrow viewport, both languages, sample analysis, valid upload, invalid upload, report downloads, current-page retention during language switching, application console errors, and local/cloud health endpoints.

## 11. Acceptance criteria

The release is complete only when:

- the seventh bilingual data-quality page works with bundled and uploaded data;
- every check exposes deterministic evidence and stable codes;
- each RCx rule has a correct, tested admission decision;
- malformed or insufficient data cannot produce a misleading “healthy” result;
- display localization never mutates raw/downloaded engineering schemas;
- the fixed synthetic KPI and 4/4 diagnostic baseline are unchanged;
- all automated tests, compilation, dependency, artifact, and diff checks pass freshly;
- code review has no unresolved high- or medium-priority correctness issue;
- the repository contains no detected secret or private local artifact;
- GitHub CI is green on the published commit;
- the public Streamlit URL loads, reports healthy, and passes browser acceptance;
- README links, release notes, resume bullets, and the three-minute demo script point to the verified public artifacts.

## 12. Non-goals

- live BACnet, Modbus, MQTT, OPC UA, or vendor-cloud connectivity;
- control writes, overrides, or automatic work orders;
- persistent upload storage, user accounts, databases, or analytics tracking;
- field-calibrated M&V, guaranteed saving, or commercial-building validation;
- deep learning, a full MPC solver, digital-twin calibration, or automated model training;
- hiding Community Cloud sleep behavior or presenting synthetic outcomes as measured results.
