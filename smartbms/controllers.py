"""Baseline and bounded-search predictive HVAC supervisory controls."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite

from smartbms.config import ControllerConfig


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


@dataclass(frozen=True)
class ZoneObservation:
    """Controller-visible zone and weather values for one timestep."""

    east_temp_c: float
    west_temp_c: float
    occupied: bool
    outdoor_temp_c: float
    hour: float


@dataclass(frozen=True)
class ControlAction:
    """Normalized HVAC commands plus explainability fields."""

    cooling_east: float
    cooling_west: float
    airflow_east: float
    airflow_west: float
    target_east_c: float
    target_west_c: float
    strategy: str
    fallback_used: bool = False
    projected_power_kw: float = 0.0
    objective_score: float = 0.0


class BaselineController:
    """Schedule plus proportional zone-temperature control."""

    def __init__(self, config: ControllerConfig) -> None:
        self.config = config

    def act(self, observation: ZoneObservation) -> ControlAction:
        target = (
            self.config.occupied_setpoint_c
            if observation.occupied
            else self.config.unoccupied_setback_c
        )
        minimum_airflow = (
            self.config.occupied_min_airflow
            if observation.occupied
            else self.config.unoccupied_min_airflow
        )

        def zone_action(temperature: float) -> tuple[float, float]:
            safe_temperature = temperature if isfinite(temperature) else target
            cooling = _clip(self.config.proportional_gain * (safe_temperature - target))
            airflow = _clip(max(minimum_airflow, minimum_airflow + (1 - minimum_airflow) * cooling))
            return cooling, airflow

        cooling_east, airflow_east = zone_action(observation.east_temp_c)
        cooling_west, airflow_west = zone_action(observation.west_temp_c)
        return ControlAction(
            cooling_east=cooling_east,
            cooling_west=cooling_west,
            airflow_east=airflow_east,
            airflow_west=airflow_west,
            target_east_c=target,
            target_west_c=target,
            strategy="baseline",
        )


class PredictiveController:
    """Small explainable candidate search, not a learned model or full MPC."""

    def __init__(self, config: ControllerConfig) -> None:
        self.config = config
        self._baseline = BaselineController(config)

    @staticmethod
    def _valid_observation(observation: ZoneObservation) -> bool:
        values = (
            observation.east_temp_c,
            observation.west_temp_c,
            observation.outdoor_temp_c,
            observation.hour,
        )
        return all(isfinite(value) for value in values)

    def _safe_fallback(self, observation: ZoneObservation) -> ControlAction:
        safe = ZoneObservation(
            east_temp_c=(
                observation.east_temp_c
                if isfinite(observation.east_temp_c)
                else self.config.occupied_setpoint_c
            ),
            west_temp_c=(
                observation.west_temp_c
                if isfinite(observation.west_temp_c)
                else self.config.occupied_setpoint_c
            ),
            occupied=observation.occupied,
            outdoor_temp_c=(
                observation.outdoor_temp_c
                if isfinite(observation.outdoor_temp_c)
                else self.config.occupied_setpoint_c
            ),
            hour=observation.hour if isfinite(observation.hour) else 12.0,
        )
        return replace(
            self._baseline.act(safe),
            strategy="predictive-fallback",
            fallback_used=True,
        )

    def act(
        self,
        observation: ZoneObservation,
        *,
        occupancy_next_hour: float = 0.0,
        outdoor_temp_next_hour_c: float | None = None,
    ) -> ControlAction:
        if not self._valid_observation(observation) or not isfinite(occupancy_next_hour):
            return self._safe_fallback(observation)
        next_outdoor = (
            observation.outdoor_temp_c
            if outdoor_temp_next_hour_c is None
            else outdoor_temp_next_hour_c
        )
        if not isfinite(next_outdoor):
            return self._safe_fallback(observation)
        next_occupancy = _clip(occupancy_next_hour)

        if observation.occupied:
            targets = (24.5, 25.0, 25.5, self.config.comfort_max_c)
        elif next_occupancy >= 0.15:
            targets = (24.5, 25.0, 25.5, self.config.comfort_max_c)
        else:
            targets = (self.config.unoccupied_setback_c, 29.0, 30.0)

        best: ControlAction | None = None
        for target in targets:
            effective_occupied = observation.occupied or next_occupancy >= 0.15
            minimum_airflow = (
                self.config.occupied_min_airflow if observation.occupied else 0.20
            ) if effective_occupied else self.config.unoccupied_min_airflow
            commands: list[float] = []
            airflows: list[float] = []
            predicted_temperatures: list[float] = []

            for temperature in (observation.east_temp_c, observation.west_temp_c):
                feedforward = max(0.0, next_outdoor - target) * 0.015
                pre_cooling = 0.10 * next_occupancy if not observation.occupied else 0.0
                command = _clip(
                    self.config.proportional_gain * (temperature - target)
                    + feedforward
                    + pre_cooling
                )
                airflow = _clip(max(minimum_airflow, minimum_airflow + (1 - minimum_airflow) * command))
                delivered_kw = 18.0 * command * (0.45 + 0.55 * airflow)
                internal_kw = 6.0 * max(next_occupancy, 0.2 if observation.occupied else 0.0) + 0.7
                predicted = temperature + (
                    (next_outdoor - temperature) / 0.55 + internal_kw - delivered_kw
                ) / 18.0
                commands.append(command)
                airflows.append(airflow)
                predicted_temperatures.append(predicted)

            delivered_total = sum(
                18.0 * command * (0.45 + 0.55 * airflow)
                for command, airflow in zip(commands, airflows, strict=True)
            )
            projected_power = delivered_total / 3.6 + 5.5 * (sum(airflows) / 2) ** 3
            if effective_occupied:
                comfort_violation = sum(
                    max(0.0, predicted - self.config.comfort_max_c)
                    + max(0.0, self.config.comfort_min_c - predicted)
                    for predicted in predicted_temperatures
                )
            else:
                comfort_violation = sum(max(0.0, predicted - 30.0) * 0.2 for predicted in predicted_temperatures)
            score = (
                self.config.energy_weight * projected_power
                + self.config.peak_weight
                * max(0.0, projected_power - self.config.peak_target_kw) ** 2
                + self.config.comfort_weight * comfort_violation**2
            )
            candidate = ControlAction(
                cooling_east=commands[0],
                cooling_west=commands[1],
                airflow_east=airflows[0],
                airflow_west=airflows[1],
                target_east_c=target,
                target_west_c=target,
                strategy="predictive",
                projected_power_kw=projected_power,
                objective_score=score,
            )
            if best is None or candidate.objective_score < best.objective_score:
                best = candidate

        if best is None:
            return self._safe_fallback(observation)
        return best
