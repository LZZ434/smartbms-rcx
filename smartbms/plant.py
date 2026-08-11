"""Explainable two-zone RC thermal plant and simplified HVAC energy model."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from smartbms.config import ProjectConfig, ZoneConfig


def _clip_fraction(value: float) -> float:
    if not isfinite(value):
        raise ValueError("equipment commands must be finite")
    return min(1.0, max(0.0, float(value)))


@dataclass(frozen=True)
class PlantSnapshot:
    """State and energy result for one simulation interval."""

    east_temp_c: float
    west_temp_c: float
    cooling_east_kw: float
    cooling_west_kw: float
    chiller_power_kw: float
    fan_power_kw: float
    hvac_power_kw: float
    airflow_east: float
    airflow_west: float
    valve_east: float
    valve_west: float
    effective_cop: float


class TwoZonePlant:
    """First-order resistance-capacitance model with a shared AHU/chiller."""

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.east_temp_c = config.plant.east.initial_temp_c
        self.west_temp_c = config.plant.west.initial_temp_c

    def reset(self) -> None:
        self.east_temp_c = self.config.plant.east.initial_temp_c
        self.west_temp_c = self.config.plant.west.initial_temp_c

    @staticmethod
    def _next_temperature(
        current_temp_c: float,
        zone: ZoneConfig,
        dt_hours: float,
        outdoor_temp_c: float,
        internal_gain_kw: float,
        solar_gain_kw: float,
        delivered_cooling_kw: float,
    ) -> float:
        envelope_kw = (outdoor_temp_c - current_temp_c) / zone.resistance_c_per_kw
        net_heat_kw = envelope_kw + internal_gain_kw + solar_gain_kw - delivered_cooling_kw
        return current_temp_c + dt_hours * net_heat_kw / zone.capacitance_kwh_per_c

    def step(
        self,
        outdoor_temp_c: float,
        internal_gains_kw: tuple[float, float],
        solar_gains_kw: tuple[float, float],
        cooling_commands: tuple[float, float],
        airflow_commands: tuple[float, float],
        *,
        actual_valve_positions: tuple[float, float] | None = None,
        airflow_multipliers: tuple[float, float] = (1.0, 1.0),
        fan_power_multiplier: float = 1.0,
    ) -> PlantSnapshot:
        """Advance one timestep using commands and optional physical fault effects."""

        if not isfinite(outdoor_temp_c):
            raise ValueError("outdoor_temp_c must be finite")
        for name, values in (
            ("internal_gains_kw", internal_gains_kw),
            ("solar_gains_kw", solar_gains_kw),
        ):
            if len(values) != 2 or not all(isfinite(float(value)) for value in values):
                raise ValueError(f"{name} must contain two finite values")
        commands = tuple(_clip_fraction(value) for value in cooling_commands)
        valves = commands if actual_valve_positions is None else tuple(
            _clip_fraction(value) for value in actual_valve_positions
        )
        requested_airflow = tuple(_clip_fraction(value) for value in airflow_commands)
        multipliers = tuple(_clip_fraction(value) for value in airflow_multipliers)
        actual_airflow = tuple(
            0.0
            if command == 0
            else _clip_fraction(
                max(
                    self.config.plant.minimum_airflow_fraction,
                    command * multiplier,
                )
            )
            for command, multiplier in zip(requested_airflow, multipliers, strict=True)
        )
        if not isfinite(fan_power_multiplier) or fan_power_multiplier <= 0:
            raise ValueError("fan_power_multiplier must be positive and finite")

        zones = (self.config.plant.east, self.config.plant.west)
        delivered: list[float] = []
        for zone, valve, airflow in zip(zones, valves, actual_airflow, strict=True):
            airflow_effectiveness = 0.45 + 0.55 * airflow
            delivered.append(zone.max_cooling_kw * valve * airflow_effectiveness)

        average_airflow = sum(actual_airflow) / 2.0
        fan_power_kw = 0.0
        if average_airflow > 0:
            fan_power_kw = (
                self.config.plant.fan_idle_kw
                + self.config.plant.rated_fan_kw * average_airflow**3
            ) * fan_power_multiplier
        effective_cop = self.config.plant.chiller_cop * min(
            1.05, max(0.72, 1.0 - 0.015 * (outdoor_temp_c - 30.0))
        )
        chiller_power_kw = sum(delivered) / effective_cop

        self.east_temp_c = self._next_temperature(
            self.east_temp_c,
            zones[0],
            self.config.simulation.dt_hours,
            outdoor_temp_c,
            float(internal_gains_kw[0]),
            float(solar_gains_kw[0]),
            delivered[0],
        )
        self.west_temp_c = self._next_temperature(
            self.west_temp_c,
            zones[1],
            self.config.simulation.dt_hours,
            outdoor_temp_c,
            float(internal_gains_kw[1]),
            float(solar_gains_kw[1]),
            delivered[1],
        )

        return PlantSnapshot(
            east_temp_c=self.east_temp_c,
            west_temp_c=self.west_temp_c,
            cooling_east_kw=delivered[0],
            cooling_west_kw=delivered[1],
            chiller_power_kw=chiller_power_kw,
            fan_power_kw=fan_power_kw,
            hvac_power_kw=chiller_power_kw + fan_power_kw,
            airflow_east=actual_airflow[0],
            airflow_west=actual_airflow[1],
            valve_east=valves[0],
            valve_west=valves[1],
            effective_cop=effective_cop,
        )
