"""Offline presentation-layer localization for the SmartBMS portfolio."""

from __future__ import annotations

from datetime import date
import re
from string import Formatter
from typing import Any, Iterable, Literal, Mapping, cast

import numpy as np
import pandas as pd

from smartbms.diagnostics import DiagnosticFinding, findings_to_frame


Language = Literal["zh", "en"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("zh", "en")
LANGUAGE_NAMES: dict[Language, str] = {"zh": "中文", "en": "English"}
PAGE_IDS = (
    "overview",
    "plant_control",
    "energy_optimization",
    "data_quality",
    "rcx_diagnostics",
    "bms_points_alarms",
    "learning_lab",
)

TRANSLATIONS: dict[Language, dict[str, str]] = {
    "en": {
        "app.title": "SmartBMS-RCx",
        "app.loading": "Running deterministic seven-day scenarios…",
        "sidebar.navigate": "Navigate",
        "sidebar.version": "Building controls portfolio · v1.0.0",
        "sidebar.disclosure": "Synthetic offline proof of concept. No live BMS connection.",
        "page.overview": "Overview",
        "page.plant_control": "Plant & Control",
        "page.energy_optimization": "Energy Optimization",
        "page.data_quality": "Data Quality & Import",
        "page.rcx_diagnostics": "RCx Diagnostics",
        "page.bms_points_alarms": "BMS Points & Alarms",
        "page.learning_lab": "Learning Lab",
        "overview.subtitle": "Synthetic Hong Kong office HVAC · controls · energy optimization · retro-commissioning",
        "overview.warning": "Portfolio proof of concept: every weather, load, BMS, fault, and savings value is synthetic. No live building or protocol connection is claimed.",
        "overview.badge": "Synthetic engineering PoC · read-only analytics · public portfolio",
        "overview.demo_title": "Three-minute demo path",
        "overview.demo.1": "**1 · Verify the fixed scenario:** explain the 5.623% simulated saving and comfort constraint.",
        "overview.demo.2": "**2 · Qualify the data:** open Data Quality & Import and show why RCx rules need trustworthy points.",
        "overview.demo.3": "**3 · Act on evidence:** open RCx Diagnostics and connect command/feedback evidence to a physical test.",
        "overview.evidence_title": "Reproducible evidence",
        "overview.evidence.tests": "{count} automated tests across physics, controls, diagnostics, ingestion, i18n, and UI",
        "overview.evidence.seed": "Deterministic portfolio seed: 20260803",
        "overview.evidence.boundary": "Synthetic trends and read-only screening; no live BMS write path",
        "overview.repository": "View public source code",
        "overview.release": "Release {version}",
        "metric.energy_saving": "Energy saving",
        "metric.scenario_specific": "scenario-specific",
        "metric.peak_reduction": "Peak reduction",
        "metric.occupied_comfort": "Occupied comfort",
        "metric.fault_recall": "Fault recall",
        "metric.delay": "45 min delay",
        "metric.energy": "Energy",
        "metric.peak": "Peak",
        "metric.runtime": "Runtime",
        "metric.comfort": "Comfort",
        "overview.week": "One-week operational view",
        "overview.inside": "What is inside this project?",
        "overview.item.1": "A two-zone resistance-capacitance thermal model and simplified AHU/chiller energy model.",
        "overview.item.2": "Schedule/P-control baseline and an explainable bounded one-hour candidate search.",
        "overview.item.3": "Sensor-bias, stuck-valve, fouled-filter, and after-hours fault injection.",
        "overview.item.4": "Persistent RCx rules with evidence, severity, impact estimate, and corrective action.",
        "overview.item.5": "Simulated BACnet object and Modbus register mapping, alarms, CSVs, and technical report.",
        "download.html": "Download HTML technical report",
        "download.markdown": "Download Markdown summary",
        "plant.subtitle": "Trace temperatures, commands, feedback, load, and HVAC power.",
        "plant.scenario": "Scenario",
        "plant.day": "Day",
        "plant.temperatures": "Zone temperatures and targets",
        "plant.power": "Power",
        "plant.command_feedback": "East command vs feedback",
        "plant.equations": "Engineering equations and units",
        "plant.units": "R: °C/kW · C: kWh/°C · heat/cooling/power: kW · interval energy: kWh",
        "optimization.subtitle": "Measured from identical deterministic inputs; optimization is a bounded candidate search, not deep learning.",
        "optimization.energy": "Energy (kWh)",
        "optimization.peak": "Peak demand (kW)",
        "optimization.why": "Why energy changed",
        "optimization.explanation": "The optimized controller uses a one-hour weather/occupancy look-ahead, authorized pre-cooling, relaxed unoccupied operation, and a comfort penalty. In this fixed synthetic week it reduces energy by **{saving:.3f}%** while keeping all occupied zone-samples inside 22–26 °C. The result is not transferable to a real site without calibration.",
        "optimization.download": "Download comparison CSV",
        "quality.subtitle": "Validate trend integrity before read-only RCx screening.",
        "quality.disclosure": "The bundled sample is synthetic. Uploaded data is screened read-only and does not change the verified portfolio KPI scenario.",
        "quality.privacy": "Uploaded CSV content is processed in memory for this session and is not stored by the application.",
        "quality.sample_download": "Download canonical sample CSV",
        "quality.upload": "Upload BMS trend CSV (optional)",
        "quality.upload_help": "Maximum 10 MB · UTF-8 CSV · canonical English engineering field names",
        "quality.source_sample": "Source: bundled synthetic healthy baseline",
        "quality.source_upload": "Source: uploaded in-memory CSV",
        "quality.rows": "Rows",
        "quality.interval": "Sampling interval",
        "quality.time_span": "Time span",
        "quality.score": "Quality score",
        "quality.ready_rules": "RCx rules ready",
        "quality.checks": "Quality checks",
        "quality.issues": "Detected data issues",
        "quality.no_issues": "No data-quality issue was detected in the selected source.",
        "quality.readiness": "Rule-specific RCx readiness",
        "quality.findings": "Screening findings",
        "quality.no_findings": "No screening finding was produced by the admitted rules.",
        "quality.preview": "Normalized-data preview",
        "quality.normalized_download": "Download normalized trends CSV",
        "quality.report_download": "Data-quality report CSV",
        "quality.screening_disclosure": "Screening findings require technician review and field context. Eligibility is not proof of calibration or deployability.",
        "quality.detail": "{issue}; affected rows: {rows}",
        "quality.error.empty_file": "The CSV is empty. Add at least one timestamped data row.",
        "quality.error.file_too_large": "The CSV exceeds the 10 MB upload limit.",
        "quality.error.malformed_csv": "The file is not a valid UTF-8 CSV.",
        "quality.error.missing_timestamp": "A canonical timestamp column is required.",
        "quality.error.invalid_timestamp": "The timestamp column contains missing or unparseable values.",
        "quality.error.invalid_numeric": "A known engineering point contains a non-numeric value.",
        "quality.error.invalid_boolean": "A known boolean point contains an unsupported value.",
        "quality.error.duplicate_columns": "The CSV contains duplicate column names.",
        "rcx.subtitle": "Four-sample persistence, explicit evidence, and corrective action.",
        "rcx.injected_fault": "Injected fault",
        "rcx.severity": "Severity",
        "rcx.confidence": "Confidence",
        "rcx.impact": "Estimated impact",
        "rcx.action": "Recommended action: {recommendation}",
        "rcx.evidence": "Evidence around the injected window",
        "rcx.window": "Fault active: {start} to {end} · detected: {detected}",
        "points.subtitle": "Simulated protocol semantics for interview discussion—no BACnet/Modbus client is connected.",
        "points.equipment_filter": "Equipment filter",
        "points.download": "Download point registry",
        "points.alarms": "Alarm event explorer",
        "points.alarm_scenario": "Alarm scenario",
        "points.priority": "Priority",
        "learning.subtitle": "Use five guided experiments to turn generated code into your own engineering knowledge.",
        "learning.experiment.1.title": "1 · Verify the fan cubic law",
        "learning.experiment.1.text": "Open Plant & Control, compare airflow and fan power, then calculate whether doubling airflow can approach eight times the variable fan power.",
        "learning.experiment.2.title": "2 · Explain the baseline comfort gap",
        "learning.experiment.2.text": "Find the first occupied hour. Explain thermal inertia and why a schedule-only controller starts cooling later than the predictive controller.",
        "learning.experiment.3.title": "3 · Audit the savings claim",
        "learning.experiment.3.text": "Download both trend CSVs and recompute Σ(power × 0.25 h). Confirm the 5.623% result before using it on a résumé.",
        "learning.experiment.4.title": "4 · Diagnose one fault blind",
        "learning.experiment.4.text": "Hide the fault name, inspect command/feedback/power trends, state a hypothesis, evidence, and maintenance test, then compare with the finding.",
        "learning.experiment.5.title": "5 · Map a point end to end",
        "learning.experiment.5.text": "Pick ZN-E-T or VLV-E-FBK, trace engineering unit, BACnet object, Modbus register, alarm rule, trend column, and dashboard use.",
        "learning.blind": "Blind fault drill",
        "learning.select_set": "Select evidence set",
        "learning.evidence_set": "Evidence set {label}",
        "learning.signals": "Signals",
        "learning.hypothesis": "Your hypothesis and next physical test",
        "learning.reveal": "Reveal answer",
        "report.eyebrow": "Synthetic controls engineering proof of concept",
        "report.title": "SmartBMS-RCx Technical Report",
        "report.subtitle": "Two-zone Hong Kong office HVAC simulation, supervisory optimization, BMS semantics, and retro-commissioning diagnostics.",
        "report.disclosure_label": "Disclosure",
        "report.disclosure": "All weather/load/BMS trends are synthetic. Results are scenario-specific and are not measured building performance, a savings guarantee, or evidence of a live BACnet/Modbus deployment.",
        "report.kpi.energy": "simulated energy saving",
        "report.kpi.peak": "simulated peak reduction",
        "report.kpi.comfort": "optimized occupied comfort",
        "report.kpi.faults": "injected faults detected",
        "report.section.scenario": "Scenario comparison",
        "report.scenario_note": "Energy is interval power integrated at 15 minutes. Comfort is the share of occupied zone-samples inside 22–26 °C. Cost is illustrative and uses a disclosed synthetic tariff.",
        "report.section.scorecard": "RCx diagnostic scorecard",
        "report.scorecard_note": "Each rule requires four consecutive samples. A 45-minute delay therefore means detection at the fourth 15-minute sample.",
        "report.section.findings": "Findings and actions",
        "report.section.boundary": "Model boundary",
        "report.boundary.1": "First-order two-zone RC thermal model and simplified shared AHU/chiller power model.",
        "report.boundary.2": "Baseline schedule/P control versus bounded one-hour candidate search; this is not a trained AI model or full MPC implementation.",
        "report.boundary.3": "Faults: sensor bias, stuck valve, fouled filter, and after-hours operation.",
        "report.boundary.4": "BACnet objects and Modbus registers are simulated point metadata only.",
        "report.section.sources": "Source anchors",
        "report.source.hko": "Hong Kong Observatory 1991–2020 August normals",
        "report.source.hko_note": "anchors for synthetic summer profile shape.",
        "report.source.emsd": "EMSD Technical Guidelines on Retro-commissioning",
        "report.source.emsd_note": "RCx workflow context.",
        "report.footer": "Deterministic project seed: {seed}. Report content is generated from the same APIs used by the dashboard and tests.",
        "report.markdown_disclosure": "Synthetic-data disclosure",
        "report.section.verified": "Verified scenario result",
        "report.result.energy": "Energy: {baseline:.3f} → {optimized:.3f} kWh ({saving:.3f}% simulated saving)",
        "report.result.peak": "Peak: {baseline:.3f} → {optimized:.3f} kW ({reduction:.3f}% simulated reduction)",
        "report.result.comfort": "Optimized occupied comfort: {comfort:.3f}% inside 22–26 °C",
        "report.result.rcx": "RCx detection: {detected}/4 injected faults; median delay {delay:.0f} minutes",
        "report.section.boundaries": "Boundaries",
        "report.markdown_disclosure_text": "This proof of concept uses generated weather, loads, faults, and BMS trends. It is not measured building performance or a savings guarantee.",
        "report.boundary.short.1": "Two-zone first-order RC model; simplified fan/chiller energy.",
        "report.boundary.short.2": "Bounded predictive candidate search, not a trained model or full MPC.",
        "report.boundary.short.3": "Simulated BACnet/Modbus metadata; no live building connection.",
        "report.boundary.short.4": "Illustrative tariff; no commercial savings claim.",
        "report.section.references": "References",
    },
    "zh": {
        "app.title": "SmartBMS-RCx",
        "app.loading": "正在运行确定性的七天仿真场景…",
        "sidebar.navigate": "页面导航",
        "sidebar.version": "楼宇控制作品集 · v1.0.0",
        "sidebar.disclosure": "离线合成概念验证，未连接真实 BMS。",
        "page.overview": "项目概览",
        "page.plant_control": "设备与控制",
        "page.energy_optimization": "能源优化",
        "page.data_quality": "数据质量与导入",
        "page.rcx_diagnostics": "再调试（RCx）诊断",
        "page.bms_points_alarms": "BMS 点表与报警",
        "page.learning_lab": "学习实验室",
        "overview.subtitle": "香港办公室 HVAC 合成仿真 · 控制 · 能源优化 · 再调试（RCx）",
        "overview.warning": "作品集概念验证：天气、负荷、BMS、故障和节能数值全部为合成数据，不代表已连接真实楼宇或通信协议。",
        "overview.badge": "合成工程 PoC · 只读分析 · 公开作品集",
        "overview.demo_title": "三分钟演示路线",
        "overview.demo.1": "**1 · 验证固定场景：**解释 5.623% 模拟节能和舒适度约束。",
        "overview.demo.2": "**2 · 判断数据能否使用：**打开“数据质量与导入”，说明 RCx 为什么需要可信点位。",
        "overview.demo.3": "**3 · 从证据到行动：**打开 RCx 诊断，把指令/反馈证据连接到现场功能测试。",
        "overview.evidence_title": "可复现实证",
        "overview.evidence.tests": "{count} 项自动化测试，覆盖物理模型、控制、诊断、导入、双语和界面",
        "overview.evidence.seed": "确定性作品集随机种子：20260803",
        "overview.evidence.boundary": "合成趋势与只读筛查；没有真实 BMS 写入路径",
        "overview.repository": "查看公开源代码",
        "overview.release": "版本 {version}",
        "metric.energy_saving": "模拟节能率",
        "metric.scenario_specific": "仅适用于本场景",
        "metric.peak_reduction": "峰值降低率",
        "metric.occupied_comfort": "占用时舒适率",
        "metric.fault_recall": "故障检出率",
        "metric.delay": "延迟 45 分钟",
        "metric.energy": "能耗",
        "metric.peak": "峰值功率",
        "metric.runtime": "运行时间",
        "metric.comfort": "舒适率",
        "overview.week": "一周运行概览",
        "overview.inside": "这个项目包含什么？",
        "overview.item.1": "两区域阻容（RC）热模型，以及简化的 AHU/冷水机组能耗模型。",
        "overview.item.2": "日程/P 控制基线，以及可解释的一小时有界候选搜索。",
        "overview.item.3": "传感器偏置、阀门卡滞、过滤器堵塞和非工作时段运行故障注入。",
        "overview.item.4": "带持续性判据、证据、严重程度、影响估算和整改措施的 RCx 规则。",
        "overview.item.5": "模拟 BACnet 对象、Modbus 寄存器映射、报警、CSV 和技术报告。",
        "download.html": "下载 HTML 技术报告",
        "download.markdown": "下载 Markdown 摘要",
        "plant.subtitle": "查看温度、控制指令、设备反馈、负荷和 HVAC 功率。",
        "plant.scenario": "场景",
        "plant.day": "日期",
        "plant.temperatures": "区域温度与目标值",
        "plant.power": "功率",
        "plant.command_feedback": "东区指令与反馈",
        "plant.equations": "工程公式与单位",
        "plant.units": "R：°C/kW · C：kWh/°C · 热量/冷量/功率：kW · 间隔能耗：kWh",
        "optimization.subtitle": "使用完全相同的确定性输入进行比较；优化采用有界候选搜索，不是深度学习。",
        "optimization.energy": "能耗 (kWh)",
        "optimization.peak": "峰值需量 (kW)",
        "optimization.why": "能耗为何发生变化",
        "optimization.explanation": "优化控制器使用一小时天气/占用预测、授权预冷、放宽无人时段运行，并加入舒适度惩罚。在该固定合成周中，能耗降低 **{saving:.3f}%**，同时所有占用时区域温度样本均位于 22–26 °C。未经真实数据标定，结果不能直接外推到实际项目。",
        "optimization.download": "下载场景对比 CSV",
        "quality.subtitle": "在运行只读 RCx 筛查前，先验证趋势数据的完整性与可信度。",
        "quality.disclosure": "内置样例为合成数据；上传数据仅用于只读筛查，不会改变作品集已验证的 KPI 场景。",
        "quality.privacy": "上传的 CSV 仅在本次会话的内存中处理，应用不会保存文件内容。",
        "quality.sample_download": "下载标准样例 CSV",
        "quality.upload": "上传 BMS 趋势 CSV（可选）",
        "quality.upload_help": "最大 10 MB · UTF-8 CSV · 使用标准英文工程字段名",
        "quality.source_sample": "数据源：内置合成健康基线",
        "quality.source_upload": "数据源：上传的内存 CSV",
        "quality.rows": "数据行数",
        "quality.interval": "采样间隔",
        "quality.time_span": "时间范围",
        "quality.score": "质量评分",
        "quality.ready_rules": "可运行 RCx 规则",
        "quality.checks": "数据质量检查",
        "quality.issues": "已发现的数据问题",
        "quality.no_issues": "当前数据源未检出数据质量问题。",
        "quality.readiness": "各 RCx 规则准入状态",
        "quality.findings": "筛查结果",
        "quality.no_findings": "已获准运行的规则没有产生筛查结果。",
        "quality.preview": "标准化数据预览",
        "quality.normalized_download": "下载标准化趋势 CSV",
        "quality.report_download": "数据质量报告 CSV",
        "quality.screening_disclosure": "筛查结果仍需技术人员结合现场信息复核；规则可运行不等于传感器已校准或方案可直接部署。",
        "quality.detail": "{issue}；影响行数：{rows}",
        "quality.error.empty_file": "CSV 为空，请至少加入一行带时间戳的数据。",
        "quality.error.file_too_large": "CSV 超过 10 MB 上传限制。",
        "quality.error.malformed_csv": "文件不是有效的 UTF-8 CSV。",
        "quality.error.missing_timestamp": "必须包含标准字段 timestamp。",
        "quality.error.invalid_timestamp": "timestamp 中存在缺失值或无法解析的时间。",
        "quality.error.invalid_numeric": "已知工程点位中存在非数值内容。",
        "quality.error.invalid_boolean": "已知布尔点位中存在不支持的取值。",
        "quality.error.duplicate_columns": "CSV 包含重复字段名。",
        "rcx.subtitle": "采用连续四个样本的持续性判据，并给出明确证据和整改措施。",
        "rcx.injected_fault": "注入故障",
        "rcx.severity": "严重程度",
        "rcx.confidence": "置信度",
        "rcx.impact": "估算影响",
        "rcx.action": "建议措施：{recommendation}",
        "rcx.evidence": "故障注入窗口附近的证据",
        "rcx.window": "故障生效：{start} 至 {end} · 检出时间：{detected}",
        "points.subtitle": "用于面试讨论的模拟协议语义；未连接 BACnet/Modbus 客户端。",
        "points.equipment_filter": "设备筛选",
        "points.download": "下载 BMS 点表",
        "points.alarms": "报警事件浏览器",
        "points.alarm_scenario": "报警场景",
        "points.priority": "优先级",
        "learning.subtitle": "通过五个引导实验，把生成的代码转化为你自己的工程知识。",
        "learning.experiment.1.title": "1 · 验证风机立方律",
        "learning.experiment.1.text": "打开“设备与控制”，比较风量和风机功率，并计算风量翻倍时变动风机功率是否可能接近八倍。",
        "learning.experiment.2.title": "2 · 解释基线舒适度缺口",
        "learning.experiment.2.text": "找到第一个占用小时，解释热惯性，以及为什么只按日程控制会比预测控制更晚启动制冷。",
        "learning.experiment.3.title": "3 · 审核节能结论",
        "learning.experiment.3.text": "下载两份趋势 CSV，重新计算 Σ(功率 × 0.25 h)。在把 5.623% 写入简历前先独立复算。",
        "learning.experiment.4.title": "4 · 盲测诊断一个故障",
        "learning.experiment.4.text": "隐藏故障名称，检查指令、反馈和功率趋势，提出假设、证据与现场测试方法，再与系统诊断对比。",
        "learning.experiment.5.title": "5 · 端到端追踪一个点位",
        "learning.experiment.5.text": "选择 ZN-E-T 或 VLV-E-FBK，追踪其工程单位、BACnet 对象、Modbus 寄存器、报警规则、趋势列和仪表盘用途。",
        "learning.blind": "故障盲测",
        "learning.select_set": "选择证据集",
        "learning.evidence_set": "证据集 {label}",
        "learning.signals": "信号",
        "learning.hypothesis": "你的故障假设和下一项现场测试",
        "learning.reveal": "显示答案",
        "report.eyebrow": "合成楼宇控制工程概念验证",
        "report.title": "SmartBMS-RCx 技术报告",
        "report.subtitle": "香港两区域办公室 HVAC 仿真、上层优化控制、BMS 点位语义与再调试（RCx）诊断。",
        "report.disclosure_label": "声明",
        "report.disclosure": "所有天气、负荷和 BMS 趋势均为合成数据。结果只适用于本场景，不代表真实楼宇实测表现、节能保证或已连接 BACnet/Modbus 现场系统。",
        "report.kpi.energy": "模拟节能率",
        "report.kpi.peak": "模拟峰值降低率",
        "report.kpi.comfort": "优化后占用时舒适率",
        "report.kpi.faults": "已检出的注入故障",
        "report.section.scenario": "场景对比",
        "report.scenario_note": "能耗由 15 分钟间隔功率积分得到；舒适率表示占用时区域温度样本位于 22–26 °C 的比例。费用采用公开说明的模拟电价，仅供演示。",
        "report.section.scorecard": "RCx 诊断评分表",
        "report.scorecard_note": "每条规则要求连续四个样本满足条件。45 分钟延迟表示在第四个 15 分钟样本处检出。",
        "report.section.findings": "诊断发现与整改措施",
        "report.section.boundary": "模型边界",
        "report.boundary.1": "一阶两区域 RC 热模型，以及简化的共用 AHU/冷水机组功率模型。",
        "report.boundary.2": "基线日程/P 控制与一小时有界候选搜索对比；这不是训练得到的 AI 模型或完整 MPC。",
        "report.boundary.3": "故障包括传感器偏置、阀门卡滞、过滤器堵塞和非工作时段运行。",
        "report.boundary.4": "BACnet 对象和 Modbus 寄存器仅为模拟点位元数据。",
        "report.section.sources": "参考依据",
        "report.source.hko": "香港天文台 1991–2020 年八月气候常值",
        "report.source.hko_note": "用于约束合成夏季曲线形态。",
        "report.source.emsd": "机电工程署再调试技术指南",
        "report.source.emsd_note": "用于说明 RCx 工作流程背景。",
        "report.footer": "项目确定性随机种子：{seed}。报告与仪表盘和测试使用相同的数据接口生成。",
        "report.markdown_disclosure": "合成数据声明",
        "report.section.verified": "已验证的场景结果",
        "report.result.energy": "能耗：{baseline:.3f} → {optimized:.3f} kWh（模拟节能 {saving:.3f}%）",
        "report.result.peak": "峰值：{baseline:.3f} → {optimized:.3f} kW（模拟降低 {reduction:.3f}%）",
        "report.result.comfort": "优化后占用时舒适率：{comfort:.3f}%（22–26 °C）",
        "report.result.rcx": "RCx 检出：{detected}/4 个注入故障；中位延迟 {delay:.0f} 分钟",
        "report.section.boundaries": "适用边界",
        "report.markdown_disclosure_text": "本概念验证使用生成的天气、负荷、故障和 BMS 趋势，不代表真实楼宇实测表现或节能保证。",
        "report.boundary.short.1": "两区域一阶 RC 模型；简化风机和冷水机组能耗。",
        "report.boundary.short.2": "有界预测候选搜索，不是训练模型或完整 MPC。",
        "report.boundary.short.3": "模拟 BACnet/Modbus 元数据；未连接真实楼宇。",
        "report.boundary.short.4": "电价仅用于演示，不构成商业节能承诺。",
        "report.section.references": "参考资料",
    },
}

SCENARIO_LABELS: dict[str, dict[Language, str]] = {
    "baseline": {"en": "Baseline control", "zh": "基线控制"},
    "optimized": {"en": "Optimized control", "zh": "优化控制"},
}
FAULT_LABELS: dict[str, dict[Language, str]] = {
    "sensor_bias": {"en": "Sensor bias", "zh": "传感器偏置"},
    "stuck_valve": {"en": "Stuck valve", "zh": "阀门卡滞"},
    "fouled_filter": {"en": "Fouled filter", "zh": "过滤器堵塞"},
    "after_hours_operation": {"en": "After-hours operation", "zh": "非工作时段运行"},
}
SEVERITY_LABELS: dict[str, dict[Language, str]] = {
    "low": {"en": "Low", "zh": "低"},
    "medium": {"en": "Medium", "zh": "中"},
    "high": {"en": "High", "zh": "高"},
}
QUALITY_LABELS: dict[str, dict[Language, str]] = {
    "timestamps": {"en": "Timestamp integrity", "zh": "时间戳完整性"},
    "history": {"en": "History length", "zh": "历史数据长度"},
    "coverage": {"en": "Point coverage", "zh": "点位覆盖率"},
    "missing": {"en": "Missing values", "zh": "缺失值"},
    "frozen": {"en": "Frozen signals", "zh": "信号冻结"},
    "bounds": {"en": "Engineering bounds", "zh": "工程范围"},
    "temperature_rate": {"en": "Temperature rate of change", "zh": "温度变化率"},
    "cross_point": {"en": "Cross-point consistency", "zh": "跨点位一致性"},
    "timestamp_missing": {"en": "Missing timestamp column", "zh": "缺少时间戳字段"},
    "timestamp_invalid": {"en": "Invalid timestamps", "zh": "无效时间戳"},
    "timestamp_duplicate": {"en": "Duplicate timestamps", "zh": "重复时间戳"},
    "timestamp_unsorted": {"en": "Unsorted timestamps", "zh": "时间戳未排序"},
    "timestamp_irregular": {"en": "Irregular sampling interval", "zh": "采样间隔不规则"},
    "history_too_short": {"en": "Insufficient history", "zh": "历史数据不足"},
    "required_columns_missing": {"en": "Required points missing", "zh": "缺少必要点位"},
    "missing_values": {"en": "Missing point values", "zh": "点位存在缺失值"},
    "frozen_signal": {"en": "Sustained frozen signal", "zh": "信号持续冻结"},
    "engineering_bounds": {"en": "Value outside engineering bounds", "zh": "数值超出工程范围"},
    "cross_point_power": {"en": "HVAC/fan power inconsistency", "zh": "HVAC 与风机功率矛盾"},
    "cross_point_expected_fan": {"en": "Invalid expected fan power", "zh": "期望风机功率无效"},
}
QUALITY_STATUS_LABELS: dict[str, dict[Language, str]] = {
    "pass": {"en": "Passed", "zh": "通过"},
    "warning": {"en": "Warning", "zh": "警告"},
    "fail": {"en": "Failed", "zh": "未通过"},
}
QUALITY_SEVERITY_LABELS: dict[str, dict[Language, str]] = {
    "critical": {"en": "Critical", "zh": "严重"},
    "warning": {"en": "Warning", "zh": "警告"},
    "info": {"en": "Info", "zh": "提示"},
}
ALARM_MESSAGES_ZH = {
    "High zone temperature": "区域温度过高",
    "Low zone temperature": "区域温度过低",
    "HVAC power detected while building is unoccupied": "建筑无人时检测到 HVAC 用电",
    "East valve feedback does not follow command": "东区阀门反馈未跟随控制指令",
    "East airflow is low relative to command": "东区实际风量低于控制指令",
}
FINDING_TITLES_ZH = {
    "sensor_bias": "东区温度传感器偏置",
    "stuck_valve": "东区冷却阀指令与反馈不一致",
    "fouled_filter": "AHU 风量衰减且风机功率异常升高",
    "after_hours_operation": "HVAC 在占用时段之外运行",
}
FINDING_RECOMMENDATIONS_ZH = {
    "sensor_bias": "使用可溯源参考仪表校准传感器，并检查接线和偏置设置。",
    "stuck_valve": "检查执行器连杆和阀门行程，然后执行全开/全关功能测试。",
    "fouled_filter": "检查过滤器压差和堵塞情况，确认后更换过滤器。",
    "after_hours_operation": "修正 BMS 日程，增加非工作时段启用超时和例外记录。",
}

POINT_DESCRIPTIONS_ZH = {
    "East zone measured temperature": "东区实测温度",
    "West zone measured temperature": "西区实测温度",
    "East zone temperature setpoint": "东区温度设定值",
    "West zone temperature setpoint": "西区温度设定值",
    "East normalized occupancy": "东区归一化占用率",
    "West normalized occupancy": "西区归一化占用率",
    "East cooling valve command": "东区冷却阀指令",
    "East cooling valve feedback": "东区冷却阀反馈",
    "West cooling valve command": "西区冷却阀指令",
    "West cooling valve feedback": "西区冷却阀反馈",
    "East airflow command": "东区风量指令",
    "East airflow feedback": "东区风量反馈",
    "West airflow command": "西区风量指令",
    "West airflow feedback": "西区风量反馈",
    "AHU fan electrical power": "AHU 风机电功率",
    "Chiller electrical power": "冷水机组电功率",
    "Total HVAC electrical power": "HVAC 总电功率",
    "Synthetic outdoor air temperature": "合成室外空气温度",
    "Synthetic outdoor relative humidity": "合成室外相对湿度",
}

COLUMN_LABELS: dict[str, dict[Language, str]] = {
    "scenario": {"en": "Scenario", "zh": "场景"},
    "energy_kwh": {"en": "Energy (kWh)", "zh": "能耗 (kWh)"},
    "peak_kw": {"en": "Peak (kW)", "zh": "峰值功率 (kW)"},
    "occupied_discomfort_degree_hours": {
        "en": "Occupied discomfort (°C·h)",
        "zh": "占用时不舒适度 (°C·h)",
    },
    "occupied_comfort_pct": {"en": "Occupied comfort (%)", "zh": "占用时舒适率 (%)"},
    "runtime_hours": {"en": "Runtime (h)", "zh": "运行时间 (h)"},
    "synthetic_energy_cost_hkd": {"en": "Energy cost (HKD)", "zh": "模拟电费 (HKD)"},
    "synthetic_demand_cost_hkd": {"en": "Demand cost (HKD)", "zh": "模拟需量费 (HKD)"},
    "total_synthetic_cost_hkd": {"en": "Total cost (HKD)", "zh": "模拟总费用 (HKD)"},
    "energy_savings_pct": {"en": "Energy saving (%)", "zh": "节能率 (%)"},
    "peak_reduction_pct": {"en": "Peak reduction (%)", "zh": "峰值降低率 (%)"},
    "cost_savings_pct": {"en": "Cost saving (%)", "zh": "费用节省率 (%)"},
    "expected_fault": {"en": "Expected fault", "zh": "预期故障"},
    "detected": {"en": "Detected", "zh": "已检出"},
    "detection_delay_minutes": {"en": "Detection delay (min)", "zh": "检出延迟 (分钟)"},
    "unexpected_findings": {"en": "Unexpected findings", "zh": "额外发现"},
    "finding_count": {"en": "Finding count", "zh": "发现数量"},
    "category": {"en": "Category", "zh": "故障类别"},
    "title": {"en": "Finding", "zh": "诊断发现"},
    "detected_at": {"en": "Detected at", "zh": "检出时间"},
    "severity": {"en": "Severity", "zh": "严重程度"},
    "confidence": {"en": "Confidence", "zh": "置信度"},
    "evidence": {"en": "Evidence", "zh": "诊断证据"},
    "evidence_columns": {"en": "Evidence signals", "zh": "证据信号"},
    "estimated_waste_kwh": {"en": "Estimated impact (kWh)", "zh": "估算影响 (kWh)"},
    "recommendation": {"en": "Recommended action", "zh": "建议措施"},
    "point_id": {"en": "Point ID", "zh": "点位 ID"},
    "description": {"en": "Description", "zh": "说明"},
    "equipment": {"en": "Equipment", "zh": "设备"},
    "unit": {"en": "Unit", "zh": "单位"},
    "data_type": {"en": "Data type", "zh": "数据类型"},
    "writable": {"en": "Writable", "zh": "可写"},
    "bacnet_object_type": {"en": "BACnet object", "zh": "BACnet 对象"},
    "bacnet_instance": {"en": "BACnet instance", "zh": "BACnet 实例"},
    "modbus_register": {"en": "Modbus register", "zh": "Modbus 寄存器"},
    "normal_min": {"en": "Normal minimum", "zh": "正常下限"},
    "normal_max": {"en": "Normal maximum", "zh": "正常上限"},
    "connection": {"en": "Connection", "zh": "连接类型"},
    "timestamp": {"en": "Timestamp", "zh": "时间戳"},
    "priority": {"en": "Priority", "zh": "优先级"},
    "observed_value": {"en": "Observed value", "zh": "观测值"},
    "limit": {"en": "Limit", "zh": "限值"},
    "message": {"en": "Message", "zh": "报警信息"},
    "check_code": {"en": "Quality check", "zh": "检查项目"},
    "status": {"en": "Check status", "zh": "检查状态"},
    "weight": {"en": "Weight", "zh": "权重"},
    "issue_count": {"en": "Issue count", "zh": "问题数量"},
    "issue_code": {"en": "Issue", "zh": "问题代码"},
    "columns": {"en": "Affected points", "zh": "受影响点位"},
    "affected_rows": {"en": "Affected rows", "zh": "影响行数"},
    "detail": {"en": "Evidence", "zh": "问题说明"},
    "eligible": {"en": "Ready", "zh": "可运行"},
    "required_columns": {"en": "Required points", "zh": "必要点位"},
    "missing_columns": {"en": "Missing points", "zh": "缺失点位"},
    "blocking_issue_codes": {"en": "Blocking issues", "zh": "阻断问题"},
}

WEEKDAYS_ZH = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _validate_language(language: str) -> Language:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    return cast(Language, language)


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


def report_filename(language: str, file_format: str) -> str:
    selected = _validate_language(language)
    if file_format not in {"html", "md"}:
        raise ValueError(f"unsupported report format: {file_format}")
    return f"smartbms-rcx-report-{selected}.{file_format}"


def _domain_label(
    mapping: Mapping[str, Mapping[Language, str]], value: str, language: str
) -> str:
    selected = _validate_language(language)
    return mapping.get(value, {}).get(selected, value)


def scenario_label(value: str, language: str) -> str:
    selected = _validate_language(language)
    if value in SCENARIO_LABELS:
        return _domain_label(SCENARIO_LABELS, value, selected)
    if value.startswith("fault-"):
        fault = value.removeprefix("fault-")
        label = fault_label(fault, selected)
        return f"Fault – {label}" if selected == "en" else f"故障 – {label}"
    return value


def fault_label(value: str, language: str) -> str:
    return _domain_label(FAULT_LABELS, value, language)


def severity_label(value: str, language: str) -> str:
    return _domain_label(SEVERITY_LABELS, value.lower(), language)


def quality_label(value: str, language: str) -> str:
    return _domain_label(QUALITY_LABELS, value, language)


def _quality_status_label(value: str, language: str) -> str:
    return _domain_label(QUALITY_STATUS_LABELS, value, language)


def _quality_severity_label(value: str, language: str) -> str:
    return _domain_label(QUALITY_SEVERITY_LABELS, value, language)


def _quality_code_list(value: object, language: str) -> object:
    if not isinstance(value, str) or not value.strip():
        return value
    return ", ".join(
        quality_label(code.strip(), language)
        for code in value.split(",")
        if code.strip()
    )


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


def localize_findings_frame(
    findings: Iterable[DiagnosticFinding], language: str
) -> pd.DataFrame:
    selected = _validate_language(language)
    items = list(findings)
    frame = findings_to_frame(items)
    if selected == "zh" and not frame.empty:
        for position, finding in enumerate(items):
            frame.at[position, "category"] = fault_label(finding.category, selected)
            frame.at[position, "title"] = FINDING_TITLES_ZH.get(
                finding.category, finding.title
            )
            frame.at[position, "severity"] = severity_label(finding.severity, selected)
            frame.at[position, "evidence"] = localize_evidence(
                finding.category, finding.evidence, selected
            )
            frame.at[position, "recommendation"] = FINDING_RECOMMENDATIONS_ZH.get(
                finding.category, finding.recommendation
            )
    return _rename_columns(frame, selected)


def _rename_columns(frame: pd.DataFrame, language: str) -> pd.DataFrame:
    selected = _validate_language(language)
    return frame.rename(
        columns={
            column: labels[selected]
            for column, labels in COLUMN_LABELS.items()
            if column in frame.columns
        }
    )


def column_label(column: str, language: str) -> str:
    selected = _validate_language(language)
    return COLUMN_LABELS.get(column, {}).get(selected, column)


def localize_frame(frame: pd.DataFrame, language: str) -> pd.DataFrame:
    selected = _validate_language(language)
    localized = frame.copy(deep=True)
    if "scenario" in localized:
        localized["scenario"] = localized["scenario"].map(
            lambda value: scenario_label(str(value), selected)
        )
    for column in ("expected_fault", "category"):
        if column in localized:
            localized[column] = localized[column].map(
                lambda value: fault_label(str(value), selected)
            )
    if "check_code" in localized:
        localized["check_code"] = localized["check_code"].map(
            lambda value: quality_label(str(value), selected)
        )
    if "issue_code" in localized:
        raw_issue_codes = localized["issue_code"].copy()
        localized["issue_code"] = localized["issue_code"].map(
            lambda value: quality_label(str(value), selected) if value else value
        )
        if "detail" in localized and "affected_rows" in localized:
            localized["detail"] = [
                t(
                    selected,
                    "quality.detail",
                    issue=quality_label(str(code), selected),
                    rows=rows,
                )
                if code
                else detail
                for code, rows, detail in zip(
                    raw_issue_codes,
                    localized["affected_rows"],
                    localized["detail"],
                    strict=True,
                )
            ]
    if "blocking_issue_codes" in localized:
        localized["blocking_issue_codes"] = localized[
            "blocking_issue_codes"
        ].map(lambda value: _quality_code_list(value, selected))
    if "status" in localized:
        localized["status"] = localized["status"].map(
            lambda value: _quality_status_label(str(value), selected)
        )
    if "severity" in localized:
        localized["severity"] = localized["severity"].map(
            lambda value: _quality_severity_label(str(value), selected)
            if str(value) in QUALITY_SEVERITY_LABELS
            else severity_label(str(value), selected)
        )
    for column in ("detected", "writable", "eligible"):
        if column in localized:
            labels = {
                True: "Yes" if selected == "en" else "是",
                False: "No" if selected == "en" else "否",
            }
            localized[column] = localized[column].map(
                lambda value: labels[bool(value)]
                if isinstance(value, (bool, np.bool_))
                else value
            )
    if "description" in localized and selected == "zh":
        localized["description"] = localized["description"].map(
            lambda value: POINT_DESCRIPTIONS_ZH.get(str(value), value)
        )
    if "message" in localized:
        localized["message"] = localized["message"].map(
            lambda value: localize_alarm_message(str(value), selected)
        )
    if "connection" in localized and selected == "zh":
        localized["connection"] = localized["connection"].replace({"simulated": "模拟"})
    return _rename_columns(localized, selected)


def format_day(value: date, language: str) -> str:
    selected = _validate_language(language)
    if selected == "zh":
        return f"{value.month}月{value.day}日（{WEEKDAYS_ZH[value.weekday()]}）"
    return value.strftime("%a %d %b")


validate_catalogs()
