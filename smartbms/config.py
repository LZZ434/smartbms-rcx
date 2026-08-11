"""Validated engineering configuration for the SmartBMS-RCx simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite value")


@dataclass(frozen=True)
class SimulationConfig:
    """Timeline configuration; time quantities are in minutes or hours."""

    days: int = 7
    timestep_minutes: int = 15
    start: datetime = datetime(2026, 8, 3)
    seed: int = 20260803

    def __post_init__(self) -> None:
        if self.days < 1:
            raise ValueError("days must be at least one")
        if self.timestep_minutes <= 0:
            raise ValueError("timestep_minutes must be positive")
        if 24 * 60 % self.timestep_minutes:
            raise ValueError("timestep_minutes must evenly divide a day")
        if not isinstance(self.start, datetime):
            raise ValueError("start must be a datetime")

    @property
    def steps(self) -> int:
        return self.days * 24 * 60 // self.timestep_minutes

    @property
    def dt_hours(self) -> float:
        return self.timestep_minutes / 60.0


@dataclass(frozen=True)
class ZoneConfig:
    """Single-zone first-order RC parameters in kW, kWh/°C, and °C/kW."""

    name: str = "Zone"
    resistance_c_per_kw: float = 0.55
    capacitance_kwh_per_c: float = 18.0
    max_cooling_kw: float = 24.0
    initial_temp_c: float = 27.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("zone name must not be empty")
        _positive("resistance_c_per_kw", self.resistance_c_per_kw)
        _positive("capacitance_kwh_per_c", self.capacitance_kwh_per_c)
        _positive("max_cooling_kw", self.max_cooling_kw)
        if not 10 <= self.initial_temp_c <= 40:
            raise ValueError("initial_temp_c must be between 10 and 40 °C")


@dataclass(frozen=True)
class PlantConfig:
    """Shared AHU/chiller and two-zone plant parameters."""

    east: ZoneConfig = field(default_factory=lambda: ZoneConfig(name="East"))
    west: ZoneConfig = field(default_factory=lambda: ZoneConfig(name="West"))
    chiller_cop: float = 3.6
    rated_fan_kw: float = 5.5
    minimum_airflow_fraction: float = 0.08
    fan_idle_kw: float = 0.10

    def __post_init__(self) -> None:
        _positive("chiller_cop", self.chiller_cop)
        _positive("rated_fan_kw", self.rated_fan_kw)
        if not 0 <= self.minimum_airflow_fraction <= 1:
            raise ValueError("minimum_airflow_fraction must be between 0 and 1")
        if self.fan_idle_kw < 0:
            raise ValueError("fan_idle_kw must be non-negative")


@dataclass(frozen=True)
class ControllerConfig:
    """Baseline and predictive supervisory controller tuning values."""

    occupied_setpoint_c: float = 24.0
    unoccupied_setback_c: float = 28.0
    comfort_min_c: float = 22.0
    comfort_max_c: float = 26.0
    proportional_gain: float = 0.42
    occupied_min_airflow: float = 0.32
    unoccupied_min_airflow: float = 0.08
    pre_cooling_hours: float = 1.0
    energy_weight: float = 1.0
    peak_weight: float = 0.08
    comfort_weight: float = 35.0
    peak_target_kw: float = 14.0

    def __post_init__(self) -> None:
        if not self.comfort_min_c < self.comfort_max_c:
            raise ValueError("comfort_min_c must be below comfort_max_c")
        if not self.comfort_min_c <= self.occupied_setpoint_c <= self.comfort_max_c:
            raise ValueError("occupied setpoint must be inside the comfort band")
        if self.unoccupied_setback_c < self.occupied_setpoint_c:
            raise ValueError("unoccupied_setback_c must not be below occupied setpoint")
        _positive("proportional_gain", self.proportional_gain)
        for name in ("occupied_min_airflow", "unoccupied_min_airflow"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in ("energy_weight", "peak_weight", "comfort_weight"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        _positive("peak_target_kw", self.peak_target_kw)


@dataclass(frozen=True)
class FaultConfig:
    """Magnitudes used by deterministic synthetic fault scenarios."""

    sensor_bias_c: float = 2.2
    stuck_valve_position: float = 0.15
    fouled_airflow_multiplier: float = 0.58
    fouled_fan_power_multiplier: float = 1.45
    after_hours_command: float = 0.65

    def __post_init__(self) -> None:
        if self.sensor_bias_c == 0:
            raise ValueError("sensor_bias_c must be non-zero")
        if not 0 <= self.stuck_valve_position <= 1:
            raise ValueError("stuck_valve_position must be between 0 and 1")
        if not 0 < self.fouled_airflow_multiplier < 1:
            raise ValueError("fouled airflow multiplier must be between zero and one")
        if self.fouled_fan_power_multiplier <= 1:
            raise ValueError("fouled fan power multiplier must exceed one")
        if not 0 < self.after_hours_command <= 1:
            raise ValueError("after_hours_command must be between zero and one")


@dataclass(frozen=True)
class TariffConfig:
    """Illustrative tariff used only for synthetic scenario comparison."""

    energy_hkd_per_kwh: float = 1.35
    demand_hkd_per_kw_week: float = 42.0

    def __post_init__(self) -> None:
        if self.energy_hkd_per_kwh < 0 or self.demand_hkd_per_kw_week < 0:
            raise ValueError("tariff rates must be non-negative")


@dataclass(frozen=True)
class ProjectConfig:
    """Top-level immutable project configuration."""

    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    plant: PlantConfig = field(default_factory=PlantConfig)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    faults: FaultConfig = field(default_factory=FaultConfig)
    tariff: TariffConfig = field(default_factory=TariffConfig)
