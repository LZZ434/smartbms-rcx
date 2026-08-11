# Three-week Project Ownership Plan

## Objective

Codex has produced a working project. Your goal over the next 21 days is to become able to explain, verify, modify, and defend it without relying on generated answers.

The ownership rule is simple:

> **Run it → predict a change → edit one thing → test it → explain the result from evidence.**

Spend 60–90 focused minutes per day. Keep a single learning log with four fields: prediction, command/change, observed result, explanation. Do not copy an explanation into the log until you have made your own attempt.

## Before Day 1

Run the acceptance commands once:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Save the outputs. Your reference baseline is 45 passing tests, 5.623% simulated energy saving, 100% optimized occupied comfort, and 4/4 faults detected at 45 minutes.

## Week 1 — Understand the plant and baseline

### Day 1: Map the repository

Read `README.zh-CN.md`, then draw the pipeline from input generator to report without copying the Mermaid diagram. Locate the function responsible for each arrow.

Deliverable: a one-page handwritten architecture map.

Pass condition: explain why `app.py` should not contain control equations.

### Day 2: Own units and configuration

Read `smartbms/config.py`. For `R`, `C`, cooling capacity, COP, fan power, timestep, and comfort band, write unit, physical meaning, and one plausible failure caused by a bad value.

Experiment: set an invalid timestep and watch the validation test fail for the expected reason.

Pass condition: derive why `kW × h ÷ (kWh/°C)` becomes °C.

### Day 3: Rebuild the input story

Read `smartbms/weather.py`. Plot or inspect one Monday and one Saturday. Identify temperature peak time, humidity relationship, occupancy ramps, and east/west solar difference.

Experiment: change only the random seed and compare weather statistics.

Pass condition: state which quantities are HKO anchors and which are invented model choices.

### Day 4: Calculate one RC step by hand

Choose one interval from `trends-baseline.csv`. Use the previous temperature, outdoor temperature, gains, cooling, R, C, and 0.25 h to approximate the next temperature.

Pass condition: your manual result is close enough to explain rounding/model-field differences, and every term has a unit.

### Day 5: Fan and chiller power

Read `smartbms/plant.py` and `tests/test_plant.py`.

Experiment 1 — **fan cubic law**: compare fan power at 0.3 and 0.9 average airflow. Explain why the ratio is much larger than three.

Pass condition: distinguish delivered cooling kW, chiller electric kW, fan kW, and interval kWh.

### Day 6: Baseline controller

Read `BaselineController` and its tests. Predict commands for 23, 24, 26, and 29 °C in occupied and unoccupied modes before calculating them.

Experiment: change proportional gain from 0.42 to 0.30 using configuration, rerun the week, and record energy and comfort.

Pass condition: explain saturation, minimum airflow, setback, and why a reactive controller has a morning comfort gap.

### Day 7: Week-one oral checkpoint

Without opening the repository, answer interview questions 1–6. Then open the dashboard and give a 90-second explanation of Plant & Control.

Pass condition: no unsupported real-building claim and no confusion between kW and kWh.

## Week 2 — Own optimization, faults, and RCx

### Day 8: Predictive candidate search

Read `PredictiveController`. List every input, target candidate, predicted quantity, objective term, and output.

Pass condition: explain exactly why it is not full MPC or machine learning.

### Day 9: Objective trade-offs

Experiment 2 — **peak penalty**: double `peak_weight`, rerun the scenarios, and record energy, peak, comfort, and cost. Restore the default afterward.

Pass condition: explain why improving peak may worsen another metric, and why you must report all guardrails.

### Day 10: Audit the savings arithmetic

Experiment 3 — **independent KPI audit**: use `trends-baseline.csv` and `trends-optimized.csv` to recompute energy with a spreadsheet or a ten-line script. Do not call `calculate_metrics`.

Pass condition: reproduce 844.288 kWh, 796.814 kWh, and approximately 5.623%.

### Day 11: Sensor bias

Trace sensor bias from `faults.py` through controller observation, trends, diagnostics, scorecard, and dashboard.

Pass condition: explain why using the true simulation state as a reference is not field-ready and propose two real reference methods.

### Day 12: Valve and filter faults

Experiment 4 — **blind physical diagnosis**: ask someone to choose the stuck-valve or fouled-filter CSV without telling you. Use only command, feedback, airflow, temperature, and power to form a hypothesis and a physical verification test.

Pass condition: distinguish low cooling capacity from command-feedback mismatch, and low airflow command from fouling.

### Day 13: After-hours logic and false positives

Explain every condition in the after-hours rule. Temporarily remove the `preconditioning_authorized` exclusion and see whether the optimized healthy run produces a false finding. Restore it and rerun tests.

Pass condition: explain precision, recall, persistence, and why legitimate pre-cooling needs context.

### Day 14: RCx oral checkpoint

Experiment 5 — **evidence-to-action drill**: pick any finding and present four parts in 60 seconds: symptom, evidence, hypothesis, next physical test.

Pass condition: answer interview questions 12–18 without reading.

## Week 3 — Own BMS semantics, software, and presentation

### Day 15: Point registry and protocols

Trace `ZN-E-T`, `VLV-E-CMD`, and `VLV-E-FBK` from point metadata to trend fields and alarms. Learn the difference between BACnet object type/instance and a Modbus register.

Pass condition: state what the project does and does not implement at protocol level.

### Day 16: Alarm versus diagnostic

Use one fault run to compare raw alarm-event rows with the single persistent RCx finding.

Pass condition: explain when an operator needs an alarm, when an engineer needs a finding, and why excessive alarms are harmful.

### Day 17: Dashboard and reports

Read `app.py` and `reporting.py`. Identify where the dashboard reuses domain APIs and where HTML escaping/deterministic exports occur.

Pass condition: add one harmless display-only chart without duplicating KPI logic in `app.py`.

### Day 18: Test-first modification

Add a small feature using strict red-green-refactor. Recommended: a frozen-temperature sensor fault or a point-data-quality alarm.

Pass condition: show the test failing because behavior is missing, implement the minimum change, and finish with the entire suite green.

### Day 19: Chinese demo

Record the three-minute Chinese demo. Review it for time, unsupported claims, filler words, and whether you explain one causal chain rather than reading KPIs.

Pass condition: finish within 3:15 and clearly state the synthetic boundary in the first 20 seconds.

### Day 20: English pitch and mock interview

Deliver the 45-second English version, then answer ten random questions from `interview-guide.md`. For any weak answer, return to the relevant code/test rather than memorizing the model answer.

Pass condition: at least 8/10 answers include a concrete equation, threshold, file, or observed metric.

### Day 21: Final ownership test

From a blank page:

1. draw the architecture;
2. derive the RC and energy equations;
3. explain baseline versus predictive control;
4. diagnose one hidden fault;
5. map one BMS point;
6. rerun tests and exports;
7. modify one parameter and predict the result;
8. state five limitations.

Pass condition: you can complete all eight without generated prose. At that point the project is legitimately yours to present as a project you understand and can extend.

## Five experiments to show an interviewer

1. Fan cubic-law calculation.
2. Peak-penalty sensitivity analysis.
3. Independent energy integration from CSV.
4. Blind fault diagnosis from trends.
5. End-to-end point mapping from protocol metadata to alarm and UI.

Keep a screenshot/table for each experiment under your own notes. Do not add a result to the repository or résumé unless you can reproduce it from a clean checkout.

## When to ask Codex for help

Good requests:

- “Give me a hint, not the answer, for why this test fails.”
- “Quiz me on the RC equation and challenge vague answers.”
- “Review my explanation for unsupported claims.”
- “Create a failing test for this behavior after I describe the expected API.”
- “Compare my manually calculated result with the code and locate the discrepancy.”

Avoid asking Codex to rewrite the entire project before you understand the current version. The next three weeks should increase your ownership, not just the code volume.
