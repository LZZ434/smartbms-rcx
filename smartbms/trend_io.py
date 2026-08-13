"""Strict, in-memory ingestion for canonical BMS trend data."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from numbers import Real
from typing import Any

import pandas as pd


MAX_UPLOAD_BYTES = 10 * 1024 * 1024

BOOLEAN_COLUMNS = frozenset(
    {
        "synthetic",
        "occupied",
        "preconditioning_authorized",
        "controller_fallback",
        "fault_active",
    }
)

NUMERIC_COLUMNS = frozenset(
    {
        "outdoor_temp_c",
        "humidity_pct",
        "solar_w_m2",
        "occupancy_east",
        "occupancy_west",
        "occupancy_next_hour",
        "internal_gain_east_kw",
        "internal_gain_west_kw",
        "solar_gain_east_kw",
        "solar_gain_west_kw",
        "east_temp_true_c",
        "west_temp_true_c",
        "east_temp_measured_c",
        "west_temp_measured_c",
        "east_temp_reference_c",
        "target_east_c",
        "target_west_c",
        "cooling_cmd_east",
        "cooling_cmd_west",
        "valve_east",
        "valve_west",
        "airflow_cmd_east",
        "airflow_cmd_west",
        "airflow_east",
        "airflow_west",
        "cooling_east_kw",
        "cooling_west_kw",
        "chiller_power_kw",
        "fan_power_kw",
        "expected_fan_power_kw",
        "hvac_power_kw",
        "effective_cop",
        "projected_power_kw",
        "objective_score",
    }
)


@dataclass(frozen=True)
class IngestionNotice:
    code: str
    column: str | None = None
    affected_rows: int = 0


@dataclass(frozen=True)
class TrendIngestionResult:
    frame: pd.DataFrame
    notices: tuple[IngestionNotice, ...] = ()


class TrendIngestionError(ValueError):
    """A stable, user-safe trend-ingestion failure."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _parse_boolean(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value
    if isinstance(value, Real) and not isinstance(value, bool):
        if float(value) == 1.0:
            return True
        if float(value) == 0.0:
            return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError(f"unsupported boolean value: {value!r}")


def canonicalize_trend_frame(frame: pd.DataFrame) -> TrendIngestionResult:
    """Return a typed copy while preserving columns, unknown data, and row order."""

    if frame.empty:
        raise TrendIngestionError("empty_file", "trend data has no rows")
    if frame.columns.duplicated().any():
        duplicates = sorted(set(frame.columns[frame.columns.duplicated()].astype(str)))
        raise TrendIngestionError(
            "duplicate_columns",
            f"trend data has duplicate columns: {duplicates}",
        )
    if "timestamp" not in frame.columns:
        raise TrendIngestionError(
            "missing_timestamp",
            "trend data must contain a timestamp column",
        )

    canonical = frame.copy(deep=True)
    notices: list[IngestionNotice] = []

    parsed_timestamps = pd.to_datetime(canonical["timestamp"], errors="coerce")
    invalid_timestamps = canonical["timestamp"].notna() & parsed_timestamps.isna()
    if bool(invalid_timestamps.any()) or bool(parsed_timestamps.isna().any()):
        raise TrendIngestionError(
            "invalid_timestamp",
            "timestamp contains missing or unparseable values",
        )
    if not pd.api.types.is_datetime64_any_dtype(canonical["timestamp"]):
        notices.append(
            IngestionNotice(
                code="timestamp_parsed",
                column="timestamp",
                affected_rows=len(canonical),
            )
        )
    canonical["timestamp"] = parsed_timestamps

    for column in sorted(NUMERIC_COLUMNS.intersection(canonical.columns)):
        source = canonical[column]
        converted = pd.to_numeric(source, errors="coerce")
        invalid = source.notna() & converted.isna()
        if bool(invalid.any()):
            raise TrendIngestionError(
                "invalid_numeric",
                f"{column} contains {int(invalid.sum())} non-numeric values",
            )
        if not pd.api.types.is_numeric_dtype(source):
            notices.append(
                IngestionNotice(
                    code="numeric_parsed",
                    column=column,
                    affected_rows=int(source.notna().sum()),
                )
            )
        canonical[column] = converted

    for column in sorted(BOOLEAN_COLUMNS.intersection(canonical.columns)):
        source = canonical[column]
        try:
            converted = source.map(_parse_boolean)
        except ValueError as exc:
            raise TrendIngestionError(
                "invalid_boolean",
                f"{column} contains an unsupported boolean value",
            ) from exc
        if converted.isna().any():
            canonical[column] = converted.astype("boolean")
        else:
            canonical[column] = converted.astype(bool)
        if not pd.api.types.is_bool_dtype(source):
            notices.append(
                IngestionNotice(
                    code="boolean_parsed",
                    column=column,
                    affected_rows=int(source.notna().sum()),
                )
            )

    return TrendIngestionResult(frame=canonical, notices=tuple(notices))


def ingest_csv_bytes(
    data: bytes | bytearray,
    *,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> TrendIngestionResult:
    """Parse a UTF-8 CSV payload and return canonical in-memory trend data."""

    payload = bytes(data)
    if not payload:
        raise TrendIngestionError("empty_file", "uploaded CSV is empty")
    if len(payload) > max_bytes:
        raise TrendIngestionError(
            "file_too_large",
            f"uploaded CSV exceeds {max_bytes} bytes",
        )
    try:
        frame = pd.read_csv(BytesIO(payload), encoding="utf-8-sig")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise TrendIngestionError(
            "malformed_csv",
            "uploaded data is not a valid UTF-8 CSV",
        ) from exc
    return canonicalize_trend_frame(frame)
