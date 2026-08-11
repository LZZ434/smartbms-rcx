# Truthful Résumé and Portfolio Wording

## Recommended project title

**SmartBMS-RCx — Synthetic Building HVAC Control and Retro-commissioning Proof of Concept**

中文：**SmartBMS-RCx——楼宇空调控制与再调试诊断仿真概念验证**

## Recommended English bullets

- Developed a deterministic Python/Streamlit **synthetic building-controls proof of concept** integrating a two-zone RC thermal model, schedule/P control, one-hour bounded predictive supervision, BMS point semantics, and RCx diagnostics.
- Reduced simulated weekly HVAC energy from **844.288 to 796.814 kWh (5.623%)** while keeping **100% of occupied zone-samples within 22–26 °C** in the fixed test scenario; reported the result as model-specific rather than real-building savings.
- Detected **4/4 injected faults** (sensor bias, stuck valve, fouled filter, and after-hours operation) after four persistent 15-minute samples, with **45-minute delay and zero unexpected findings**; exposed evidence, corrective actions, alarms, simulated BACnet/Modbus metadata, and CSV/HTML reports.
- Wrote **69 unit, integration, export, localization, and dashboard-smoke tests** covering thermal response, control bounds/fallback, fault effects, diagnostic persistence, KPI arithmetic, deterministic exports, bilingual reports, and two-language page rendering.

Use the best three bullets for a one-page résumé. Keep the fourth for testing/software-heavy roles.

## 推荐中文表述

- 使用 Python/Streamlit 完成**楼宇自控仿真概念验证**：整合两区 RC 热模型、时序/P 控制、一小时有界预测监督、BMS 点表语义和 RCx 故障诊断。
- 在固定合成周场景中，将 HVAC 能耗由 **844.288 kWh 降至 796.814 kWh（5.623%）**，同时保持占用时区温样本 **100% 位于 22–26 °C**；明确说明结果只适用于该仿真模型。
- 对传感器偏置、阀门卡滞、过滤器堵塞和非工作时段运行实现持续性诊断，固定场景下 **4/4 检出、延迟 45 分钟、额外误报 0 项**，并输出证据、整改建议、报警和模拟 BACnet/Modbus 点表。
- 编写 **69 个自动化测试**，覆盖热响应、控制边界/回退、故障影响、诊断持续性、指标复算、双语报告和两种语言的页面渲染。

## Role-specific emphasis

### BMS control software / Digital Solutions

Lead with the end-to-end trend schema, controller fallback, point registry, alarm semantics, tested APIs, and six-page operator dashboard.

Suggested line:

> Designed a tested BMS-oriented data/control pipeline from synthetic points and supervisory actions to alarms, RCx findings, KPI reports, and an operator dashboard, with explicit writable flags and simulated BACnet/Modbus mappings.

### Energy optimization

Lead with identical input conditions, energy integration, comfort constraints, peak trade-off, and honest M&V limitations.

Suggested line:

> Compared baseline and predictive HVAC supervision under identical deterministic weather/load inputs, measuring a 5.623% simulated energy reduction with zero occupied discomfort degree-hours; documented why the result is not an M&V claim.

### RCx / commissioning analytics

Lead with command-feedback evidence, persistence, false-positive control, diagnostic delay, and physical corrective tests.

Suggested line:

> Implemented persistent RCx rules that link command/feedback/power residuals to evidence, severity, impact estimates, and technician actions; achieved 4/4 detection with 45-minute delay in labeled synthetic scenarios.

### Data-center controls

Use the project to demonstrate transferable control/monitoring foundations, but do not call it a data-center project. Say:

> Built transferable HVAC supervisory-control and fault-diagnostics foundations; next step is extending the point/model boundary to chilled-water loops, CRAH/CRAC units, redundancy, and thermal-risk constraints.

## Keywords that are supported by the repository

Python, pandas, NumPy, Streamlit, HVAC, BMS, building controls, RC thermal model, supervisory control, proportional control, predictive control, RCx, fault detection and diagnostics (FDD), trend analysis, BACnet point model, Modbus register mapping, alarm management, energy KPI, peak demand, comfort constraint, unit testing, data visualization.

## Claims to avoid

Do not write:

- “deployed to a commercial building”;
- “saved a client 5.6% electricity”;
- “developed production BACnet integration”;
- “built an AI/MPC controller”;
- “guaranteed fault detection”;
- “validated on real Hong Kong office data.”

Use instead:

- “synthetic simulation,” “offline proof of concept,” or “fixed test scenario”;
- “bounded predictive candidate search” rather than “full MPC”;
- “simulated BACnet/Modbus metadata” rather than “protocol integration”;
- “estimated scenario impact” rather than “verified savings.”

## Before adding the project to a résumé

You should be able to do all of the following without reading a prepared answer:

1. derive the RC temperature update and explain every unit;
2. explain why fan power is modeled cubically;
3. contrast baseline, bounded predictive search, and full MPC;
4. recompute energy from the exported trend CSV;
5. diagnose one hidden fault from command/feedback/power evidence;
6. explain why the sensor-bias rule is not field-ready;
7. map one point through registry, trend, alarm, and dashboard;
8. state every synthetic-data and deployment limitation;
9. modify one controller or diagnostic parameter and predict the effect;
10. run all tests and explain at least one failure you previously fixed.
