"""Quality-gated, read-only RCx screening over canonical trend data."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from smartbms.data_quality import DataQualityReport, assess_trend_quality
from smartbms.diagnostics import DiagnosticFinding, run_diagnostics


@dataclass(frozen=True)
class ScreeningResult:
    frame: pd.DataFrame
    quality: DataQualityReport
    findings: tuple[DiagnosticFinding, ...]


def screen_trends(frame: pd.DataFrame) -> ScreeningResult:
    """Assess data and execute only diagnostic categories admitted by quality gates."""

    canonical = frame.copy(deep=True)
    quality = assess_trend_quality(canonical)
    findings: list[DiagnosticFinding] = []
    for readiness in quality.readiness:
        if not readiness.eligible:
            continue
        interval = quality.sampling_interval_minutes
        if interval is None or interval <= 0:
            continue
        findings.extend(
            run_diagnostics(
                canonical,
                categories=(readiness.category,),
                timestep_minutes=interval,
            )
        )
    return ScreeningResult(
        frame=canonical,
        quality=quality,
        findings=tuple(findings),
    )
