"""Simulated BMS point registry and transparent alarm evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True)
class BMSPoint:
    point_id: str
    description: str
    equipment: str
    unit: str
    data_type: str
    writable: bool
    bacnet_object_type: str
    bacnet_instance: int
    modbus_register: int
    normal_min: float
    normal_max: float


@dataclass(frozen=True)
class AlarmEvent:
    timestamp: datetime
    point_id: str
    priority: int
    observed_value: float
    limit: float
    message: str


def build_point_registry() -> tuple[BMSPoint, ...]:
    """Return simulated BACnet/Modbus metadata; no live protocol connection exists."""

    definitions = (
        ("ZN-E-T", "East zone measured temperature", "ZONE-E", "°C", "analog-input", 18.0, 30.0, False),
        ("ZN-W-T", "West zone measured temperature", "ZONE-W", "°C", "analog-input", 18.0, 30.0, False),
        ("ZN-E-SP", "East zone temperature setpoint", "ZONE-E", "°C", "analog-output", 22.0, 30.0, True),
        ("ZN-W-SP", "West zone temperature setpoint", "ZONE-W", "°C", "analog-output", 22.0, 30.0, True),
        ("ZN-E-OCC", "East normalized occupancy", "ZONE-E", "fraction", "analog-input", 0.0, 1.0, False),
        ("ZN-W-OCC", "West normalized occupancy", "ZONE-W", "fraction", "analog-input", 0.0, 1.0, False),
        ("VLV-E-CMD", "East cooling valve command", "AHU-1", "%", "analog-output", 0.0, 100.0, True),
        ("VLV-E-FBK", "East cooling valve feedback", "AHU-1", "%", "analog-input", 0.0, 100.0, False),
        ("VLV-W-CMD", "West cooling valve command", "AHU-1", "%", "analog-output", 0.0, 100.0, True),
        ("VLV-W-FBK", "West cooling valve feedback", "AHU-1", "%", "analog-input", 0.0, 100.0, False),
        ("AF-E-CMD", "East airflow command", "AHU-1", "%", "analog-output", 0.0, 100.0, True),
        ("AF-E-FBK", "East airflow feedback", "AHU-1", "%", "analog-input", 0.0, 100.0, False),
        ("AF-W-CMD", "West airflow command", "AHU-1", "%", "analog-output", 0.0, 100.0, True),
        ("AF-W-FBK", "West airflow feedback", "AHU-1", "%", "analog-input", 0.0, 100.0, False),
        ("AHU-FAN-KW", "AHU fan electrical power", "AHU-1", "kW", "analog-input", 0.0, 8.0, False),
        ("CHLR-KW", "Chiller electrical power", "CHLR-1", "kW", "analog-input", 0.0, 20.0, False),
        ("HVAC-KW", "Total HVAC electrical power", "PLANT", "kW", "analog-input", 0.0, 25.0, False),
        ("OA-T", "Synthetic outdoor air temperature", "WEATHER", "°C", "analog-input", 15.0, 38.0, False),
        ("OA-RH", "Synthetic outdoor relative humidity", "WEATHER", "%RH", "analog-input", 30.0, 100.0, False),
    )
    points: list[BMSPoint] = []
    for offset, definition in enumerate(definitions):
        point_id, description, equipment, unit, object_type, low, high, writable = definition
        points.append(
            BMSPoint(
                point_id=point_id,
                description=description,
                equipment=equipment,
                unit=unit,
                data_type="float",
                writable=writable,
                bacnet_object_type=object_type,
                bacnet_instance=1001 + offset,
                modbus_register=30001 + offset,
                normal_min=low,
                normal_max=high,
            )
        )
    return tuple(points)


def points_to_frame(points: tuple[BMSPoint, ...] | None = None) -> pd.DataFrame:
    return pd.DataFrame(asdict(point) for point in (points or build_point_registry()))


def _value(record: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    value = float(record.get(key, default))
    return value if isfinite(value) else default


def evaluate_alarms(record: Mapping[str, Any], timestamp: datetime) -> list[AlarmEvent]:
    """Evaluate explicit BMS-style alarm rules for one trend record."""

    alarms: list[AlarmEvent] = []
    for key, point_id in (
        ("east_temp_measured_c", "ZN-E-T"),
        ("west_temp_measured_c", "ZN-W-T"),
    ):
        temperature = _value(record, key, 24.0)
        if temperature > 28.0:
            alarms.append(
                AlarmEvent(timestamp, point_id, 2, temperature, 28.0, "High zone temperature")
            )
        elif temperature < 18.0:
            alarms.append(
                AlarmEvent(timestamp, point_id, 2, temperature, 18.0, "Low zone temperature")
            )

    hvac_power = _value(record, "hvac_power_kw")
    if not bool(record.get("occupied", False)) and hvac_power > 1.5:
        alarms.append(
            AlarmEvent(
                timestamp,
                "HVAC-KW",
                2,
                hvac_power,
                1.5,
                "HVAC power detected while building is unoccupied",
            )
        )

    command = _value(record, "cooling_cmd_east")
    valve = _value(record, "valve_east")
    if command > 0.45 and command - valve > 0.30:
        alarms.append(
            AlarmEvent(
                timestamp,
                "VLV-E-FBK",
                2,
                valve,
                command - 0.30,
                "East valve feedback does not follow command",
            )
        )

    airflow_command = _value(record, "airflow_cmd_east")
    airflow = _value(record, "airflow_east")
    if airflow_command > 0.50 and airflow < 0.65 * airflow_command:
        alarms.append(
            AlarmEvent(
                timestamp,
                "AF-E-FBK",
                2,
                airflow,
                0.65 * airflow_command,
                "East airflow is low relative to command",
            )
        )
    return alarms
