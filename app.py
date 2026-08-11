"""Streamlit dashboard for the SmartBMS-RCx synthetic portfolio project."""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from smartbms.diagnostics import findings_to_frame
from smartbms.i18n import (
    LANGUAGE_NAMES,
    PAGE_IDS,
    format_day,
    page_label,
    scenario_label,
    t,
)
from smartbms.reporting import render_html_report, render_markdown_report
from smartbms.scenarios import ScenarioBundle, ScenarioRun, run_portfolio_scenarios


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


def _hidden_fault_labels(categories: tuple[str, ...]) -> dict[str, str]:
    """Give blind-drill choices unique labels without revealing fault names."""

    return {
        category: f"Evidence set {chr(ord('A') + position)}"
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
        file_name=f"smartbms-rcx-report-{language}.html",
        mime="text/html",
        width="stretch",
    )
    right.download_button(
        t(language, "download.markdown"),
        data=render_markdown_report(bundle, language=language),
        file_name=f"smartbms-rcx-report-{language}.md",
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
    st.title("Energy Optimization")
    st.caption(
        "Measured from identical deterministic inputs; optimization is a bounded candidate search, not deep learning."
    )
    st.dataframe(bundle.comparison.round(3), hide_index=True, width="stretch")
    metrics = bundle.comparison.set_index("scenario")
    left, right = st.columns(2)
    with left:
        st.subheader("Energy (kWh)")
        st.bar_chart(metrics[["energy_kwh"]], color="#2a9d8f")
    with right:
        st.subheader("Peak demand (kW)")
        st.bar_chart(metrics[["peak_kw"]], color="#176b87")

    st.subheader("Why energy changed")
    comparison = pd.DataFrame(
        {
            "timestamp": bundle.baseline.trends.timestamp,
            "baseline": bundle.baseline.trends.hvac_power_kw,
            "optimized": bundle.optimized.trends.hvac_power_kw,
        }
    ).set_index("timestamp")
    st.line_chart(comparison)
    st.markdown(
        f"""
        The optimized controller uses a one-hour weather/occupancy look-ahead, authorized pre-cooling,
        relaxed unoccupied operation, and a comfort penalty. In this fixed synthetic week it reduces
        energy by **{metrics.loc['optimized', 'energy_savings_pct']:.3f}%** while keeping all occupied
        zone-samples inside 22–26 °C. The result is not transferable to a real site without calibration.
        """
    )
    st.download_button(
        "Download comparison CSV",
        bundle.comparison.to_csv(index=False).encode("utf-8"),
        "scenario-comparison.csv",
        "text/csv",
    )


def render_rcx(bundle: ScenarioBundle, language: str) -> None:
    st.title("RCx Diagnostics")
    st.caption("Four-sample persistence, explicit evidence, and corrective action.")
    st.dataframe(bundle.diagnostic_scorecard, hide_index=True, width="stretch")
    category = st.selectbox(
        "Injected fault",
        list(bundle.fault_runs),
        format_func=lambda value: value.replace("_", " ").title(),
    )
    run = bundle.fault_runs[category]
    finding_frame = findings_to_frame(list(run.findings))
    st.dataframe(finding_frame, hide_index=True, width="stretch")
    finding = next(item for item in run.findings if item.category == category)
    c1, c2, c3 = st.columns(3)
    c1.metric("Severity", finding.severity.title())
    c2.metric("Confidence", f"{finding.confidence:.0%}")
    c3.metric("Estimated impact", f"{finding.estimated_waste_kwh:.2f} kWh")
    st.success(f"Recommended action: {finding.recommendation}")

    active = run.trends.loc[run.trends.fault_active]
    padding = pd.Timedelta(hours=2)
    view = run.trends.loc[
        (run.trends.timestamp >= active.timestamp.min() - padding)
        & (run.trends.timestamp <= active.timestamp.max() + padding)
    ]
    numeric_evidence = [column for column in finding.evidence_columns if column in view and pd.api.types.is_numeric_dtype(view[column])]
    st.subheader("Evidence around the injected window")
    st.line_chart(view.set_index("timestamp")[numeric_evidence])
    st.caption(f"Fault active: {active.timestamp.min()} to {active.timestamp.max()} · detected: {finding.detected_at}")


def render_points_alarms(bundle: ScenarioBundle, language: str) -> None:
    st.title("BMS Points & Alarms")
    st.caption(
        "Simulated protocol semantics for interview discussion—no BACnet/Modbus client is connected."
    )
    equipment = st.multiselect(
        "Equipment filter",
        sorted(bundle.point_registry.equipment.unique()),
        default=sorted(bundle.point_registry.equipment.unique()),
    )
    points = bundle.point_registry.loc[bundle.point_registry.equipment.isin(equipment)]
    st.dataframe(points, hide_index=True, width="stretch")
    st.download_button(
        "Download point registry",
        points.to_csv(index=False).encode("utf-8"),
        "bms-point-registry.csv",
        "text/csv",
    )

    st.subheader("Alarm event explorer")
    scenarios = _scenario_map(bundle)
    selected = st.selectbox("Alarm scenario", list(scenarios), index=2)
    alarms = _alarms_frame(scenarios[selected])
    priorities = sorted(alarms.priority.unique()) if not alarms.empty else []
    selected_priorities = st.multiselect("Priority", priorities, default=priorities)
    filtered = alarms.loc[alarms.priority.isin(selected_priorities)] if priorities else alarms
    st.dataframe(filtered.head(500), hide_index=True, width="stretch")


def render_learning_lab(bundle: ScenarioBundle, language: str) -> None:
    st.title("Learning Lab")
    st.caption(
        "Use five guided experiments to turn generated code into your own engineering knowledge."
    )
    experiments = (
        (
            "1 · Verify the fan cubic law",
            "Open Plant & Control, compare airflow and fan power, then calculate whether doubling airflow can approach eight times the variable fan power.",
        ),
        (
            "2 · Explain the baseline comfort gap",
            "Find the first occupied hour. Explain thermal inertia and why a schedule-only controller starts cooling later than the predictive controller.",
        ),
        (
            "3 · Audit the savings claim",
            "Download both trend CSVs and recompute Σ(power × 0.25 h). Confirm the 5.623% result before using it on a résumé.",
        ),
        (
            "4 · Diagnose one fault blind",
            "Hide the fault name, inspect command/feedback/power trends, state a hypothesis, evidence, and maintenance test, then compare with the finding.",
        ),
        (
            "5 · Map a point end to end",
            "Pick ZN-E-T or VLV-E-FBK, trace engineering unit, BACnet object, Modbus register, alarm rule, trend column, and dashboard use.",
        ),
    )
    for title, instructions in experiments:
        with st.expander(title):
            st.write(instructions)

    st.subheader("Blind fault drill")
    categories = tuple(bundle.fault_runs)
    hidden_labels = _hidden_fault_labels(categories)
    category = st.selectbox(
        "Select evidence set",
        categories,
        format_func=hidden_labels.__getitem__,
    )
    run = bundle.fault_runs[category]
    active = run.trends.loc[run.trends.fault_active]
    signals = st.multiselect(
        "Signals",
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
    )
    window = run.trends.loc[
        (run.trends.timestamp >= active.timestamp.min() - pd.Timedelta(hours=1))
        & (run.trends.timestamp <= active.timestamp.max() + pd.Timedelta(hours=1))
    ]
    st.line_chart(window.set_index("timestamp")[signals])
    hypothesis = st.text_area("Your hypothesis and next physical test")
    if st.button("Reveal answer", disabled=not hypothesis.strip()):
        finding = next(item for item in run.findings if item.category == category)
        st.info(f"{finding.title}: {finding.evidence}. {finding.recommendation}")


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
        "rcx_diagnostics": render_rcx,
        "bms_points_alarms": render_points_alarms,
        "learning_lab": render_learning_lab,
    }
    renderers[page_id](bundle, language)


if __name__ == "__main__":
    main()
