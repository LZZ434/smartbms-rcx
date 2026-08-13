"""Persistent RCx diagnostic rules with evidence and corrective actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DiagnosticFinding:
    category: str
    title: str
    detected_at: pd.Timestamp
    severity: str
    confidence: float
    evidence: str
    evidence_columns: tuple[str, ...]
    estimated_waste_kwh: float
    recommendation: str


FINDING_COLUMNS = (
    "category",
    "title",
    "detected_at",
    "severity",
    "confidence",
    "evidence",
    "evidence_columns",
    "estimated_waste_kwh",
    "recommendation",
)

DIAGNOSTIC_CATEGORIES = (
    "sensor_bias",
    "stuck_valve",
    "fouled_filter",
    "after_hours_operation",
)

REQUIRED_COLUMNS_BY_CATEGORY = {
    "sensor_bias": frozenset(
        {"timestamp", "east_temp_measured_c", "east_temp_reference_c"}
    ),
    "stuck_valve": frozenset(
        {
            "timestamp",
            "cooling_cmd_east",
            "valve_east",
            "east_temp_measured_c",
        }
    ),
    "fouled_filter": frozenset(
        {
            "timestamp",
            "airflow_cmd_east",
            "airflow_east",
            "fan_power_kw",
            "expected_fan_power_kw",
        }
    ),
    "after_hours_operation": frozenset(
        {
            "timestamp",
            "occupied",
            "preconditioning_authorized",
            "cooling_cmd_east",
            "hvac_power_kw",
        }
    ),
}


def _require_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(f"diagnostic trends are missing columns: {sorted(missing)}")


def _first_persistent_position(mask: pd.Series, samples: int) -> int | None:
    persistent = mask.astype(int).rolling(samples, min_periods=samples).sum() >= samples
    positions = np.flatnonzero(persistent.to_numpy())
    return int(positions[0]) if positions.size else None


def _select_categories(categories: Iterable[str] | None) -> tuple[str, ...]:
    selected = (
        DIAGNOSTIC_CATEGORIES
        if categories is None
        else tuple(dict.fromkeys(categories))
    )
    unknown = sorted(set(selected).difference(DIAGNOSTIC_CATEGORIES))
    if unknown:
        raise ValueError(f"unsupported diagnostic categories: {unknown}")
    return selected


def run_diagnostics(
    trends: pd.DataFrame,
    *,
    categories: Iterable[str] | None = None,
    persistence_samples: int = 4,
    timestep_minutes: int = 15,
    nominal_zone_cooling_kw: float = 24.0,
    nominal_chiller_cop: float = 3.6,
) -> list[DiagnosticFinding]:
    """Run four transparent RCx rules over a trend DataFrame."""

    selected = _select_categories(categories)
    required = set().union(
        *(REQUIRED_COLUMNS_BY_CATEGORY[category] for category in selected)
    )
    _require_columns(trends, required)
    if persistence_samples < 1:
        raise ValueError("persistence_samples must be positive")
    if not isfinite(nominal_zone_cooling_kw) or nominal_zone_cooling_kw <= 0:
        raise ValueError("nominal_zone_cooling_kw must be positive and finite")
    if not isfinite(nominal_chiller_cop) or nominal_chiller_cop <= 0:
        raise ValueError("nominal_chiller_cop must be positive and finite")
    dt_hours = timestep_minutes / 60.0
    findings: list[DiagnosticFinding] = []

    if "sensor_bias" in selected:
        residual = trends["east_temp_measured_c"] - trends["east_temp_reference_c"]
        sensor_mask = residual.abs() > 1.2
        position = _first_persistent_position(sensor_mask, persistence_samples)
        if position is not None:
            mean_residual = float(residual[sensor_mask].mean())
            findings.append(
                DiagnosticFinding(
                    category="sensor_bias",
                    title="East-zone temperature sensor bias",
                    detected_at=pd.Timestamp(trends.iloc[position]["timestamp"]),
                    severity="medium",
                    confidence=min(0.99, 0.70 + abs(mean_residual) / 10),
                    evidence=f"Measured-minus-reference residual averaged {mean_residual:+.2f} °C",
                    evidence_columns=("east_temp_measured_c", "east_temp_reference_c"),
                    estimated_waste_kwh=round(
                        float(residual[sensor_mask].abs().sum()) * dt_hours * 0.08,
                        3,
                    ),
                    recommendation="Calibrate the sensor against a traceable reference and verify wiring/offset settings.",
                )
            )

    if "stuck_valve" in selected:
        valve_gap = trends["cooling_cmd_east"] - trends["valve_east"]
        valve_mask = (trends["cooling_cmd_east"] > 0.45) & (valve_gap > 0.30)
        position = _first_persistent_position(valve_mask, persistence_samples)
        if position is not None:
            mean_gap = float(valve_gap[valve_mask].mean())
            findings.append(
                DiagnosticFinding(
                    category="stuck_valve",
                    title="East cooling-valve command/feedback mismatch",
                    detected_at=pd.Timestamp(trends.iloc[position]["timestamp"]),
                    severity="high",
                    confidence=min(0.99, 0.72 + mean_gap / 2),
                    evidence=f"Valve feedback remained {mean_gap:.2f} fraction below command",
                    evidence_columns=(
                        "cooling_cmd_east",
                        "valve_east",
                        "east_temp_measured_c",
                    ),
                    estimated_waste_kwh=round(
                        float(valve_gap[valve_mask].sum())
                        * nominal_zone_cooling_kw
                        * dt_hours
                        / nominal_chiller_cop,
                        3,
                    ),
                    recommendation="Inspect actuator linkage and valve stroke; then command a full open/close functional test.",
                )
            )

    if "fouled_filter" in selected:
        airflow_ratio = trends["airflow_east"] / trends["airflow_cmd_east"].clip(
            lower=0.05
        )
        fan_ratio = trends["fan_power_kw"] / trends["expected_fan_power_kw"].clip(
            lower=0.05
        )
        filter_mask = (
            (trends["airflow_cmd_east"] > 0.40)
            & (airflow_ratio < 0.72)
            & (fan_ratio > 1.18)
        )
        position = _first_persistent_position(filter_mask, persistence_samples)
        if position is not None:
            mean_airflow_ratio = float(airflow_ratio[filter_mask].mean())
            excess_power = (
                trends["fan_power_kw"] - trends["expected_fan_power_kw"]
            ).clip(lower=0)
            findings.append(
                DiagnosticFinding(
                    category="fouled_filter",
                    title="AHU airflow degradation with excess fan power",
                    detected_at=pd.Timestamp(trends.iloc[position]["timestamp"]),
                    severity="medium",
                    confidence=min(0.99, 0.72 + (1 - mean_airflow_ratio) / 2),
                    evidence=f"Airflow/command ratio averaged {mean_airflow_ratio:.2f} while fan power exceeded expectation",
                    evidence_columns=(
                        "airflow_cmd_east",
                        "airflow_east",
                        "fan_power_kw",
                        "expected_fan_power_kw",
                    ),
                    estimated_waste_kwh=round(
                        float(excess_power[filter_mask].sum()) * dt_hours,
                        3,
                    ),
                    recommendation="Check filter differential pressure, inspect blockage, and replace the filter if confirmed.",
                )
            )

    if "after_hours_operation" in selected:
        west_command = trends.get("cooling_cmd_west", trends["cooling_cmd_east"])
        authorized_preconditioning = trends["preconditioning_authorized"].astype(bool)
        largest_command = pd.concat(
            [trends["cooling_cmd_east"], west_command], axis=1
        ).max(axis=1)
        after_hours_mask = (
            (~trends["occupied"].astype(bool))
            & (~authorized_preconditioning)
            & (largest_command > 0.55)
            & (trends["hvac_power_kw"] > 1.5)
        )
        position = _first_persistent_position(after_hours_mask, persistence_samples)
        if position is not None:
            waste = (
                float(trends.loc[after_hours_mask, "hvac_power_kw"].sum())
                * dt_hours
            )
            findings.append(
                DiagnosticFinding(
                    category="after_hours_operation",
                    title="HVAC operation outside occupied schedule",
                    detected_at=pd.Timestamp(trends.iloc[position]["timestamp"]),
                    severity="high",
                    confidence=0.96,
                    evidence=f"Detected {int(after_hours_mask.sum())} unoccupied samples above 1.5 kW",
                    evidence_columns=(
                        "occupied",
                        "cooling_cmd_east",
                        "hvac_power_kw",
                    ),
                    estimated_waste_kwh=round(waste, 3),
                    recommendation="Correct the BMS schedule and add an after-hours enable timeout with exception logging.",
                )
            )
    return findings


def findings_to_frame(findings: list[DiagnosticFinding]) -> pd.DataFrame:
    if not findings:
        return pd.DataFrame(columns=FINDING_COLUMNS)
    frame = pd.DataFrame(asdict(finding) for finding in findings)
    frame["evidence_columns"] = frame["evidence_columns"].map(lambda values: ", ".join(values))
    return frame.loc[:, FINDING_COLUMNS]
