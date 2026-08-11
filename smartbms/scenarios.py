"""End-to-end orchestration for healthy, optimized, and faulted scenarios."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from smartbms.config import ProjectConfig
from smartbms.controllers import (
    BaselineController,
    PredictiveController,
    ZoneObservation,
)
from smartbms.diagnostics import DiagnosticFinding, run_diagnostics
from smartbms.faults import FaultType, apply_fault, fault_is_active
from smartbms.metrics import MetricSummary, calculate_metrics, comparison_frame
from smartbms.plant import TwoZonePlant
from smartbms.points import AlarmEvent, evaluate_alarms, points_to_frame
from smartbms.weather import generate_inputs


@dataclass(frozen=True)
class ScenarioRun:
    name: str
    strategy: str
    expected_fault: str | None
    trends: pd.DataFrame
    metrics: MetricSummary
    alarms: tuple[AlarmEvent, ...]
    findings: tuple[DiagnosticFinding, ...]


@dataclass(frozen=True)
class ScenarioBundle:
    baseline: ScenarioRun
    optimized: ScenarioRun
    fault_runs: dict[str, ScenarioRun]
    comparison: pd.DataFrame
    diagnostic_scorecard: pd.DataFrame
    point_registry: pd.DataFrame


def _measurement(true_temp_c: float, fault: FaultType | None, active: bool, config: ProjectConfig) -> float:
    effect = apply_fault(
        fault if active else None,
        true_temp_c,
        command=0,
        airflow=0,
        power_kw=0,
        config=config.faults,
    )
    return effect.measured_temp_c


def run_scenario(
    config: ProjectConfig,
    *,
    name: str,
    strategy: str,
    fault: FaultType | None = None,
) -> ScenarioRun:
    """Simulate one deterministic scenario and derive alarms/RCx findings."""

    inputs = generate_inputs(config.simulation)
    plant = TwoZonePlant(config)
    if strategy == "baseline":
        controller = BaselineController(config.controller)
    elif strategy == "predictive":
        controller = PredictiveController(config.controller, config.plant)
    else:
        raise ValueError("strategy must be 'baseline' or 'predictive'")

    records: list[dict[str, object]] = []
    alarms: list[AlarmEvent] = []
    forecast_steps = max(
        1,
        round(
            config.controller.pre_cooling_hours
            * 60
            / config.simulation.timestep_minutes
        ),
    )
    for position, row in inputs.iterrows():
        timestamp = pd.Timestamp(row["timestamp"])
        active = fault is not None and fault_is_active(fault, timestamp.to_pydatetime())
        east_measured_before = _measurement(plant.east_temp_c, fault, active, config)
        observation = ZoneObservation(
            east_temp_c=east_measured_before,
            west_temp_c=plant.west_temp_c,
            occupied=bool(row["occupied"]),
            outdoor_temp_c=float(row["outdoor_temp_c"]),
            hour=timestamp.hour + timestamp.minute / 60.0,
        )
        occupancy_next = 0.0
        preconditioning_authorized = False
        if strategy == "predictive":
            forecast_position = min(position + forecast_steps, len(inputs) - 1)
            forecast = inputs.iloc[forecast_position]
            occupancy_next = max(
                float(forecast["occupancy_east"]),
                float(forecast["occupancy_west"]),
            )
            preconditioning_authorized = bool(
                not row["occupied"] and occupancy_next >= 0.15
            )
            action = controller.act(
                observation,
                occupancy_next_hour=occupancy_next,
                outdoor_temp_next_hour_c=float(forecast["outdoor_temp_c"]),
            )
        else:
            action = controller.act(observation)

        effect = apply_fault(
            fault if active else None,
            plant.east_temp_c,
            command=action.cooling_east,
            airflow=action.airflow_east,
            power_kw=0,
            config=config.faults,
        )
        snapshot = plant.step(
            outdoor_temp_c=float(row["outdoor_temp_c"]),
            internal_gains_kw=(
                float(row["internal_gain_east_kw"]),
                float(row["internal_gain_west_kw"]),
            ),
            solar_gains_kw=(
                float(row["solar_gain_east_kw"]),
                float(row["solar_gain_west_kw"]),
            ),
            cooling_commands=(effect.command, action.cooling_west),
            airflow_commands=(effect.commanded_airflow, action.airflow_west),
            actual_valve_positions=(effect.actual_valve_position, action.cooling_west),
            airflow_multipliers=(effect.airflow_multiplier, 1.0),
            fan_power_multiplier=effect.fan_power_multiplier,
        )
        actual_average_airflow = (snapshot.airflow_east + snapshot.airflow_west) / 2.0
        expected_fan_power = 0.0
        if actual_average_airflow > 0:
            expected_fan_power = (
                config.plant.fan_idle_kw
                + config.plant.rated_fan_kw * actual_average_airflow**3
            )
        east_measured_after = _measurement(snapshot.east_temp_c, fault, active, config)
        record: dict[str, object] = {
            "timestamp": timestamp,
            "scenario": name,
            "strategy": strategy,
            "synthetic": True,
            "outdoor_temp_c": float(row["outdoor_temp_c"]),
            "humidity_pct": float(row["humidity_pct"]),
            "solar_w_m2": float(row["solar_w_m2"]),
            "occupancy_east": float(row["occupancy_east"]),
            "occupancy_west": float(row["occupancy_west"]),
            "occupied": bool(row["occupied"]),
            "occupancy_next_hour": occupancy_next,
            "preconditioning_authorized": preconditioning_authorized,
            "internal_gain_east_kw": float(row["internal_gain_east_kw"]),
            "internal_gain_west_kw": float(row["internal_gain_west_kw"]),
            "solar_gain_east_kw": float(row["solar_gain_east_kw"]),
            "solar_gain_west_kw": float(row["solar_gain_west_kw"]),
            "east_temp_true_c": snapshot.east_temp_c,
            "west_temp_true_c": snapshot.west_temp_c,
            "east_temp_measured_c": east_measured_after,
            "west_temp_measured_c": snapshot.west_temp_c,
            "east_temp_reference_c": snapshot.east_temp_c,
            "target_east_c": action.target_east_c,
            "target_west_c": action.target_west_c,
            "cooling_cmd_east": effect.command,
            "cooling_cmd_west": action.cooling_west,
            "valve_east": snapshot.valve_east,
            "valve_west": snapshot.valve_west,
            "airflow_cmd_east": effect.commanded_airflow,
            "airflow_cmd_west": action.airflow_west,
            "airflow_east": snapshot.airflow_east,
            "airflow_west": snapshot.airflow_west,
            "cooling_east_kw": snapshot.cooling_east_kw,
            "cooling_west_kw": snapshot.cooling_west_kw,
            "chiller_power_kw": snapshot.chiller_power_kw,
            "fan_power_kw": snapshot.fan_power_kw,
            "expected_fan_power_kw": expected_fan_power,
            "hvac_power_kw": snapshot.hvac_power_kw,
            "effective_cop": snapshot.effective_cop,
            "projected_power_kw": action.projected_power_kw,
            "objective_score": action.objective_score,
            "controller_fallback": action.fallback_used,
            "fault_type": fault.value if fault is not None else "healthy",
            "fault_active": active,
        }
        records.append(record)
        alarms.extend(evaluate_alarms(record, timestamp.to_pydatetime()))

    trends = pd.DataFrame.from_records(records)
    trends.attrs.update(
        {
            "synthetic": True,
            "scenario": name,
            "strategy": strategy,
            "disclosure": "Synthetic simulation; not measured building performance.",
            "weather_reference": inputs.attrs["weather_reference"],
            "seed": config.simulation.seed,
        }
    )
    findings = tuple(
        run_diagnostics(
            trends,
            timestep_minutes=config.simulation.timestep_minutes,
            nominal_zone_cooling_kw=config.plant.east.max_cooling_kw,
            nominal_chiller_cop=config.plant.chiller_cop,
        )
    )
    metrics = calculate_metrics(
        trends,
        timestep_minutes=config.simulation.timestep_minutes,
        tariff=config.tariff,
        scenario=name,
    )
    return ScenarioRun(
        name=name,
        strategy=strategy,
        expected_fault=fault.value if fault is not None else None,
        trends=trends,
        metrics=metrics,
        alarms=tuple(alarms),
        findings=findings,
    )


def _diagnostic_scorecard(fault_runs: dict[str, ScenarioRun]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for expected, run in fault_runs.items():
        matching = [finding for finding in run.findings if finding.category == expected]
        active_timestamps = run.trends.loc[run.trends["fault_active"], "timestamp"]
        detected = bool(matching)
        delay = None
        if detected and not active_timestamps.empty:
            delay = (
                pd.Timestamp(matching[0].detected_at) - pd.Timestamp(active_timestamps.iloc[0])
            ).total_seconds() / 60.0
        unexpected = len([finding for finding in run.findings if finding.category != expected])
        rows.append(
            {
                "scenario": run.name,
                "expected_fault": expected,
                "detected": detected,
                "detection_delay_minutes": delay,
                "unexpected_findings": unexpected,
                "finding_count": len(run.findings),
            }
        )
    return pd.DataFrame(rows)


def run_portfolio_scenarios(config: ProjectConfig | None = None) -> ScenarioBundle:
    """Run the complete deterministic portfolio scenario suite."""

    settings = config or ProjectConfig()
    baseline = run_scenario(settings, name="baseline", strategy="baseline")
    optimized = run_scenario(settings, name="optimized", strategy="predictive")
    fault_runs: dict[str, ScenarioRun] = {}
    for fault in FaultType:
        run = run_scenario(
            settings,
            name=f"fault-{fault.value}",
            strategy="baseline",
            fault=fault,
        )
        fault_runs[fault.value] = run
    point_registry = points_to_frame().assign(connection="simulated")
    return ScenarioBundle(
        baseline=baseline,
        optimized=optimized,
        fault_runs=fault_runs,
        comparison=comparison_frame(baseline.metrics, optimized.metrics),
        diagnostic_scorecard=_diagnostic_scorecard(fault_runs),
        point_registry=point_registry,
    )
