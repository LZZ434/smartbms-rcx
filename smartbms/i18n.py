"""Offline presentation-layer localization for the SmartBMS portfolio."""

from __future__ import annotations

from datetime import date
import re
from string import Formatter
from typing import Any, Iterable, Literal, Mapping, cast

import pandas as pd

from smartbms.diagnostics import DiagnosticFinding, findings_to_frame


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
        "page.overview": "项目概览",
        "page.plant_control": "设备与控制",
        "page.energy_optimization": "能源优化",
        "page.rcx_diagnostics": "再调试（RCx）诊断",
        "page.bms_points_alarms": "BMS 点表与报警",
        "page.learning_lab": "学习实验室",
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


def _domain_label(
    mapping: Mapping[str, Mapping[Language, str]], value: str, language: str
) -> str:
    selected = _validate_language(language)
    return mapping.get(value, {}).get(selected, value)


def scenario_label(value: str, language: str) -> str:
    if value in SCENARIO_LABELS:
        return _domain_label(SCENARIO_LABELS, value, language)
    if value.startswith("fault-"):
        fault = value.removeprefix("fault-")
        label = fault_label(fault, language)
        return f"Fault – {label}" if language == "en" else f"故障 – {label}"
    return value


def fault_label(value: str, language: str) -> str:
    return _domain_label(FAULT_LABELS, value, language)


def severity_label(value: str, language: str) -> str:
    return _domain_label(SEVERITY_LABELS, value.lower(), language)


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
    if "severity" in localized:
        localized["severity"] = localized["severity"].map(
            lambda value: severity_label(str(value), selected)
        )
    for column in ("detected", "writable"):
        if column in localized:
            labels = {True: "Yes" if selected == "en" else "是", False: "No" if selected == "en" else "否"}
            localized[column] = localized[column].map(lambda value: labels.get(bool(value), value))
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
