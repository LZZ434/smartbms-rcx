# SmartBMS-RCx Trend Data Contract

## Purpose and boundary

This contract describes the read-only CSV boundary used by the Data Quality & Import page. The bundled file is deterministic synthetic data. Uploaded files are processed in memory for the active application session; the application does not persist them, connect to a live BMS, or write control values.

A passing quality check only means that a known rule has enough structurally credible data to run. It is not evidence of field calibration, commissioning, measurement and verification, or production deployment.

## CSV and timestamp

- Encoding: UTF-8 or UTF-8 with BOM.
- Maximum public-app upload: 10 MB.
- Header names: canonical English engineering identifiers.
- Required universal field: `timestamp`, parseable by pandas and ordered oldest to newest.
- Sampling: one regular interval throughout the file. The bundled sample uses 15 minutes.
- Minimum history: 16 rows, supporting four-sample persistence plus context.
- Unknown columns: preserved in the normalized export but ignored by known checks.
- Missing columns: reported; they are never synthesized.

## Typed fields

Known boolean fields are `synthetic`, `occupied`, `preconditioning_authorized`, `controller_fallback`, and `fault_active`. Accepted values are actual booleans, 0/1, or case-insensitive `true`/`false`/`yes`/`no`. Other values are rejected rather than converted by truthiness.

Known numeric fields include weather, loads, temperatures, targets, normalized commands and feedback, cooling load, fan/chiller/HVAC power, COP, and controller objective signals. Non-numeric content in a known numeric field is rejected. Context strings such as `scenario`, `strategy`, and `fault_type` are preserved.

## Quality checks

| Check code | Weight | Deterministic rule |
|---|---:|---|
| `timestamps` | 20 | Reject invalid, duplicate, unsorted, or irregular timestamps. |
| `history` | 10 | Require at least 16 rows. |
| `coverage` | 15 | List missing points required by known diagnostic rules. |
| `missing` | 15 | Report nulls per point; nulls in rule inputs are critical. |
| `frozen` | 10 | Flag measured/reference temperatures unchanged for 8 or more samples. |
| `bounds` | 15 | Check disclosed physical/normalized ranges. |
| `temperature_rate` | 10 | Flag zone/reference temperature steps above 2 °C per sample. |
| `cross_point` | 5 | Check HVAC/fan power and active-airflow/expected-fan consistency. |

The navigation score awards full check weight for `pass`, half for `warning`, and zero for `fail`. It does not override rule-admission logic.

### Engineering bounds

- outdoor temperature: -20 to 55 °C;
- zone, reference, and target temperatures: 5 to 45 °C;
- relative humidity: 0 to 100%;
- cooling commands, valve positions, and airflow command/feedback: 0 to 1;
- cooling and electrical power: non-negative;
- effective COP: 0.5 to 10.

## Rule-specific readiness

Each rule is admitted independently. A rule is eligible only if all required columns exist, global timestamp/history gates pass, and no critical issue affects its required points.

| Category | Required fields |
|---|---|
| `sensor_bias` | `timestamp`, `east_temp_measured_c`, `east_temp_reference_c` |
| `stuck_valve` | `timestamp`, `cooling_cmd_east`, `valve_east`, `east_temp_measured_c` |
| `fouled_filter` | `timestamp`, `airflow_cmd_east`, `airflow_east`, `fan_power_kw`, `expected_fan_power_kw` |
| `after_hours_operation` | `timestamp`, `occupied`, `cooling_cmd_east`, `hvac_power_kw` |

Optional `cooling_cmd_west` and `preconditioning_authorized` improve after-hours context. Their absence does not invent data: the existing rule uses its documented east-command and unauthorized-preconditioning fallback semantics.

## Export schemas

The user interface localizes display copies only. Downloads retain stable English machine contracts:

- `smartbms-sample-trends.csv`: bundled raw synthetic baseline;
- `smartbms-normalized-trends.csv`: typed canonical input, with unknown columns preserved;
- `smartbms-data-quality-report.csv`: `check_code`, `status`, `weight`, `issue_code`, `severity`, `columns`, `affected_rows`, `detail`.

Screening findings are advisory. A technician must confirm point semantics, calibration, schedules, equipment state, and corrective action before any field decision.
