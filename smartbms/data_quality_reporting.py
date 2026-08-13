"""Stable English-schema export adapters for data-quality evidence."""

from __future__ import annotations

import pandas as pd

from smartbms.data_quality import DataQualityReport


CHECK_COLUMNS = ("check_code", "status", "weight", "issue_count")
ISSUE_COLUMNS = (
    "issue_code",
    "severity",
    "columns",
    "affected_rows",
    "detail",
)
READINESS_COLUMNS = (
    "category",
    "eligible",
    "required_columns",
    "missing_columns",
    "blocking_issue_codes",
)
QUALITY_REPORT_COLUMNS = (
    "check_code",
    "status",
    "weight",
    "issue_code",
    "severity",
    "columns",
    "affected_rows",
    "detail",
)


def checks_frame(report: DataQualityReport) -> pd.DataFrame:
    rows = [
        {
            "check_code": check.code,
            "status": check.status,
            "weight": check.weight,
            "issue_count": len(check.issues),
        }
        for check in report.checks
    ]
    return pd.DataFrame(rows, columns=CHECK_COLUMNS)


def issues_frame(report: DataQualityReport) -> pd.DataFrame:
    rows = [
        {
            "issue_code": issue.code,
            "severity": issue.severity,
            "columns": ", ".join(issue.columns),
            "affected_rows": issue.affected_rows,
            "detail": issue.detail,
        }
        for issue in report.issues
    ]
    return pd.DataFrame(rows, columns=ISSUE_COLUMNS)


def readiness_frame(report: DataQualityReport) -> pd.DataFrame:
    rows = [
        {
            "category": readiness.category,
            "eligible": readiness.eligible,
            "required_columns": ", ".join(readiness.required_columns),
            "missing_columns": ", ".join(readiness.missing_columns),
            "blocking_issue_codes": ", ".join(readiness.blocking_issue_codes),
        }
        for readiness in report.readiness
    ]
    return pd.DataFrame(rows, columns=READINESS_COLUMNS)


def quality_report_frame(report: DataQualityReport) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for check in report.checks:
        if not check.issues:
            rows.append(
                {
                    "check_code": check.code,
                    "status": check.status,
                    "weight": check.weight,
                    "issue_code": "",
                    "severity": "",
                    "columns": "",
                    "affected_rows": 0,
                    "detail": "",
                }
            )
            continue
        for issue in check.issues:
            rows.append(
                {
                    "check_code": check.code,
                    "status": check.status,
                    "weight": check.weight,
                    "issue_code": issue.code,
                    "severity": issue.severity,
                    "columns": ", ".join(issue.columns),
                    "affected_rows": issue.affected_rows,
                    "detail": issue.detail,
                }
            )
    return pd.DataFrame(rows, columns=QUALITY_REPORT_COLUMNS)
