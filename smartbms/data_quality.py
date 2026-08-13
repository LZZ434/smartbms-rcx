"""Deterministic data-quality checks and RCx rule-admission decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from smartbms.diagnostics import (
    DIAGNOSTIC_CATEGORIES,
    REQUIRED_COLUMNS_BY_CATEGORY,
)


IssueSeverity = Literal["critical", "warning", "info"]
CheckStatus = Literal["pass", "warning", "fail"]

MIN_HISTORY_ROWS = 16
FROZEN_RUN_SAMPLES = 8
MAX_TEMPERATURE_STEP_C = 2.0

CHECK_WEIGHTS = {
    "timestamps": 20,
    "history": 10,
    "coverage": 15,
    "missing": 15,
    "frozen": 10,
    "bounds": 15,
    "temperature_rate": 10,
    "cross_point": 5,
}

GLOBAL_BLOCKING_CODES = frozenset(
    {
        "timestamp_missing",
        "timestamp_invalid",
        "timestamp_duplicate",
        "timestamp_unsorted",
        "timestamp_irregular",
        "history_too_short",
    }
)

FROZEN_SIGNAL_COLUMNS = (
    "east_temp_measured_c",
    "west_temp_measured_c",
    "east_temp_reference_c",
)

TEMPERATURE_RATE_COLUMNS = FROZEN_SIGNAL_COLUMNS

ENGINEERING_BOUNDS: dict[str, tuple[float, float]] = {
    "outdoor_temp_c": (-20.0, 55.0),
    "humidity_pct": (0.0, 100.0),
    "east_temp_true_c": (5.0, 45.0),
    "west_temp_true_c": (5.0, 45.0),
    "east_temp_measured_c": (5.0, 45.0),
    "west_temp_measured_c": (5.0, 45.0),
    "east_temp_reference_c": (5.0, 45.0),
    "target_east_c": (5.0, 45.0),
    "target_west_c": (5.0, 45.0),
    "cooling_cmd_east": (0.0, 1.0),
    "cooling_cmd_west": (0.0, 1.0),
    "valve_east": (0.0, 1.0),
    "valve_west": (0.0, 1.0),
    "airflow_cmd_east": (0.0, 1.0),
    "airflow_cmd_west": (0.0, 1.0),
    "airflow_east": (0.0, 1.0),
    "airflow_west": (0.0, 1.0),
    "cooling_east_kw": (0.0, 1000.0),
    "cooling_west_kw": (0.0, 1000.0),
    "chiller_power_kw": (0.0, 1000.0),
    "fan_power_kw": (0.0, 1000.0),
    "expected_fan_power_kw": (0.0, 1000.0),
    "hvac_power_kw": (0.0, 1000.0),
    "projected_power_kw": (0.0, 1000.0),
    "effective_cop": (0.5, 10.0),
}


@dataclass(frozen=True)
class QualityIssue:
    code: str
    severity: IssueSeverity
    columns: tuple[str, ...]
    affected_rows: int
    detail: str


@dataclass(frozen=True)
class QualityCheckResult:
    code: str
    status: CheckStatus
    weight: int
    issues: tuple[QualityIssue, ...] = ()


@dataclass(frozen=True)
class DiagnosticReadiness:
    category: str
    required_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    blocking_issue_codes: tuple[str, ...]
    eligible: bool


@dataclass(frozen=True)
class DataQualityReport:
    row_count: int
    start_time: pd.Timestamp | None
    end_time: pd.Timestamp | None
    sampling_interval_minutes: float | None
    score: float
    checks: tuple[QualityCheckResult, ...]
    readiness: tuple[DiagnosticReadiness, ...]

    @property
    def issues(self) -> tuple[QualityIssue, ...]:
        return tuple(issue for check in self.checks for issue in check.issues)


def _check_result(
    code: str,
    issues: list[QualityIssue],
) -> QualityCheckResult:
    if any(issue.severity == "critical" for issue in issues):
        status: CheckStatus = "fail"
    elif issues:
        status = "warning"
    else:
        status = "pass"
    return QualityCheckResult(
        code=code,
        status=status,
        weight=CHECK_WEIGHTS[code],
        issues=tuple(issues),
    )


def _timestamp_check(
    frame: pd.DataFrame,
) -> tuple[QualityCheckResult, pd.Series | None, float | None]:
    issues: list[QualityIssue] = []
    if "timestamp" not in frame.columns:
        issues.append(
            QualityIssue(
                code="timestamp_missing",
                severity="critical",
                columns=("timestamp",),
                affected_rows=len(frame),
                detail="timestamp column is missing",
            )
        )
        return _check_result("timestamps", issues), None, None

    timestamps = pd.to_datetime(frame["timestamp"], errors="coerce")
    invalid_count = int(timestamps.isna().sum())
    if invalid_count:
        issues.append(
            QualityIssue(
                code="timestamp_invalid",
                severity="critical",
                columns=("timestamp",),
                affected_rows=invalid_count,
                detail=f"{invalid_count} timestamps are missing or invalid",
            )
        )

    duplicate_count = int(timestamps.duplicated(keep=False).sum())
    if duplicate_count:
        issues.append(
            QualityIssue(
                code="timestamp_duplicate",
                severity="critical",
                columns=("timestamp",),
                affected_rows=duplicate_count,
                detail=f"{duplicate_count} rows share duplicate timestamps",
            )
        )

    if not timestamps.is_monotonic_increasing:
        issues.append(
            QualityIssue(
                code="timestamp_unsorted",
                severity="critical",
                columns=("timestamp",),
                affected_rows=len(frame),
                detail="timestamps are not monotonically increasing",
            )
        )

    interval_minutes: float | None = None
    valid = timestamps.dropna()
    if len(valid) >= 2:
        differences = valid.diff().dropna().dt.total_seconds().div(60.0)
        if not differences.empty:
            interval_minutes = float(differences.median())
            irregular = ~np.isclose(
                differences.to_numpy(dtype=float),
                interval_minutes,
                atol=1.0 / 60.0,
                rtol=0.0,
            )
            irregular_count = int(irregular.sum())
            if irregular_count:
                issues.append(
                    QualityIssue(
                        code="timestamp_irregular",
                        severity="critical",
                        columns=("timestamp",),
                        affected_rows=irregular_count,
                        detail=(
                            f"{irregular_count} intervals differ from the "
                            f"{interval_minutes:.3f}-minute median"
                        ),
                    )
                )
    return _check_result("timestamps", issues), timestamps, interval_minutes


def _history_check(frame: pd.DataFrame) -> QualityCheckResult:
    issues: list[QualityIssue] = []
    if len(frame) < MIN_HISTORY_ROWS:
        issues.append(
            QualityIssue(
                code="history_too_short",
                severity="critical",
                columns=("timestamp",),
                affected_rows=len(frame),
                detail=f"at least {MIN_HISTORY_ROWS} rows are required",
            )
        )
    return _check_result("history", issues)


def _coverage_check(frame: pd.DataFrame) -> QualityCheckResult:
    required = set().union(*REQUIRED_COLUMNS_BY_CATEGORY.values())
    missing = tuple(sorted(required.difference(frame.columns)))
    issues: list[QualityIssue] = []
    if missing:
        issues.append(
            QualityIssue(
                code="required_columns_missing",
                severity="critical",
                columns=missing,
                affected_rows=0,
                detail=f"{len(missing)} diagnostic-required columns are missing",
            )
        )
    return _check_result("coverage", issues)


def _missing_check(frame: pd.DataFrame) -> QualityCheckResult:
    diagnostic_columns = set().union(*REQUIRED_COLUMNS_BY_CATEGORY.values())
    issues: list[QualityIssue] = []
    for column in frame.columns:
        missing_count = int(frame[column].isna().sum())
        if missing_count:
            severity: IssueSeverity = (
                "critical" if column in diagnostic_columns else "warning"
            )
            issues.append(
                QualityIssue(
                    code="missing_values",
                    severity=severity,
                    columns=(str(column),),
                    affected_rows=missing_count,
                    detail=f"{missing_count} values are missing in {column}",
                )
            )
    return _check_result("missing", issues)


def _longest_unchanged_run(series: pd.Series) -> int:
    numeric = pd.to_numeric(series, errors="coerce")
    unchanged = numeric.diff().abs().le(1e-9) & numeric.notna() & numeric.shift().notna()
    groups = (~unchanged).cumsum()
    longest_transitions = int(unchanged.groupby(groups).sum().max()) if len(series) else 0
    return longest_transitions + 1 if longest_transitions else 0


def _frozen_check(frame: pd.DataFrame) -> QualityCheckResult:
    issues: list[QualityIssue] = []
    for column in FROZEN_SIGNAL_COLUMNS:
        if column not in frame:
            continue
        run_length = _longest_unchanged_run(frame[column])
        if run_length >= FROZEN_RUN_SAMPLES:
            issues.append(
                QualityIssue(
                    code="frozen_signal",
                    severity="critical",
                    columns=(column,),
                    affected_rows=run_length,
                    detail=f"{column} is unchanged for {run_length} samples",
                )
            )
    return _check_result("frozen", issues)


def _bounds_check(frame: pd.DataFrame) -> QualityCheckResult:
    issues: list[QualityIssue] = []
    for column, (lower, upper) in ENGINEERING_BOUNDS.items():
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = values.notna() & ~values.between(lower, upper, inclusive="both")
        count = int(invalid.sum())
        if count:
            issues.append(
                QualityIssue(
                    code="engineering_bounds",
                    severity="critical",
                    columns=(column,),
                    affected_rows=count,
                    detail=f"{count} {column} values fall outside [{lower}, {upper}]",
                )
            )
    return _check_result("bounds", issues)


def _temperature_rate_check(frame: pd.DataFrame) -> QualityCheckResult:
    issues: list[QualityIssue] = []
    for column in TEMPERATURE_RATE_COLUMNS:
        if column not in frame:
            continue
        step = pd.to_numeric(frame[column], errors="coerce").diff().abs()
        excessive = step > MAX_TEMPERATURE_STEP_C
        count = int(excessive.sum())
        if count:
            issues.append(
                QualityIssue(
                    code="temperature_rate",
                    severity="critical",
                    columns=(column,),
                    affected_rows=count,
                    detail=(
                        f"{count} {column} steps exceed "
                        f"{MAX_TEMPERATURE_STEP_C:.1f} °C per sample"
                    ),
                )
            )
    return _check_result("temperature_rate", issues)


def _cross_point_check(frame: pd.DataFrame) -> QualityCheckResult:
    issues: list[QualityIssue] = []
    if {"hvac_power_kw", "fan_power_kw"}.issubset(frame.columns):
        inconsistent = frame["hvac_power_kw"] + 1e-6 < frame["fan_power_kw"]
        count = int(inconsistent.fillna(False).sum())
        if count:
            issues.append(
                QualityIssue(
                    code="cross_point_power",
                    severity="critical",
                    columns=("hvac_power_kw", "fan_power_kw"),
                    affected_rows=count,
                    detail=f"HVAC power is below fan power in {count} rows",
                )
            )
    required = {"airflow_cmd_east", "expected_fan_power_kw"}
    if required.issubset(frame.columns):
        inconsistent = (frame["airflow_cmd_east"] > 0.4) & (
            frame["expected_fan_power_kw"] <= 0
        )
        count = int(inconsistent.fillna(False).sum())
        if count:
            issues.append(
                QualityIssue(
                    code="cross_point_expected_fan",
                    severity="critical",
                    columns=("airflow_cmd_east", "expected_fan_power_kw"),
                    affected_rows=count,
                    detail=f"expected fan power is non-positive in {count} active rows",
                )
            )
    return _check_result("cross_point", issues)


def _score(checks: tuple[QualityCheckResult, ...]) -> float:
    earned = 0.0
    for check in checks:
        if check.status == "pass":
            earned += check.weight
        elif check.status == "warning":
            earned += check.weight / 2.0
    return round(earned, 1)


def _readiness(
    frame: pd.DataFrame,
    issues: tuple[QualityIssue, ...],
) -> tuple[DiagnosticReadiness, ...]:
    critical = tuple(issue for issue in issues if issue.severity == "critical")
    global_codes = {
        issue.code for issue in critical if issue.code in GLOBAL_BLOCKING_CODES
    }
    readiness: list[DiagnosticReadiness] = []
    for category in DIAGNOSTIC_CATEGORIES:
        required = tuple(sorted(REQUIRED_COLUMNS_BY_CATEGORY[category]))
        missing = tuple(sorted(set(required).difference(frame.columns)))
        blocking = set(global_codes)
        for issue in critical:
            if set(issue.columns).intersection(required):
                blocking.add(issue.code)
        readiness.append(
            DiagnosticReadiness(
                category=category,
                required_columns=required,
                missing_columns=missing,
                blocking_issue_codes=tuple(sorted(blocking)),
                eligible=not missing and not blocking,
            )
        )
    return tuple(readiness)


def assess_trend_quality(frame: pd.DataFrame) -> DataQualityReport:
    """Assess a copy of a canonical trend frame without repairing its evidence."""

    source = frame.copy(deep=True)
    timestamp_check, timestamps, interval_minutes = _timestamp_check(source)
    checks = (
        timestamp_check,
        _history_check(source),
        _coverage_check(source),
        _missing_check(source),
        _frozen_check(source),
        _bounds_check(source),
        _temperature_rate_check(source),
        _cross_point_check(source),
    )
    issues = tuple(issue for check in checks for issue in check.issues)
    valid_timestamps = timestamps.dropna() if timestamps is not None else pd.Series(dtype="datetime64[ns]")
    start = pd.Timestamp(valid_timestamps.min()) if not valid_timestamps.empty else None
    end = pd.Timestamp(valid_timestamps.max()) if not valid_timestamps.empty else None
    return DataQualityReport(
        row_count=len(source),
        start_time=start,
        end_time=end,
        sampling_interval_minutes=(
            round(interval_minutes, 3) if interval_minutes is not None else None
        ),
        score=_score(checks),
        checks=checks,
        readiness=_readiness(source, issues),
    )
