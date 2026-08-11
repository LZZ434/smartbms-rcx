# SmartBMS-RCx Design

Date: 2026-08-11

## Purpose

Build a portfolio-ready, locally reproducible demonstration of building automation, HVAC energy optimization, retro-commissioning (RCx), and digital energy services. The project is designed for a Hong Kong automation student targeting BMS controls, energy engineering, RCx, data-centre controls, and digital-solutions roles.

Codex will build the first complete version. The repository must then support three weeks of guided learning so the owner can explain, modify, test, and defend every major engineering decision in an interview.

## Truthful Portfolio Claim

The project is a software simulation and engineering proof of concept. It does not claim:

- connection to a real building or production BMS;
- field commissioning or hardware installation experience;
- production-grade BACnet or Modbus interoperability;
- calibrated energy savings from a real customer site;
- compliance certification or professional RCx qualification.

All synthetic inputs, engineering assumptions, simulated protocol mappings, and inferred savings must be labelled clearly.

## Primary Scenario

Simulate one small Hong Kong office floor with two thermal zones over a deterministic seven-day period at 15-minute resolution.

The virtual plant contains:

- outdoor weather and solar/load inputs;
- occupied and unoccupied schedules;
- two zone-temperature states;
- an air-handling unit;
- supply-air temperature and airflow control;
- cooling-valve and fan-power behaviour;
- a simplified chiller coefficient-of-performance model;
- temperature, power, valve, airflow, and occupancy BMS points.

The thermal model will be deliberately compact and explainable. A first-principles resistance-capacitance model is preferred over a black-box machine-learning model.

## Control Strategies

### Baseline control

- fixed occupied/unoccupied schedule;
- fixed comfort setpoint;
- thermostat or proportional control;
- static supply-air and airflow rules;
- conventional alarm thresholds.

### Optimized control

- weather- and occupancy-aware pre-cooling;
- dynamic zone-temperature setpoints;
- bounded control actions;
- occupied comfort constraints;
- explicit penalty for energy, peak demand, and comfort violations;
- deterministic optimizer with a documented fallback to safe baseline control.

The optimized controller must be understandable from the equations and code. The project will not use deep learning merely to create an AI label.

## RCx and Fault Diagnostics

The simulator will inject four labelled fault scenarios:

1. zone-temperature sensor bias;
2. cooling valve stuck or partially stuck;
3. fouled filter represented by increased fan power for delivered airflow;
4. after-hours HVAC operation in an unoccupied zone.

Diagnostics will combine engineering rules and model residuals. Each finding must include:

- affected BMS points;
- detection time and severity;
- evidence used by the rule or residual;
- estimated energy or comfort impact;
- recommended inspection or corrective action;
- post-correction comparison when applicable.

This is an educational RCx workflow, not a claim of certified fault diagnosis.

## BMS Point and Alarm Layer

Maintain a machine-readable point registry containing:

- point identifier and human-readable name;
- equipment and zone;
- sensor, command, status, or calculated-point type;
- engineering unit and valid range;
- alarm limits;
- trend interval;
- example BACnet object mapping;
- example Modbus register mapping where appropriate.

Protocol information is a semantic simulation only. The first version will not open a BACnet socket or control real equipment.

## Metrics and Measurement

For baseline and optimized operation, calculate:

- HVAC electrical energy in kWh;
- peak electrical demand in kW;
- occupied comfort-violation degree-hours;
- equipment runtime;
- a clearly labelled synthetic operating-cost metric;
- energy, peak, and cost differences;
- fault-detection precision, recall, and detection delay on the bundled scenarios.

The interface and documentation must show absolute values as well as percentage changes. No fixed savings percentage will be promised before running the verified model.

## User Interface

Use a Python Streamlit application with these pages:

1. **Executive Overview** — system status, headline KPIs, current alarms, and baseline-versus-optimized results.
2. **Plant and Controls** — zone states, controller actions, equipment behaviour, and an accelerated simulation runner.
3. **Energy Optimization** — control-strategy comparison, energy/peak/comfort trade-offs, and adjustable parameters.
4. **RCx Diagnostics** — fault injection, evidence plots, severity, energy impact, and corrective recommendations.
5. **BMS Points and Alarms** — point registry, current values, units, alarm states, and simulated protocol references.
6. **Learning Lab** — guided experiments and interview-focused explanations.

The application must remain usable without internet access.

## Reports and Portfolio Assets

Generate:

- a reproducible HTML or Markdown RCx report;
- CSV exports of trends, alarms, points, and comparison metrics;
- English and Chinese README material;
- a Mermaid architecture diagram;
- a one-page English case-study outline;
- truthful Chinese and English resume bullets;
- a three-minute demonstration script;
- interview questions with answer guidance;
- a three-week ownership and learning schedule.

PDF export and video recording are optional follow-up tasks, not acceptance requirements for the first version.

## Code Architecture

Use small, separately testable modules:

- `smartbms/config.py` — validated scenario and controller configuration;
- `smartbms/weather.py` — deterministic weather and load generation;
- `smartbms/plant.py` — thermal zones and HVAC plant simulation;
- `smartbms/controllers.py` — baseline and optimized controllers;
- `smartbms/faults.py` — fault definitions and injection;
- `smartbms/diagnostics.py` — RCx rules, residuals, severity, and recommendations;
- `smartbms/points.py` — point registry, alarms, and protocol metadata;
- `smartbms/metrics.py` — energy, comfort, cost, and diagnostic metrics;
- `smartbms/reporting.py` — report and export generation;
- `smartbms/scenarios.py` — bundled healthy and faulty scenarios;
- `app.py` — Streamlit presentation layer only;
- `tests/` — unit, integration, and acceptance tests.

The UI must call domain modules rather than duplicating engineering calculations.

## Error Handling and Reproducibility

- Validate configuration ranges before simulation.
- Use fixed random seeds where noise is included.
- Reject impossible sensor or equipment parameters with helpful messages.
- Detect optimizer failure and fall back to baseline control while recording the event.
- Keep bundled scenarios deterministic so tests and screenshots remain reproducible.
- Avoid network dependencies during normal execution.

## Testing Strategy

Unit tests will cover thermal state updates, controller bounds, fault injection, alarm generation, metric calculations, and configuration validation.

Integration tests will cover:

- complete healthy baseline simulation;
- complete optimized simulation;
- each fault scenario and its expected diagnostic category;
- report generation;
- data-export schemas.

Acceptance tests must demonstrate:

1. one documented command starts the application;
2. the seven-day scenario runs without manual data preparation;
3. baseline and optimized results are both visible;
4. comfort, energy, and peak metrics are calculated from simulated trends;
5. all four fault types produce traceable diagnostic evidence;
6. the report and CSV exports are generated successfully;
7. the complete automated test suite passes;
8. claims in README and resume bullets match measured outputs.

Optimization is considered successful only if the verified bundled scenario improves the stated objective without violating the documented comfort limit. If it does not, the result will be reported honestly and the controller will be corrected rather than hard-coding a favourable percentage.

## Learning and Ownership Design

The Learning Lab will require the owner to complete five experiments:

1. change occupancy and explain the cooling-load response;
2. change the comfort band and explain the energy trade-off;
3. inject a sensor fault and trace the diagnostic evidence;
4. compare controller actions during pre-cooling and occupied hours;
5. regenerate and explain an RCx report without relying on memorized wording.

Each core module will have a concise explanation covering purpose, inputs, outputs, assumptions, and common interview questions. The project is not considered personally mastered until the owner can reproduce these experiments and explain the governing equations.

## Optional Extension

After all acceptance criteria pass, a simplified data-centre cooling scenario may be added with IT load, cooling power, supply-temperature control, and PUE-style metrics. It must reuse the same plant, points, diagnostics, and reporting interfaces.

This extension will not delay or destabilize the office-HVAC core.

## Explicit Non-Goals for the First Version

- real hardware control;
- production BACnet, Modbus, MQTT, or cloud deployment;
- EnergyPlus-scale whole-building modelling;
- BIM or 3D visualization;
- deep-learning fault detection;
- multi-building fleet management;
- authentication, billing, or multi-user administration;
- a second complete data-centre application.

## Delivery Boundary for the Initial Build

The initial build will deliver the complete office-HVAC core, local dashboard, automated tests, reports, documentation, portfolio text, and learning materials. It will be verified locally. Deployment, publication to GitHub, and connection to any external service require separate authorization.
