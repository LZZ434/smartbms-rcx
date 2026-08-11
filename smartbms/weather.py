"""Deterministic synthetic Hong Kong summer weather and office loads."""

from __future__ import annotations

import numpy as np
import pandas as pd

from smartbms.config import SimulationConfig


HKO_AUGUST_NORMALS = {
    "period": "1991-2020",
    "mean_temp_c": 28.7,
    "mean_daily_max_c": 31.3,
    "mean_daily_min_c": 26.6,
    "mean_relative_humidity_pct": 81.0,
    "mean_daily_global_solar_mj_m2": 15.73,
    "source_url": "https://www.hko.gov.hk/en/cis/normal/1991_2020/dnormal08.htm",
}


def _office_occupancy(hour: np.ndarray, weekday: np.ndarray) -> np.ndarray:
    """Return a smooth, deterministic normalized office occupancy schedule."""

    occupancy = np.full(hour.shape, 0.01, dtype=float)
    arrival = weekday & (hour >= 7.5) & (hour < 9.0)
    morning = weekday & (hour >= 9.0) & (hour < 12.0)
    lunch = weekday & (hour >= 12.0) & (hour < 13.0)
    afternoon = weekday & (hour >= 13.0) & (hour < 17.5)
    departure = weekday & (hour >= 17.5) & (hour < 19.0)
    occupancy[arrival] = 0.08 + 0.82 * (hour[arrival] - 7.5) / 1.5
    occupancy[morning] = 0.90
    occupancy[lunch] = 0.65
    occupancy[afternoon] = 0.94
    occupancy[departure] = 0.94 - 0.86 * (hour[departure] - 17.5) / 1.5
    return np.clip(occupancy, 0.0, 1.0)


def generate_inputs(config: SimulationConfig) -> pd.DataFrame:
    """Generate a reproducible, synthetic seven-day Hong Kong office profile.

    The temperature, humidity, and solar levels are shaped around HKO August
    1991-2020 normals. They are not measurements from a real building or station.
    """

    timestamps = pd.date_range(
        start=config.start,
        periods=config.steps,
        freq=f"{config.timestep_minutes}min",
    )
    hour = timestamps.hour.to_numpy(dtype=float) + timestamps.minute.to_numpy() / 60.0
    weekday = timestamps.dayofweek.to_numpy() < 5
    day_index = ((timestamps.normalize() - timestamps[0].normalize()).days).to_numpy()
    rng = np.random.default_rng(config.seed)
    daily_temp_offsets = rng.normal(0.0, 0.18, config.days)
    daily_cloud_factor = rng.uniform(0.84, 1.0, config.days)

    thermal_wave = np.sin(2 * np.pi * (hour - 9.0) / 24.0)
    outdoor_temp = 28.7 + 2.35 * thermal_wave + daily_temp_offsets[day_index]
    humidity = np.clip(81.0 - 7.5 * thermal_wave + 0.8 * np.cos(day_index), 65.0, 95.0)
    solar_shape = np.maximum(0.0, np.sin(np.pi * (hour - 6.0) / 12.0))
    solar = 590.0 * solar_shape * daily_cloud_factor[day_index]

    base_occupancy = _office_occupancy(hour, weekday)
    occupancy_east = np.clip(base_occupancy * (0.97 + 0.03 * np.cos(2 * np.pi * hour / 24)), 0, 1)
    occupancy_west = np.clip(base_occupancy * (0.94 + 0.04 * np.sin(2 * np.pi * hour / 24)), 0, 1)

    east_orientation = 0.35 + 0.65 * np.clip((13.0 - hour) / 6.0, 0.0, 1.0)
    west_orientation = 0.35 + 0.65 * np.clip((hour - 11.0) / 6.0, 0.0, 1.0)
    solar_gain_east = solar * 0.0105 * east_orientation
    solar_gain_west = solar * 0.0105 * west_orientation

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "outdoor_temp_c": np.round(outdoor_temp, 3),
            "humidity_pct": np.round(humidity, 3),
            "solar_w_m2": np.round(solar, 3),
            "occupancy_east": np.round(occupancy_east, 4),
            "occupancy_west": np.round(occupancy_west, 4),
            "internal_gain_east_kw": np.round(0.65 + 6.6 * occupancy_east, 4),
            "internal_gain_west_kw": np.round(0.70 + 6.8 * occupancy_west, 4),
            "solar_gain_east_kw": np.round(solar_gain_east, 4),
            "solar_gain_west_kw": np.round(solar_gain_west, 4),
            "occupied": np.maximum(occupancy_east, occupancy_west) >= 0.15,
            "source_kind": "synthetic",
        }
    )
    frame.attrs.update(
        {
            "synthetic": True,
            "weather_reference": "Hong Kong Observatory 1991-2020 August normals",
            "weather_reference_url": HKO_AUGUST_NORMALS["source_url"],
            "disclosure": "Synthetic engineering profile; not real BMS or weather observations.",
            "seed": config.seed,
        }
    )
    return frame
