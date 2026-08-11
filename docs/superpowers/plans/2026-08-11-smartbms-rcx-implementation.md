# SmartBMS-RCx Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify an offline-capable SmartBMS-RCx portfolio application that simulates a two-zone Hong Kong office HVAC system, compares baseline and predictive supervisory control, detects four RCx faults, and produces dashboard, export, learning, and resume assets.

**Architecture:** A deterministic Python domain package owns configuration, weather/load generation, plant simulation, controllers, faults, diagnostics, point metadata, metrics, and reports. A thin Streamlit app consumes those APIs. Standard-library `unittest` tests exercise each domain boundary and end-to-end scenarios; normal execution requires only NumPy, pandas, and Streamlit.

**Tech Stack:** Python 3.11+, dataclasses, NumPy, pandas, Streamlit, HTML/CSS, `unittest`, Git.

---

## File Map

- `.gitignore` — Python, environment, cache, and generated-output exclusions.
- `pyproject.toml` — package metadata and runtime dependencies.
- `requirements.txt` — simple installation entry point.
- `smartbms/__init__.py` — public package exports and version.
- `smartbms/config.py` — validated simulation, zone, and controller dataclasses.
- `smartbms/weather.py` — Hong Kong-normal-inspired synthetic weather and occupancy inputs.
- `smartbms/plant.py` — explainable two-zone RC thermal/HVAC model.
- `smartbms/controllers.py` — baseline and predictive supervisory controllers.
- `smartbms/faults.py` — deterministic fault definitions and injection.
- `smartbms/points.py` — BMS point registry, alarm evaluation, BACnet/Modbus metadata.
- `smartbms/diagnostics.py` — RCx rules, residual evidence, severity, and recommendations.
- `smartbms/metrics.py` — energy, peak, comfort, cost, runtime, and detection metrics.
- `smartbms/scenarios.py` — healthy/faulted simulation orchestration and comparisons.
- `smartbms/reporting.py` — HTML/Markdown and CSV portfolio exports.
- `app.py` — six-page Streamlit dashboard.
- `tests/` — unit and integration tests mirroring domain modules.
- `docs/architecture.md` — architecture, equations, assumptions, and references.
- `docs/case-study-en.md` — one-page English case study.
- `docs/resume-bullets.md` — truthful bilingual resume bullets.
- `docs/demo-script.md` — three-minute demonstration script.
- `docs/interview-guide.md` — interview questions and answer guidance.
- `docs/learning-plan.md` — three-week ownership plan.
- `scripts/generate_portfolio.py` — command-line generation of verified reports and CSVs.

### Task 1: Scaffold and configuration validation

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `smartbms/__init__.py`
- Create: `smartbms/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing configuration tests**

```python
class ConfigTests(unittest.TestCase):
    def test_default_config_is_valid(self):
        config = SimulationConfig()
        self.assertEqual(config.steps, 7 * 24 * 4)

    def test_invalid_timestep_is_rejected(self):
        with self.assertRaises(ValueError):
            SimulationConfig(timestep_minutes=0)
```

- [ ] **Step 2: Run the test and verify import failure**

Run: `python -m unittest tests.test_config -v`

Expected: FAIL because `smartbms.config` does not exist.

- [ ] **Step 3: Implement immutable validated dataclasses**

```python
@dataclass(frozen=True)
class SimulationConfig:
    days: int = 7
    timestep_minutes: int = 15
    start: datetime = datetime(2026, 8, 3, 0, 0)

    def __post_init__(self):
        if self.days < 1 or self.timestep_minutes <= 0:
            raise ValueError("days and timestep_minutes must be positive")

    @property
    def steps(self) -> int:
        return self.days * 24 * 60 // self.timestep_minutes
```

Add `ZoneConfig`, `PlantConfig`, `ControllerConfig`, `FaultConfig`, and `ProjectConfig` with explicit engineering-unit docstrings and range validation.

- [ ] **Step 4: Run configuration tests**

Run: `python -m unittest tests.test_config -v`

Expected: PASS.

- [ ] **Step 5: Commit scaffold and configuration**

Run: `git add .gitignore pyproject.toml requirements.txt smartbms tests/test_config.py && git commit -m "feat: scaffold SmartBMS configuration"`

### Task 2: Deterministic Hong Kong weather, solar, and occupancy inputs

**Files:**
- Create: `smartbms/weather.py`
- Create: `tests/test_weather.py`

- [ ] **Step 1: Write failing input-profile tests**

```python
class WeatherTests(unittest.TestCase):
    def test_profile_has_expected_schema_and_length(self):
        frame = generate_inputs(SimulationConfig())
        self.assertEqual(len(frame), 672)
        self.assertTrue({"timestamp", "outdoor_temp_c", "humidity_pct", "solar_w_m2", "occupancy_east", "occupancy_west"}.issubset(frame.columns))

    def test_occupied_weekday_profile_is_higher_than_night(self):
        frame = generate_inputs(SimulationConfig())
        occupied = frame[(frame.timestamp.dt.hour >= 9) & (frame.timestamp.dt.hour < 18) & (frame.timestamp.dt.dayofweek < 5)]
        night = frame[frame.timestamp.dt.hour < 5]
        self.assertGreater(occupied.occupancy_east.mean(), night.occupancy_east.mean())
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_weather -v`

Expected: FAIL because `generate_inputs` is missing.

- [ ] **Step 3: Implement explainable synthetic inputs**

```python
outdoor = 28.7 + 2.8 * np.sin(2 * np.pi * (hour - 9) / 24)
humidity = np.clip(81 - 8 * np.sin(2 * np.pi * (hour - 8) / 24), 65, 95)
solar = np.maximum(0, 650 * np.sin(np.pi * (hour - 6) / 12))
```

Use deterministic weekday occupancy ramps, east/west solar diversity, a fixed seed for small measurement noise, and source metadata citing HKO 1991–2020 August normals. Label every generated series synthetic.

- [ ] **Step 4: Run weather tests**

Run: `python -m unittest tests.test_weather -v`

Expected: PASS.

- [ ] **Step 5: Commit input generation**

Run: `git add smartbms/weather.py tests/test_weather.py && git commit -m "feat: add Hong Kong office input profiles"`

### Task 3: Explainable plant model and baseline controls

**Files:**
- Create: `smartbms/plant.py`
- Create: `smartbms/controllers.py`
- Create: `tests/test_plant.py`
- Create: `tests/test_controllers.py`

- [ ] **Step 1: Write failing thermal and controller tests**

```python
def test_cooling_command_lowers_zone_temperature(self):
    plant = TwoZonePlant(ProjectConfig())
    hot = plant.step(outdoor_temp_c=31, internal_kw=(8, 8), cooling_commands=(0, 0), airflow_commands=(0.2, 0.2))
    cooled = plant.step(outdoor_temp_c=31, internal_kw=(8, 8), cooling_commands=(1, 1), airflow_commands=(1, 1))
    self.assertLess(cooled.zone_east_temp_c, hot.zone_east_temp_c)

def test_baseline_controller_respects_bounds(self):
    action = BaselineController(ControllerConfig()).act(ZoneObservation(27, 27, True, 31, 10))
    self.assertTrue(0 <= action.cooling_east <= 1)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_plant tests.test_controllers -v`

Expected: FAIL because plant and controller APIs are absent.

- [ ] **Step 3: Implement plant state and energy equations**

```python
dtemp = dt_hours / capacitance_kwh_per_c * (
    (outdoor_temp_c - zone_temp_c) / resistance_c_per_kw
    + internal_gain_kw
    + solar_gain_kw
    - delivered_cooling_kw
)
fan_kw = rated_fan_kw * max(min_airflow, airflow_fraction) ** 3
chiller_kw = delivered_cooling_kw / max(min_cop, cop)
```

Return a typed `PlantSnapshot` with zone temperatures, cooling delivery, fan/chiller powers, airflow, valve positions, and total HVAC power.

- [ ] **Step 4: Implement baseline controller**

Use occupied setpoint 24°C, unoccupied setback 28°C, proportional cooling, minimum occupied ventilation, and complete output clamping.

- [ ] **Step 5: Run plant/controller tests**

Run: `python -m unittest tests.test_plant tests.test_controllers -v`

Expected: PASS.

- [ ] **Step 6: Commit plant and baseline controller**

Run: `git add smartbms/plant.py smartbms/controllers.py tests/test_plant.py tests/test_controllers.py && git commit -m "feat: simulate HVAC plant and baseline control"`

### Task 4: Predictive supervisory energy optimization

**Files:**
- Modify: `smartbms/controllers.py`
- Create: `tests/test_optimizer.py`

- [ ] **Step 1: Write failing optimizer tests**

```python
class OptimizerTests(unittest.TestCase):
    def test_predictive_controller_uses_pre_cooling(self):
        controller = PredictiveController(ControllerConfig())
        action = controller.act(ZoneObservation(27, 27, False, 31, 8), occupancy_next_hour=0.9)
        self.assertGreater(action.cooling_east, 0)

    def test_optimizer_actions_stay_bounded(self):
        action = PredictiveController(ControllerConfig()).act(ZoneObservation(35, 35, True, 36, 14), occupancy_next_hour=1)
        self.assertTrue(0 <= action.cooling_west <= 1)
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m unittest tests.test_optimizer -v`

Expected: FAIL because `PredictiveController` is absent.

- [ ] **Step 3: Implement bounded candidate search**

Evaluate candidate comfort setpoints and cooling actions using one-hour thermal predictions:

```python
score = energy_weight * predicted_kwh + peak_weight * max(0, predicted_kw - peak_target_kw) ** 2 + comfort_weight * comfort_violation ** 2
```

Use weather, current zone state, current occupancy, and next-hour occupancy. On invalid inputs, return a baseline action and record `fallback_used=True`.

- [ ] **Step 4: Run optimizer tests**

Run: `python -m unittest tests.test_optimizer -v`

Expected: PASS.

- [ ] **Step 5: Commit predictive controller**

Run: `git add smartbms/controllers.py tests/test_optimizer.py && git commit -m "feat: add predictive HVAC optimization"`

### Task 5: Fault injection and BMS point/alarm semantics

**Files:**
- Create: `smartbms/faults.py`
- Create: `smartbms/points.py`
- Create: `tests/test_faults.py`
- Create: `tests/test_points.py`

- [ ] **Step 1: Write failing fault and point tests**

```python
def test_sensor_bias_changes_measured_not_true_temperature(self):
    result = apply_fault(FaultType.SENSOR_BIAS, true_temp_c=24, command=0.5, airflow=0.7, power_kw=3)
    self.assertEqual(result.true_temp_c, 24)
    self.assertGreater(result.measured_temp_c, 24)

def test_point_registry_has_protocol_metadata(self):
    points = build_point_registry()
    zone_temp = next(p for p in points if p.point_id == "ZN-E-T")
    self.assertEqual(zone_temp.bacnet_object_type, "analog-input")
    self.assertIsNotNone(zone_temp.modbus_register)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_faults tests.test_points -v`

Expected: FAIL because fault and point modules are absent.

- [ ] **Step 3: Implement four deterministic faults**

Implement sensor bias, stuck valve, fouled filter, and after-hours command override with explicit active windows and labels.

- [ ] **Step 4: Implement point registry and alarms**

Use a frozen `BMSPoint` dataclass. Alarm evaluation returns structured `AlarmEvent` values with timestamp, point, priority, observed value, limit, and message.

- [ ] **Step 5: Run fault/point tests**

Run: `python -m unittest tests.test_faults tests.test_points -v`

Expected: PASS.

- [ ] **Step 6: Commit faults and point model**

Run: `git add smartbms/faults.py smartbms/points.py tests/test_faults.py tests/test_points.py && git commit -m "feat: model BMS points alarms and faults"`

### Task 6: RCx diagnostics and evidence

**Files:**
- Create: `smartbms/diagnostics.py`
- Create: `tests/test_diagnostics.py`

- [ ] **Step 1: Write failing diagnostic tests**

```python
def test_after_hours_rule_returns_actionable_finding(self):
    trends = fixture_after_hours_operation()
    findings = run_diagnostics(trends)
    finding = next(item for item in findings if item.category == "after_hours_operation")
    self.assertIn("schedule", finding.recommendation.lower())
    self.assertGreater(finding.estimated_waste_kwh, 0)
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m unittest tests.test_diagnostics -v`

Expected: FAIL because diagnostics are absent.

- [ ] **Step 3: Implement rules and model residuals**

Use rolling persistence to avoid single-sample alarms. Findings cover:

```python
categories = {
    "sensor_bias": "Compare measured temperature against model/reference residual",
    "stuck_valve": "Detect command/position mismatch with inadequate cooling response",
    "fouled_filter": "Detect fan-power/airflow ratio deterioration",
    "after_hours_operation": "Detect HVAC power and command while unoccupied",
}
```

Each `DiagnosticFinding` includes evidence columns, detection timestamp, severity, estimated impact, and corrective recommendation.

- [ ] **Step 4: Run diagnostic tests**

Run: `python -m unittest tests.test_diagnostics -v`

Expected: PASS.

- [ ] **Step 5: Commit RCx diagnostics**

Run: `git add smartbms/diagnostics.py tests/test_diagnostics.py && git commit -m "feat: add RCx fault diagnostics"`

### Task 7: Scenario orchestration and verified metrics

**Files:**
- Create: `smartbms/metrics.py`
- Create: `smartbms/scenarios.py`
- Create: `tests/test_metrics.py`
- Create: `tests/test_scenarios.py`

- [ ] **Step 1: Write failing metric and end-to-end tests**

```python
def test_metric_summary_matches_trend_energy(self):
    summary = calculate_metrics(sample_trends(), timestep_minutes=15)
    expected = sample_trends().hvac_power_kw.sum() * 0.25
    self.assertAlmostEqual(summary.energy_kwh, expected)

def test_bundle_contains_baseline_optimized_and_four_faults(self):
    bundle = run_portfolio_scenarios(ProjectConfig())
    self.assertEqual(set(bundle.fault_runs), {"sensor_bias", "stuck_valve", "fouled_filter", "after_hours_operation"})
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_metrics tests.test_scenarios -v`

Expected: FAIL because metric and orchestration modules are absent.

- [ ] **Step 3: Implement metrics**

Calculate energy, peak demand, occupied degree-hours outside 22–26°C, runtime, synthetic cost with documented rates, percentage differences, diagnostic precision/recall, and detection delay.

- [ ] **Step 4: Implement scenario runner**

Create a fresh plant/controller for every run, produce a stable DataFrame schema, inject fault labels, run diagnostics, and return `ScenarioBundle` containing trends, summaries, alarms, findings, and comparison rows.

- [ ] **Step 5: Run metrics/scenario tests**

Run: `python -m unittest tests.test_metrics tests.test_scenarios -v`

Expected: PASS and measured optimization outcome visible in verbose output.

- [ ] **Step 6: Commit scenarios and metrics**

Run: `git add smartbms/metrics.py smartbms/scenarios.py tests/test_metrics.py tests/test_scenarios.py && git commit -m "feat: run verified SmartBMS scenarios"`

### Task 8: Reports and exports

**Files:**
- Create: `smartbms/reporting.py`
- Create: `scripts/generate_portfolio.py`
- Create: `tests/test_reporting.py`

- [ ] **Step 1: Write failing report/export test**

```python
def test_portfolio_export_writes_expected_files(self):
    with tempfile.TemporaryDirectory() as directory:
        paths = export_portfolio(run_portfolio_scenarios(ProjectConfig()), Path(directory))
        self.assertTrue((Path(directory) / "rcx-report.html").exists())
        self.assertTrue((Path(directory) / "scenario-comparison.csv").exists())
        self.assertIn("trends-baseline.csv", {path.name for path in paths})
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m unittest tests.test_reporting -v`

Expected: FAIL because report generation is absent.

- [ ] **Step 3: Implement safe deterministic exports**

Generate HTML using escaped values and a self-contained CSS block. Export baseline/optimized trends, comparison metrics, points, alarms, and diagnostic findings as CSV. Include source/assumption disclosures in the report.

- [ ] **Step 4: Run reporting test and CLI**

Run: `python -m unittest tests.test_reporting -v`

Expected: PASS.

Run: `python scripts/generate_portfolio.py --output generated`

Expected: report and CSV paths printed; exit code 0.

- [ ] **Step 5: Commit reporting**

Run: `git add smartbms/reporting.py scripts/generate_portfolio.py tests/test_reporting.py && git commit -m "feat: export RCx portfolio reports"`

### Task 9: Streamlit dashboard

**Files:**
- Create: `app.py`
- Create: `.streamlit/config.toml`
- Create: `tests/test_app_smoke.py`

- [ ] **Step 1: Write failing import smoke test**

```python
def test_dashboard_module_imports(self):
    module = importlib.import_module("app")
    self.assertTrue(callable(module.main))
```

- [ ] **Step 2: Run smoke test and verify failure**

Run: `python -m unittest tests.test_app_smoke -v`

Expected: FAIL because `app.py` is absent.

- [ ] **Step 3: Implement a thin six-page dashboard**

Cache `run_portfolio_scenarios`, use sidebar navigation, show KPI cards, native Streamlit line charts, comparison tables, fault evidence, point registry, downloadable exports, and guided Learning Lab experiments. All engineering results must come from `smartbms` APIs.

- [ ] **Step 4: Run import and headless startup checks**

Run: `python -m unittest tests.test_app_smoke -v`

Expected: PASS.

Run: `python -m streamlit run app.py --server.headless true --server.port 8501`

Expected: local URL displayed with no startup traceback; terminate after the health check.

- [ ] **Step 5: Commit dashboard**

Run: `git add app.py .streamlit/config.toml tests/test_app_smoke.py && git commit -m "feat: add SmartBMS Streamlit dashboard"`

### Task 10: Portfolio documentation and learning assets

**Files:**
- Create: `README.md`
- Create: `README.zh-CN.md`
- Create: `docs/architecture.md`
- Create: `docs/case-study-en.md`
- Create: `docs/resume-bullets.md`
- Create: `docs/demo-script.md`
- Create: `docs/interview-guide.md`
- Create: `docs/learning-plan.md`

- [ ] **Step 1: Generate verified metrics before writing claims**

Run: `python scripts/generate_portfolio.py --output generated`

Expected: exit code 0 with actual baseline/optimized metrics.

- [ ] **Step 2: Write bilingual usage and disclosure documentation**

Document installation, one-command test/run/export commands, equations, source references, synthetic-data labels, screenshots instructions, troubleshooting, and exact measured results from the verified scenario.

- [ ] **Step 3: Write interview and ownership materials**

Include the five required experiments, 20 questions covering plant physics/control/RCx/BMS/protocols/metrics, a three-week schedule, and a three-minute demo script. Resume bullets must say “simulated” or “proof of concept” and quote only verified measurements.

- [ ] **Step 4: Scan documentation for unsupported claims**

Run: `rg -n "real building|deployed|production|guaranteed|TBD|TODO|FIXME" README* docs -g "*.md"`

Expected: no misleading claim or unfinished placeholder; legitimate non-goal uses are manually reviewed.

- [ ] **Step 5: Commit documentation**

Run: `git add README.md README.zh-CN.md docs && git commit -m "docs: add SmartBMS portfolio and learning guide"`

### Task 11: Full verification and final clean state

**Files:**
- Modify only files implicated by verification failures.

- [ ] **Step 1: Run complete test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 2: Regenerate the portfolio artifacts**

Run: `python scripts/generate_portfolio.py --output generated`

Expected: HTML and CSV artifacts generated without warnings or traceback.

- [ ] **Step 3: Start dashboard and perform HTTP health check**

Run the Streamlit server on localhost and request `http://localhost:8501/_stcore/health`.

Expected: HTTP 200 and body `ok`.

- [ ] **Step 4: Inspect measured outcomes and repository status**

Run: `git status --short` and inspect the generated comparison CSV.

Expected: only intentionally ignored generated artifacts; optimization claims exactly match CSV values.

- [ ] **Step 5: Commit verification fixes if any**

Run: `git add <verified-project-files> && git commit -m "test: verify SmartBMS portfolio"`

Expected: no commit is created when no tracked changes are required.
