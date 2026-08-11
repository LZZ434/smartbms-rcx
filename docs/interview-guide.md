# Interview Guide: 24 Questions You Must Own

The short answers below are starting points, not scripts to memorize. For each question, first answer aloud without looking, then compare, run the relevant code, and improve your answer.

## Plant physics and energy

### 1. What does the RC model represent?

`R` represents resistance to heat transfer between the zone and outdoors in °C/kW. `C` represents stored thermal energy per degree of zone-temperature change in kWh/°C. The model sums envelope heat, internal gains, solar gains, and cooling over the timestep to update temperature.

### 2. Check the units in the temperature equation.

Every term inside the brackets is kW. Multiplying by `Δt` in hours produces kWh. Dividing by `C` in kWh/°C produces °C, which can be added to the current zone temperature.

### 3. Why is fan power cubic in airflow?

For geometrically similar fan operation, flow is proportional to speed, pressure roughly to speed squared, and power to speed cubed. The model uses that affinity-law relationship to show why reducing airflow can materially reduce variable fan power. Real systems have static-pressure reset, efficiency curves, minimum speed, and system effects that this simple equation omits.

### 4. How is chiller power modeled?

Delivered cooling from both zones is divided by an effective COP. COP is nominally 3.6 and slightly derated at high outdoor temperature. It does not model chilled-water temperatures, part-load curves, pumps, towers, or staging.

### 5. Why are east and west zones different?

They use slightly different occupancy/internal loads and orientation factors. East gains more morning solar; west gains more afternoon solar. This creates a meaningful multi-zone control and diagnostic example without pretending to model a full floor.

## Controls

### 6. How does the baseline controller work?

It selects a 24 °C occupied target or 28 °C unoccupied setback, applies proportional cooling based on measured temperature error, imposes minimum airflow, and clamps every output to `[0, 1]`. It is reactive and has no future information.

### 7. What is the predictive controller actually doing?

It evaluates a small set of candidate targets using current state plus one-hour outdoor-temperature and occupancy forecasts. It estimates power and future comfort, scores each candidate with energy, peak, and comfort terms, and selects the lowest score. Invalid data triggers a sanitized baseline fallback.

### 8. Why should you not call it full MPC?

It has an internal prediction and objective, but it does not solve a formal multi-step constrained optimization over a control sequence, has no state estimator, and uses a small hand-defined candidate set. “Bounded predictive candidate search” is accurate.

### 9. Why does optimized comfort outperform the baseline even though it saves energy?

The baseline waits until the occupied schedule begins, so thermal inertia creates a morning comfort gap. The predictive strategy sees near-future occupancy and authorizes pre-cooling, then relaxes unnecessary unoccupied operation. It shifts when energy is used rather than simply reducing all cooling.

### 10. Why is peak reduction only 0.745%?

Pre-cooling and the required cooling capacity still create a high morning demand. The objective weights energy and comfort more strongly than peak shaving, and the candidate space is limited. A higher peak penalty, longer horizon, thermal-storage strategy, or explicit demand constraint could improve peak reduction, possibly at an energy or comfort cost.

### 11. What happens when a sensor value is NaN?

The predictive controller rejects non-finite observations or forecasts. It replaces unsafe values with conservative setpoint-based values, invokes the baseline controller, and marks the action `predictive-fallback` with `fallback_used=True` for observability.

## RCx and fault diagnostics

### 12. Why require four persistent samples?

Persistence reduces noise-driven alerts. With 15-minute sampling, the fourth consecutive violation occurs 45 minutes after the first violating sample. The trade-off is slower detection; the persistence length should be tuned from real false-positive/false-negative costs.

### 13. How is a sensor bias detected, and what is unrealistic about it?

The rule detects a sustained measured-minus-reference residual above 1.2 °C. In simulation the reference is a trusted state, but a real building has no observable “true zone temperature.” Field use would need a calibrated model, redundant sensor, cross-check, or portable instrument.

### 14. How do you distinguish a stuck valve from insufficient cooling capacity?

A stuck-valve diagnosis uses command-feedback mismatch: high command with feedback remaining far below it. Insufficient capacity could have high command and high feedback but poor temperature response. In the field I would also check actuator signal, linkage, valve stroke, water temperatures/flow, and sensor validity.

### 15. Why does the fouled-filter rule use both airflow and fan power?

Low airflow alone could reflect a low command. The rule requires meaningful airflow command, degraded airflow/command ratio, and higher-than-expected fan power. Combining independent symptoms improves specificity, though real validation should also use filter differential pressure and VFD/static-pressure data.

### 16. How is authorized pre-cooling kept from becoming an after-hours false positive?

The scenario records `preconditioning_authorized` when the predictive controller is unoccupied but sees near-future occupancy. The after-hours rule explicitly excludes that condition, then requires unoccupied status, high command, and HVAC power.

### 17. What is the difference between an alarm and an RCx finding?

An alarm is an immediate limit or state violation tied to a point and priority. An RCx finding requires sustained multi-point evidence, assigns a likely category, estimates impact, and recommends a corrective test or action. Alarms support operations; findings support investigation and improvement.

### 18. Does 4/4 recall prove the diagnostics are good?

No. It proves the rules detect four deterministic injected cases. The dataset is small and constructed. A credible validation needs diverse labeled faults, healthy seasons, sensor noise/dropouts, cross-validation, precision/recall by class, detection delay, and technician review.

## BMS and protocols

### 19. What is represented by the BACnet and Modbus fields?

Each simulated point has a BACnet object type/instance and a Modbus register, plus units and writable status. The registry demonstrates address and semantic mapping. It does not discover devices, read packets, implement scaling/endianness, or write to a controller.

### 20. What safety controls would be needed before allowing writes?

Read-only commissioning first; explicit device/point allowlists; engineering-unit and range validation; rate limits; command expiry; operator approval; local controller priority; interlocks; rollback/fallback; audit logs; network segmentation; authentication where supported; and tests that communications loss leaves the plant safe.

### 21. What data-quality checks are missing from the first version?

Missing points, frozen values, timestamp drift, duplicate samples, impossible rates of change, unit/scaling errors, stale quality flags, command/feedback naming errors, and cross-point consistency. A real analytics pipeline should block or qualify diagnostics when data quality is insufficient.

## Metrics, evidence, and professional judgment

### 22. How do you recompute the 5.623% result?

For each scenario, sum `hvac_power_kw × 0.25 h` across 672 rows. Compute `(baseline_kWh - optimized_kWh) / baseline_kWh × 100`. The exported values are 844.288 and 796.814 kWh, yielding 5.623% after rounding.

### 23. Why is the cost result less impressive than the energy result?

The illustrative cost includes both energy and peak-demand components. Energy falls 5.623%, but peak falls only 0.745%, so total cost falls 3.637%. This is a useful example of why tariff structure changes the optimization target.

### 24. What would you do first with a real office dataset?

Clarify point semantics and operating intent, preserve raw data, check quality and timestamps, profile schedules/weather/loads, split calibration and validation periods, estimate model uncertainty, define comfort/override constraints with operators, and establish a weather-normalized M&V baseline. I would deploy diagnostics read-only before any supervisory write path.

## Live modification exercises

An interviewer may ask you to change the project. Practice these without AI assistance:

1. Change occupied comfort to 23–25 °C and update both metrics and controller constraints consistently.
2. Add a frozen-temperature-sensor fault and a persistent rate-of-change diagnostic.
3. Add chilled-water supply temperature to the point registry and explain its BACnet/Modbus semantics.
4. Double the peak penalty, rerun scenarios, and explain energy/comfort/peak trade-offs.
5. Add one data-quality flag and prevent diagnostics when the relevant signal is invalid.
6. Write the failing test before each modification, then make it pass.
