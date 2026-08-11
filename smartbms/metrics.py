"""Energy, demand, comfort, runtime, and illustrative cost metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from smartbms.config import TariffConfig


@dataclass(frozen=True)
class MetricSummary:
    scenario: str
    energy_kwh: float
    peak_kw: float
    occupied_discomfort_degree_hours: float
    occupied_comfort_pct: float
    runtime_hours: float
    synthetic_energy_cost_hkd: float
    synthetic_demand_cost_hkd: float
    total_synthetic_cost_hkd: float


def calculate_metrics(
    trends: pd.DataFrame,
    *,
    timestep_minutes: int = 15,
    tariff: TariffConfig | None = None,
    scenario: str = "scenario",
) -> MetricSummary:
    """Calculate auditable summary values directly from interval trends."""

    required = {
        "hvac_power_kw",
        "east_temp_true_c",
        "west_temp_true_c",
        "occupied",
    }
    missing = required.difference(trends.columns)
    if missing:
        raise ValueError(f"metric trends are missing columns: {sorted(missing)}")
    if timestep_minutes <= 0:
        raise ValueError("timestep_minutes must be positive")
    rates = tariff or TariffConfig()
    dt_hours = timestep_minutes / 60.0
    power = trends["hvac_power_kw"].clip(lower=0)
    energy_kwh = float(power.sum()) * dt_hours
    peak_kw = float(power.max()) if len(power) else 0.0
    runtime_hours = float((power > 0.5).sum()) * dt_hours

    occupied = trends["occupied"].astype(bool)
    temperatures = trends.loc[occupied, ["east_temp_true_c", "west_temp_true_c"]]
    if temperatures.empty:
        discomfort_degree_hours = 0.0
        comfort_pct = 100.0
    else:
        high = (temperatures - 26.0).clip(lower=0)
        low = (22.0 - temperatures).clip(lower=0)
        discomfort_degree_hours = float((high + low).to_numpy().sum()) * dt_hours
        comfortable = temperatures.ge(22.0) & temperatures.le(26.0)
        comfort_pct = float(comfortable.to_numpy().mean()) * 100.0

    energy_cost = energy_kwh * rates.energy_hkd_per_kwh
    demand_cost = peak_kw * rates.demand_hkd_per_kw_week
    return MetricSummary(
        scenario=scenario,
        energy_kwh=round(energy_kwh, 3),
        peak_kw=round(peak_kw, 3),
        occupied_discomfort_degree_hours=round(discomfort_degree_hours, 3),
        occupied_comfort_pct=round(comfort_pct, 3),
        runtime_hours=round(runtime_hours, 3),
        synthetic_energy_cost_hkd=round(energy_cost, 2),
        synthetic_demand_cost_hkd=round(demand_cost, 2),
        total_synthetic_cost_hkd=round(energy_cost + demand_cost, 2),
    )


def _savings(baseline: float, optimized: float) -> float:
    return 0.0 if baseline == 0 else (baseline - optimized) / baseline * 100.0


def comparison_frame(
    baseline: MetricSummary,
    optimized: MetricSummary,
) -> pd.DataFrame:
    """Return two rows with improvements measured against the baseline row."""

    frame = pd.DataFrame([asdict(baseline), asdict(optimized)])
    frame["energy_savings_pct"] = [
        0.0,
        round(_savings(baseline.energy_kwh, optimized.energy_kwh), 3),
    ]
    frame["peak_reduction_pct"] = [
        0.0,
        round(_savings(baseline.peak_kw, optimized.peak_kw), 3),
    ]
    frame["cost_savings_pct"] = [
        0.0,
        round(
            _savings(
                baseline.total_synthetic_cost_hkd,
                optimized.total_synthetic_cost_hkd,
            ),
            3,
        ),
    ]
    return frame
