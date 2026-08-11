"""Deterministic synthetic fault definitions and physical/sensor effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from smartbms.config import FaultConfig


class FaultType(str, Enum):
    SENSOR_BIAS = "sensor_bias"
    STUCK_VALVE = "stuck_valve"
    FOULED_FILTER = "fouled_filter"
    AFTER_HOURS = "after_hours_operation"


FAULT_DESCRIPTIONS = {
    FaultType.SENSOR_BIAS: "East-zone temperature sensor reads high",
    FaultType.STUCK_VALVE: "East-zone cooling valve remains near closed",
    FaultType.FOULED_FILTER: "AHU airflow falls while fan power rises",
    FaultType.AFTER_HOURS: "HVAC command remains enabled after office hours",
}


@dataclass(frozen=True)
class FaultEffect:
    """Commands, actual equipment values, and measurements after fault injection."""

    true_temp_c: float
    measured_temp_c: float
    command: float
    actual_valve_position: float
    commanded_airflow: float
    actual_airflow: float
    airflow_multiplier: float
    fan_power_multiplier: float
    reported_power_kw: float
    active_fault: str


def fault_is_active(fault_type: FaultType, timestamp: datetime) -> bool:
    """Return whether a fault is active in its disclosed weekly demo window."""

    hour = timestamp.hour + timestamp.minute / 60.0
    windows = {
        FaultType.SENSOR_BIAS: timestamp.weekday() == 1 and 10 <= hour < 16,
        FaultType.STUCK_VALVE: timestamp.weekday() == 2 and 10 <= hour < 17,
        FaultType.FOULED_FILTER: timestamp.weekday() == 3 and 9 <= hour < 18,
        FaultType.AFTER_HOURS: timestamp.weekday() == 4 and 20 <= hour < 24,
    }
    return windows[FaultType(fault_type)]


def apply_fault(
    fault_type: FaultType | None,
    true_temp_c: float,
    command: float,
    airflow: float,
    power_kw: float,
    *,
    config: FaultConfig | None = None,
    active: bool = True,
) -> FaultEffect:
    """Apply one fault to an east-zone command/measurement tuple."""

    settings = config or FaultConfig()
    selected = FaultType(fault_type) if fault_type is not None else None
    measured_temp = float(true_temp_c)
    effective_command = min(1.0, max(0.0, float(command)))
    commanded_airflow = min(1.0, max(0.0, float(airflow)))
    actual_valve = effective_command
    airflow_multiplier = 1.0
    fan_multiplier = 1.0
    label = "healthy"

    if active and selected is not None:
        label = selected.value
        if selected is FaultType.SENSOR_BIAS:
            measured_temp += settings.sensor_bias_c
        elif selected is FaultType.STUCK_VALVE:
            actual_valve = settings.stuck_valve_position
        elif selected is FaultType.FOULED_FILTER:
            airflow_multiplier = settings.fouled_airflow_multiplier
            fan_multiplier = settings.fouled_fan_power_multiplier
        elif selected is FaultType.AFTER_HOURS:
            effective_command = max(effective_command, settings.after_hours_command)
            commanded_airflow = max(commanded_airflow, min(1.0, settings.after_hours_command + 0.1))
            actual_valve = effective_command

    return FaultEffect(
        true_temp_c=float(true_temp_c),
        measured_temp_c=measured_temp,
        command=effective_command,
        actual_valve_position=actual_valve,
        commanded_airflow=commanded_airflow,
        actual_airflow=commanded_airflow * airflow_multiplier,
        airflow_multiplier=airflow_multiplier,
        fan_power_multiplier=fan_multiplier,
        reported_power_kw=float(power_kw) * fan_multiplier,
        active_fault=label,
    )
