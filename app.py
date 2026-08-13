"""Streamlit dashboard for the SmartBMS-RCx synthetic portfolio project."""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from smartbms.data_quality_reporting import (
    checks_frame,
    issues_frame,
    quality_report_frame,
    readiness_frame,
)
from smartbms.i18n import (
    LANGUAGE_NAMES,
    PAGE_IDS,
    column_label,
    fault_label,
    format_day,
    localize_findings_frame,
    localize_frame,
    page_label,
    report_filename,
    scenario_label,
    severity_label,
    t,
)
from smartbms.reporting import render_html_report, render_markdown_report
from smartbms.scenarios import ScenarioBundle, ScenarioRun, run_portfolio_scenarios
from smartbms.screening import screen_trends
from smartbms.trend_io import (
    TrendIngestionError,
    canonicalize_trend_frame,
    ingest_csv_bytes,
)


QUALITY_DOWNLOAD_FILENAMES = {
    "sample": "smartbms-sample-trends.csv",
    "normalized": "smartbms-normalized-trends.csv",
    "report": "smartbms-data-quality-report.csv",
}


@st.cache_resource(show_spinner=False)
def load_bundle() -> ScenarioBundle:
    return run_portfolio_scenarios()


def _scenario_map(bundle: ScenarioBundle) -> dict[str, ScenarioRun]:
    mapping = {
        "baseline": bundle.baseline,
        "optimized": bundle.optimized,
    }
    mapping.update(
        {
            f"fault-{category}": run
            for category, run in bundle.fault_runs.items()
        }
    )
    return mapping


def _alarms_frame(run: ScenarioRun) -> pd.DataFrame:
    if not run.alarms:
        return pd.DataFrame(
            columns=("timestamp", "point_id", "priority", "observed_value", "limit", "message")
        )
    return pd.DataFrame(asdict(alarm) for alarm in run.alarms)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def _quality_error_message(error: TrendIngestionError, language: str) -> str:
    return t(language, f"quality.error.{error.code}")


def _hidden_fault_labels(
    categories: tuple[str, ...], language: str = "en"
) -> dict[str, str]:
    """Give blind-drill choices unique labels without revealing fault names."""

    return {
        category: t(
            language,
            "learning.evidence_set",
            label=chr(ord("A") + position),
        )
        for position, category in enumerate(categories)
    }


def _page_header(page_id: str, subtitle_key: str, language: str) -> None:
    st.title(page_label(page_id, language))
    st.caption(t(language, subtitle_key))


def render_overview(bundle: ScenarioBundle, language: str) -> None:
    _page_header("overview", "overview.subtitle", language)
    st.warning(t(language, "overview.warning"))
    optimized_row = bundle.comparison.loc[bundle.comparison.scenario == "optimized"].iloc[0]
    cols = st.columns(4)
    cols[0].metric(
        t(language, "metric.energy_saving"),
        f"{optimized_row.energy_savings_pct:.2f}%",
        t(language, "metric.scenario_specific"),
    )
    cols[1].metric(t(language, "metric.peak_reduction"), f"{optimized_row.peak_reduction_pct:.2f}%")
    cols[2].metric(
        t(language, "metric.occupied_comfort"),
        f"{bundle.optimized.metrics.occupied_comfort_pct:.1f}%",
    )
    cols[3].metric(
        t(language, "metric.fault_recall"),
        f"{int(bundle.diagnostic_scorecard.detected.sum())}/4",
        t(language, "metric.delay"),
    )

    st.subheader(t(language, "overview.week"))
    chart = pd.DataFrame(
        {
            "timestamp": bundle.baseline.trends.timestamp,
            "baseline_kW": bundle.baseline.trends.hvac_power_kw,
            "optimized_kW": bundle.optimized.trends.hvac_power_kw,
        }
    ).set_index("timestamp")
    st.line_chart(chart, color=["#ef8354", "#1f8a70"])

    with st.expander(t(language, "overview.inside"), expanded=True):
        st.markdown("\n".join(f"- {t(language, f'overview.item.{position}')}" for position in range(1, 6)))
    left, right = st.columns(2)
    left.download_button(
        t(language, "download.html"),
        data=render_html_report(bundle, language=language),
        file_name=report_filename(language, "html"),
        mime="text/html",
        width="stretch",
    )
    right.download_button(
        t(language, "download.markdown"),
        data=render_markdown_report(bundle, language=language),
        file_name=report_filename(language, "md"),
        mime="text/markdown",
        width="stretch",
    )


def render_plant_control(bundle: ScenarioBundle, language: str) -> None:
    _page_header("plant_control", "plant.subtitle", language)
    scenarios = _scenario_map(bundle)
    selected = st.selectbox(
        t(language, "plant.scenario"),
        list(scenarios),
        index=1,
        format_func=lambda value: scenario_label(value, language),
        key="plant_scenario",
    )
    run = scenarios[selected]
    trends = run.trends
    day = st.selectbox(
        t(language, "plant.day"),
        sorted(trends.timestamp.dt.date.unique()),
        format_func=lambda value: format_day(value, language),
        key="plant_day",
    )
    view = trends.loc[trends.timestamp.dt.date == day]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t(language, "metric.energy"), f"{run.metrics.energy_kwh:.1f} kWh")
    c2.metric(t(language, "metric.peak"), f"{run.metrics.peak_kw:.2f} kW")
    c3.metric(t(language, "metric.runtime"), f"{run.metrics.runtime_hours:.1f} h")
    c4.metric(t(language, "metric.comfort"), f"{run.metrics.occupied_comfort_pct:.1f}%")

    st.subheader(t(language, "plant.temperatures"))
    st.line_chart(
        view.set_index("timestamp")[
            ["east_temp_measured_c", "west_temp_measured_c", "target_east_c"]
        ],
        color=["#176b87", "#7b2cbf", "#6c757d"],
    )
    left, right = st.columns(2)
    with left:
        st.subheader(t(language, "plant.power"))
        st.line_chart(
            view.set_index("timestamp")[["hvac_power_kw", "chiller_power_kw", "fan_power_kw"]]
        )
    with right:
        st.subheader(t(language, "plant.command_feedback"))
        st.line_chart(
            view.set_index("timestamp")[["cooling_cmd_east", "valve_east", "airflow_east"]]
        )

    with st.expander(t(language, "plant.equations")):
        st.latex(r"T_{k+1}=T_k+\frac{\Delta t}{C}\left(\frac{T_o-T_k}{R}+Q_{int}+Q_{solar}-Q_{cool}\right)")
        st.latex(r"P_{fan}=P_{rated}\,u_{air}^{3},\qquad P_{chiller}=Q_{cool}/COP")
        st.caption(t(language, "plant.units"))


def render_optimization(bundle: ScenarioBundle, language: str) -> None:
    _page_header("energy_optimization", "optimization.subtitle", language)
    st.dataframe(
        localize_frame(bundle.comparison.round(3), language),
        hide_index=True,
        width="stretch",
    )
    metrics = bundle.comparison.set_index("scenario")
    left, right = st.columns(2)
    with left:
        st.subheader(t(language, "optimization.energy"))
        st.bar_chart(metrics[["energy_kwh"]], color="#2a9d8f")
    with right:
        st.subheader(t(language, "optimization.peak"))
        st.bar_chart(metrics[["peak_kw"]], color="#176b87")

    st.subheader(t(language, "optimization.why"))
    comparison = pd.DataFrame(
        {
            "timestamp": bundle.baseline.trends.timestamp,
            "baseline": bundle.baseline.trends.hvac_power_kw,
            "optimized": bundle.optimized.trends.hvac_power_kw,
        }
    ).set_index("timestamp")
    st.line_chart(comparison)
    st.markdown(
        t(
            language,
            "optimization.explanation",
            saving=metrics.loc["optimized", "energy_savings_pct"],
        )
    )
    st.download_button(
        t(language, "optimization.download"),
        bundle.comparison.to_csv(index=False).encode("utf-8"),
        "scenario-comparison.csv",
        "text/csv",
    )


def render_data_quality(bundle: ScenarioBundle, language: str) -> None:
    _page_header("data_quality", "quality.subtitle", language)
    st.info(t(language, "quality.disclosure"))
    st.caption(t(language, "quality.privacy"))

    sample_frame = bundle.baseline.trends
    st.download_button(
        t(language, "quality.sample_download"),
        data=_csv_bytes(sample_frame),
        file_name=QUALITY_DOWNLOAD_FILENAMES["sample"],
        mime="text/csv",
        key="quality_sample_download",
    )
    uploaded = st.file_uploader(
        t(language, "quality.upload"),
        type=("csv",),
        help=t(language, "quality.upload_help"),
        key="quality_upload",
    )

    try:
        ingestion = (
            ingest_csv_bytes(uploaded.getvalue())
            if uploaded is not None
            else canonicalize_trend_frame(sample_frame)
        )
    except TrendIngestionError as error:
        st.error(_quality_error_message(error, language))
        return

    st.caption(
        t(
            language,
            "quality.source_upload" if uploaded is not None else "quality.source_sample",
        )
    )
    result = screen_trends(ingestion.frame)
    report = result.quality
    ready_count = sum(item.eligible for item in report.readiness)
    interval = (
        f"{report.sampling_interval_minutes:g} min"
        if report.sampling_interval_minutes is not None
        else "—"
    )
    metrics = st.columns(4)
    metrics[0].metric(t(language, "quality.rows"), f"{report.row_count:,}")
    metrics[1].metric(t(language, "quality.interval"), interval)
    metrics[2].metric(t(language, "quality.score"), f"{report.score:.1f}/100")
    metrics[3].metric(
        t(language, "quality.ready_rules"),
        f"{ready_count}/{len(report.readiness)}",
    )

    st.subheader(t(language, "quality.checks"))
    st.dataframe(
        localize_frame(checks_frame(report), language),
        hide_index=True,
        width="stretch",
    )

    st.subheader(t(language, "quality.issues"))
    issue_data = issues_frame(report)
    if issue_data.empty:
        st.success(t(language, "quality.no_issues"))
    else:
        st.dataframe(
            localize_frame(issue_data, language),
            hide_index=True,
            width="stretch",
        )

    st.subheader(t(language, "quality.readiness"))
    st.dataframe(
        localize_frame(readiness_frame(report), language),
        hide_index=True,
        width="stretch",
    )

    st.subheader(t(language, "quality.findings"))
    if result.findings:
        st.dataframe(
            localize_findings_frame(result.findings, language),
            hide_index=True,
            width="stretch",
        )
    else:
        st.success(t(language, "quality.no_findings"))
    st.warning(t(language, "quality.screening_disclosure"))

    st.subheader(t(language, "quality.preview"))
    st.dataframe(
        localize_frame(result.frame.head(100), language),
        hide_index=True,
        width="stretch",
    )
    left, right = st.columns(2)
    left.download_button(
        t(language, "quality.normalized_download"),
        data=_csv_bytes(result.frame),
        file_name=QUALITY_DOWNLOAD_FILENAMES["normalized"],
        mime="text/csv",
        key="quality_normalized_download",
    )
    right.download_button(
        t(language, "quality.report_download"),
        data=_csv_bytes(quality_report_frame(report)),
        file_name=QUALITY_DOWNLOAD_FILENAMES["report"],
        mime="text/csv",
        key="quality_report_download",
    )


def render_rcx(bundle: ScenarioBundle, language: str) -> None:
    _page_header("rcx_diagnostics", "rcx.subtitle", language)
    st.dataframe(
        localize_frame(bundle.diagnostic_scorecard, language),
        hide_index=True,
        width="stretch",
    )
    category = st.selectbox(
        t(language, "rcx.injected_fault"),
        list(bundle.fault_runs),
        format_func=lambda value: fault_label(value, language),
        key="rcx_fault",
    )
    run = bundle.fault_runs[category]
    finding_frame = localize_findings_frame(run.findings, language)
    st.dataframe(finding_frame, hide_index=True, width="stretch")
    finding = next(item for item in run.findings if item.category == category)
    localized_finding = localize_findings_frame([finding], language).iloc[0]
    recommendation = localized_finding[column_label("recommendation", language)]
    c1, c2, c3 = st.columns(3)
    c1.metric(t(language, "rcx.severity"), severity_label(finding.severity, language))
    c2.metric(t(language, "rcx.confidence"), f"{finding.confidence:.0%}")
    c3.metric(t(language, "rcx.impact"), f"{finding.estimated_waste_kwh:.2f} kWh")
    st.success(t(language, "rcx.action", recommendation=recommendation))

    active = run.trends.loc[run.trends.fault_active]
    padding = pd.Timedelta(hours=2)
    view = run.trends.loc[
        (run.trends.timestamp >= active.timestamp.min() - padding)
        & (run.trends.timestamp <= active.timestamp.max() + padding)
    ]
    numeric_evidence = [column for column in finding.evidence_columns if column in view and pd.api.types.is_numeric_dtype(view[column])]
    st.subheader(t(language, "rcx.evidence"))
    st.line_chart(view.set_index("timestamp")[numeric_evidence])
    st.caption(
        t(
            language,
            "rcx.window",
            start=active.timestamp.min(),
            end=active.timestamp.max(),
            detected=finding.detected_at,
        )
    )


def render_points_alarms(bundle: ScenarioBundle, language: str) -> None:
    _page_header("bms_points_alarms", "points.subtitle", language)
    equipment = st.multiselect(
        t(language, "points.equipment_filter"),
        sorted(bundle.point_registry.equipment.unique()),
        default=sorted(bundle.point_registry.equipment.unique()),
        key="points_equipment",
    )
    points = bundle.point_registry.loc[bundle.point_registry.equipment.isin(equipment)]
    st.dataframe(localize_frame(points, language), hide_index=True, width="stretch")
    st.download_button(
        t(language, "points.download"),
        points.to_csv(index=False).encode("utf-8"),
        "bms-point-registry.csv",
        "text/csv",
    )

    st.subheader(t(language, "points.alarms"))
    scenarios = _scenario_map(bundle)
    selected = st.selectbox(
        t(language, "points.alarm_scenario"),
        list(scenarios),
        index=2,
        format_func=lambda value: scenario_label(value, language),
        key="alarm_scenario",
    )
    alarms = _alarms_frame(scenarios[selected])
    priorities = sorted(alarms.priority.unique()) if not alarms.empty else []
    selected_priorities = st.multiselect(
        t(language, "points.priority"),
        priorities,
        default=priorities,
        key="alarm_priority",
    )
    filtered = alarms.loc[alarms.priority.isin(selected_priorities)] if priorities else alarms
    st.dataframe(
        localize_frame(filtered.head(500), language),
        hide_index=True,
        width="stretch",
    )


def render_learning_lab(bundle: ScenarioBundle, language: str) -> None:
    _page_header("learning_lab", "learning.subtitle", language)
    for position in range(1, 6):
        with st.expander(t(language, f"learning.experiment.{position}.title")):
            st.write(t(language, f"learning.experiment.{position}.text"))

    st.subheader(t(language, "learning.blind"))
    categories = tuple(bundle.fault_runs)
    hidden_labels = _hidden_fault_labels(categories, language)
    category = st.selectbox(
        t(language, "learning.select_set"),
        categories,
        format_func=hidden_labels.__getitem__,
        key="learning_evidence_set",
    )
    run = bundle.fault_runs[category]
    active = run.trends.loc[run.trends.fault_active]
    signals = st.multiselect(
        t(language, "learning.signals"),
        [
            "east_temp_measured_c",
            "east_temp_reference_c",
            "cooling_cmd_east",
            "valve_east",
            "airflow_cmd_east",
            "airflow_east",
            "fan_power_kw",
            "expected_fan_power_kw",
            "hvac_power_kw",
        ],
        default=["cooling_cmd_east", "valve_east", "hvac_power_kw"],
        key="learning_signals",
    )
    window = run.trends.loc[
        (run.trends.timestamp >= active.timestamp.min() - pd.Timedelta(hours=1))
        & (run.trends.timestamp <= active.timestamp.max() + pd.Timedelta(hours=1))
    ]
    st.line_chart(window.set_index("timestamp")[signals])
    hypothesis = st.text_area(
        t(language, "learning.hypothesis"), key="learning_hypothesis"
    )
    if st.button(
        t(language, "learning.reveal"),
        disabled=not hypothesis.strip(),
        key="learning_reveal",
    ):
        finding = next(item for item in run.findings if item.category == category)
        localized = localize_findings_frame([finding], language).iloc[0]
        title = localized[column_label("title", language)]
        evidence = localized[column_label("evidence", language)]
        recommendation = localized[column_label("recommendation", language)]
        st.info(f"{title}: {evidence}. {recommendation}")


def main() -> None:
    st.set_page_config(
        page_title="SmartBMS-RCx",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {background: linear-gradient(180deg,#102a43 0%,#163f5c 100%);}
        [data-testid="stSidebar"] * {color:#f4f8fb;}
        div[data-testid="stMetric"] {background:#f7fafc;border:1px solid #d9e2ec;padding:14px;border-radius:12px;}
        .stAlert {border-radius:10px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    language = st.sidebar.radio(
        "语言 / Language",
        tuple(LANGUAGE_NAMES),
        index=0,
        format_func=LANGUAGE_NAMES.__getitem__,
        key="language",
    )
    st.sidebar.markdown("## SmartBMS-RCx")
    st.sidebar.caption(t(language, "sidebar.version"))
    page_id = st.sidebar.radio(
        t(language, "sidebar.navigate"),
        PAGE_IDS,
        format_func=lambda value: page_label(value, language),
        key="page_id",
    )
    st.sidebar.divider()
    st.sidebar.info(t(language, "sidebar.disclosure"))
    with st.spinner(t(language, "app.loading")):
        bundle = load_bundle()
    renderers = {
        "overview": render_overview,
        "plant_control": render_plant_control,
        "energy_optimization": render_optimization,
        "data_quality": render_data_quality,
        "rcx_diagnostics": render_rcx,
        "bms_points_alarms": render_points_alarms,
        "learning_lab": render_learning_lab,
    }
    renderers[page_id](bundle, language)


if __name__ == "__main__":
    main()
