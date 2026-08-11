"""Deterministic HTML, Markdown, and CSV portfolio exports."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pandas as pd

from smartbms.diagnostics import findings_to_frame
from smartbms.i18n import (
    column_label,
    localize_findings_frame,
    localize_frame,
    scenario_label,
    t,
)
from smartbms.scenarios import ScenarioBundle, ScenarioRun


def _all_runs(bundle: ScenarioBundle) -> list[ScenarioRun]:
    return [bundle.baseline, bundle.optimized, *bundle.fault_runs.values()]


def _findings_frame(bundle: ScenarioBundle) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for run in _all_runs(bundle):
        frame = findings_to_frame(list(run.findings))
        if not frame.empty:
            frame.insert(0, "scenario", run.name)
            frames.append(frame)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(
        columns=[
            "scenario",
            "category",
            "title",
            "detected_at",
            "severity",
            "confidence",
            "evidence",
            "evidence_columns",
            "estimated_waste_kwh",
            "recommendation",
        ]
    )


def _alarms_frame(bundle: ScenarioBundle) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for run in _all_runs(bundle):
        for alarm in run.alarms:
            row = asdict(alarm)
            row["scenario"] = run.name
            rows.append(row)
    columns = (
        "scenario",
        "timestamp",
        "point_id",
        "priority",
        "observed_value",
        "limit",
        "message",
    )
    return pd.DataFrame(rows, columns=columns)


def _localized_findings_frame(bundle: ScenarioBundle, language: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    scenario_column = column_label("scenario", language)
    for run in _all_runs(bundle):
        frame = localize_findings_frame(run.findings, language)
        if not frame.empty:
            frame.insert(0, scenario_column, scenario_label(run.name, language))
            frames.append(frame)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return localize_frame(_findings_frame(bundle), language)


def render_html_report(bundle: ScenarioBundle, language: str = "en") -> str:
    """Render a self-contained, escaped technical report."""

    title = t(language, "report.title")
    optimized = bundle.comparison.loc[bundle.comparison["scenario"] == "optimized"].iloc[0]
    comparison_table = localize_frame(bundle.comparison.round(3), language).to_html(
        index=False, escape=True, classes="data"
    )
    scorecard_table = localize_frame(bundle.diagnostic_scorecard, language).to_html(
        index=False, escape=True, classes="data"
    )
    findings_table = _localized_findings_frame(bundle, language).to_html(
        index=False, escape=True, classes="data"
    )
    document_language = "zh-CN" if language == "zh" else "en"
    boundary_items = "".join(
        f"<li>{t(language, f'report.boundary.{position}')}</li>"
        for position in range(1, 5)
    )
    return f"""<!doctype html>
<html lang="{document_language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --ink:#132238; --muted:#5d6b7d; --blue:#176b87; --teal:#2a9d8f; --paper:#f4f7fb; --card:#fff; --line:#d9e1eb; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1120px; margin:0 auto; padding:42px 24px 64px; }}
h1 {{ font-size:36px; margin:0 0 8px; letter-spacing:-.03em; }}
h2 {{ margin-top:34px; border-bottom:2px solid var(--line); padding-bottom:8px; }}
.eyebrow {{ color:var(--blue); font-weight:700; letter-spacing:.09em; text-transform:uppercase; }}
.notice {{ background:#fff3cd; border-left:5px solid #e0a800; padding:14px 16px; margin:22px 0; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:24px 0; }}
.kpi {{ background:var(--card); padding:18px; border:1px solid var(--line); border-radius:12px; box-shadow:0 6px 20px rgba(19,34,56,.06); }}
.kpi b {{ display:block; font-size:27px; color:var(--teal); }}
.kpi span {{ color:var(--muted); }}
.table-wrap {{ overflow-x:auto; background:var(--card); padding:10px; border-radius:10px; border:1px solid var(--line); }}
table.data {{ width:100%; border-collapse:collapse; font-size:13px; }}
table.data th, table.data td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
table.data th {{ background:#eaf1f7; position:sticky; top:0; }}
code {{ background:#e9eef4; padding:2px 5px; border-radius:4px; }}
footer {{ color:var(--muted); margin-top:36px; }}
@media(max-width:760px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} h1 {{ font-size:29px; }} }}
</style>
</head>
<body><main>
<div class="eyebrow">{t(language, "report.eyebrow")}</div>
<h1>{title}</h1>
<p>{t(language, "report.subtitle")}</p>
<div class="notice"><strong>{t(language, "report.disclosure_label")}:</strong> {t(language, "report.disclosure")}</div>
<div class="kpis">
  <div class="kpi"><b>{optimized['energy_savings_pct']:.3f}%</b><span>{t(language, "report.kpi.energy")}</span></div>
  <div class="kpi"><b>{optimized['peak_reduction_pct']:.3f}%</b><span>{t(language, "report.kpi.peak")}</span></div>
  <div class="kpi"><b>{bundle.optimized.metrics.occupied_comfort_pct:.1f}%</b><span>{t(language, "report.kpi.comfort")}</span></div>
  <div class="kpi"><b>{int(bundle.diagnostic_scorecard['detected'].sum())}/4</b><span>{t(language, "report.kpi.faults")}</span></div>
</div>
<h2>{t(language, "report.section.scenario")}</h2>
<p>{t(language, "report.scenario_note")}</p>
<div class="table-wrap">{comparison_table}</div>
<h2>{t(language, "report.section.scorecard")}</h2>
<p>{t(language, "report.scorecard_note")}</p>
<div class="table-wrap">{scorecard_table}</div>
<h2>{t(language, "report.section.findings")}</h2>
<div class="table-wrap">{findings_table}</div>
<h2>{t(language, "report.section.boundary")}</h2>
<ul>{boundary_items}</ul>
<h2>{t(language, "report.section.sources")}</h2>
<ul>
  <li><a href="https://www.hko.gov.hk/en/cis/normal/1991_2020/dnormal08.htm">{t(language, "report.source.hko")}</a> — {t(language, "report.source.hko_note")}</li>
  <li><a href="https://www.emsd.gov.hk/filemanager/en/content_718/Technical_Guidelines_Retro-commissioning.pdf">{t(language, "report.source.emsd")}</a> — {t(language, "report.source.emsd_note")}</li>
</ul>
<footer>{t(language, "report.footer", seed=bundle.baseline.trends.attrs.get("seed"))}</footer>
</main></body></html>"""


def render_markdown_report(bundle: ScenarioBundle, language: str = "en") -> str:
    optimized = bundle.comparison.loc[bundle.comparison["scenario"] == "optimized"].iloc[0]
    lines = [
        f"# {t(language, 'report.title')}",
        "",
        f"> **{t(language, 'report.markdown_disclosure')}:** {t(language, 'report.markdown_disclosure_text')}",
        "",
        f"## {t(language, 'report.section.verified')}",
        "",
        f"- {t(language, 'report.result.energy', baseline=bundle.baseline.metrics.energy_kwh, optimized=bundle.optimized.metrics.energy_kwh, saving=optimized['energy_savings_pct'])}",
        f"- {t(language, 'report.result.peak', baseline=bundle.baseline.metrics.peak_kw, optimized=bundle.optimized.metrics.peak_kw, reduction=optimized['peak_reduction_pct'])}",
        f"- {t(language, 'report.result.comfort', comfort=bundle.optimized.metrics.occupied_comfort_pct)}",
        f"- {t(language, 'report.result.rcx', detected=int(bundle.diagnostic_scorecard['detected'].sum()), delay=bundle.diagnostic_scorecard['detection_delay_minutes'].median())}",
        "",
        f"## {t(language, 'report.section.boundaries')}",
        "",
        *[f"- {t(language, f'report.boundary.short.{position}')}" for position in range(1, 5)],
        "",
        f"## {t(language, 'report.section.references')}",
        "",
        f"- [{t(language, 'report.source.hko')}](https://www.hko.gov.hk/en/cis/normal/1991_2020/dnormal08.htm)",
        f"- [{t(language, 'report.source.emsd')}](https://www.emsd.gov.hk/filemanager/en/content_718/Technical_Guidelines_Retro-commissioning.pdf)",
        "",
    ]
    return "\n".join(lines)


def export_portfolio(bundle: ScenarioBundle, output_dir: Path | str) -> list[Path]:
    """Write all reproducible portfolio artifacts and return their paths."""

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    def write_text(name: str, content: str) -> None:
        path = target / name
        path.write_text(content, encoding="utf-8")
        paths.append(path)

    def write_csv(name: str, frame: pd.DataFrame) -> None:
        path = target / name
        frame.to_csv(path, index=False)
        paths.append(path)

    write_text("rcx-report.html", render_html_report(bundle))
    write_text("rcx-report.md", render_markdown_report(bundle))
    write_csv("scenario-comparison.csv", bundle.comparison)
    write_csv("diagnostic-scorecard.csv", bundle.diagnostic_scorecard)
    write_csv("diagnostic-findings.csv", _findings_frame(bundle))
    write_csv("alarm-events.csv", _alarms_frame(bundle))
    write_csv("bms-point-registry.csv", bundle.point_registry)
    write_csv("trends-baseline.csv", bundle.baseline.trends)
    write_csv("trends-optimized.csv", bundle.optimized.trends)
    for category, run in bundle.fault_runs.items():
        write_csv(f"trends-fault-{category}.csv", run.trends)

    manifest_path = target / "manifest.json"
    manifest = {
        "project": "SmartBMS-RCx",
        "version": "0.1.0",
        "data_classification": "synthetic",
        "deterministic_seed": bundle.baseline.trends.attrs.get("seed"),
        "files": sorted(path.name for path in paths) + ["manifest.json"],
        "disclosure": "Synthetic simulation; not measured building performance.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    paths.append(manifest_path)
    return paths
