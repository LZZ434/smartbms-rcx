# Case Study: SmartBMS-RCx Synthetic Office HVAC Supervisor

## Context

Building-controls, RCx, and digital-energy roles require more than a visually attractive dashboard. A useful portfolio project should show plant reasoning, control decisions, BMS point semantics, fault evidence, measurable constraints, and honest claim boundaries.

SmartBMS-RCx is an offline proof of concept for a two-zone Hong Kong office. It uses deterministic synthetic weather and loads, a first-order RC thermal plant, a simplified shared AHU/chiller model, two supervisory strategies, four fault scenarios, persistent diagnostics, and simulated protocol metadata.

## Engineering question

Can an explainable predictive supervisor reduce simulated HVAC energy without sacrificing occupied comfort, while the same software stack detects actionable RCx faults and exposes BMS-style point/alarm data?

## Approach

1. Built validated dataclass configuration with explicit engineering units and deterministic seven-day inputs anchored to HKO August normals.
2. Implemented two independent RC zones with internal/solar gains, airflow-dependent cooling, chiller COP, and cubic fan power.
3. Established a schedule/P-control baseline, then implemented a bounded one-hour candidate search using energy, peak, and comfort penalties plus safe fallback.
4. Injected temperature-sensor bias, stuck-valve, fouled-filter, and after-hours faults in disclosed time windows.
5. Designed persistent RCx rules that produce evidence, severity, confidence, estimated impact, and corrective action.
6. Added a 19-point simulated BMS registry with BACnet/Modbus metadata and instantaneous alarm rules.
7. Connected the same tested APIs to a seven-page bilingual Streamlit dashboard, strict trend-data quality workspace, and deterministic HTML/CSV export pipeline.

## Verified result

For the fixed synthetic week, baseline energy was 844.288 kWh and predictive-supervisor energy was 796.814 kWh, a 5.623% reduction. Peak demand changed from 18.646 to 18.507 kW. Occupied comfort inside 22–26 °C improved from 86.889% to 100.000%, while discomfort degree-hours decreased from 6.253 to zero.

All four injected faults were detected at the fourth persistent 15-minute sample: 4/4 recall, 45-minute delay, and no unexpected findings in the fixed scenario suite. The repository contains 69 passing unit, integration, export, localization, and dashboard-smoke tests.

## Interpretation

The result shows internal consistency of the disclosed model, not field savings. The largest optimization value comes from pre-conditioning and reduced unnecessary runtime; peak reduction is small, which is reported rather than hidden. The baseline's morning comfort gap also shows why energy-only comparison is insufficient.

The sensor-bias rule uses a trusted simulation reference, so a real deployment would need calibration or independent reference evidence. Likewise, the BACnet/Modbus fields demonstrate point-model understanding but do not constitute protocol commissioning.

## What I would do with real data

- run data-quality checks before model fitting;
- estimate R/C/load parameters with train/validation periods and uncertainty bounds;
- agree comfort, scheduling, and override constraints with operators;
- establish a measurement-and-verification baseline separate from the control model;
- deploy diagnostics read-only, review false positives with technicians, and only then consider supervised control writes with interlocks;
- compare savings over weather-normalized periods rather than one week.

## Portfolio claim

“I developed and tested a synthetic building-controls proof of concept that links a two-zone thermal model, explainable predictive supervision, RCx diagnostics, BMS point semantics, and a Streamlit operator dashboard. In its fixed simulated week it reduced HVAC energy by 5.623% while maintaining 100% occupied comfort and detected four injected faults after 45 minutes. I explicitly treat those results as model-specific, not real-building savings.”
