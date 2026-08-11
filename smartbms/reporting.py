"""Deterministic HTML, Markdown, and CSV portfolio exports."""

from __future__ import annotations

from dataclasses import asdict
from html import escape
import json
from pathlib import Path

import pandas as pd

from smartbms.diagnostics import findings_to_frame
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


def render_html_report(bundle: ScenarioBundle) -> str:
    """Render a self-contained, escaped technical report."""

    optimized = bundle.comparison.loc[bundle.comparison["scenario"] == "optimized"].iloc[0]
    findings = _findings_frame(bundle)
    comparison_table = bundle.comparison.round(3).to_html(index=False, escape=True, classes="data")
    scorecard_table = bundle.diagnostic_scorecard.to_html(index=False, escape=True, classes="data")
    findings_table = findings.to_html(index=False, escape=True, classes="data")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartBMS-RCx Technical Report</title>
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
<div class="eyebrow">Synthetic controls engineering proof of concept</div>
<h1>SmartBMS-RCx Technical Report</h1>
<p>Two-zone Hong Kong office HVAC simulation, supervisory optimization, BMS semantics, and retro-commissioning diagnostics.</p>
<div class="notice"><strong>Disclosure:</strong> All weather/load/BMS trends are synthetic. Results are scenario-specific and are not measured building performance, a savings guarantee, or evidence of a live BACnet/Modbus deployment.</div>
<div class="kpis">
  <div class="kpi"><b>{optimized['energy_savings_pct']:.3f}%</b><span>simulated energy saving</span></div>
  <div class="kpi"><b>{optimized['peak_reduction_pct']:.3f}%</b><span>simulated peak reduction</span></div>
  <div class="kpi"><b>{bundle.optimized.metrics.occupied_comfort_pct:.1f}%</b><span>optimized occupied comfort</span></div>
  <div class="kpi"><b>{int(bundle.diagnostic_scorecard['detected'].sum())}/4</b><span>injected faults detected</span></div>
</div>
<h2>Scenario comparison</h2>
<p>Energy is interval power integrated at 15 minutes. Comfort is the share of occupied zone-samples inside 22–26 °C. Cost is illustrative and uses a disclosed synthetic tariff.</p>
<div class="table-wrap">{comparison_table}</div>
<h2>RCx diagnostic scorecard</h2>
<p>Each rule requires four consecutive samples. A 45-minute delay therefore means detection at the fourth 15-minute sample.</p>
<div class="table-wrap">{scorecard_table}</div>
<h2>Findings and actions</h2>
<div class="table-wrap">{findings_table}</div>
<h2>Model boundary</h2>
<ul>
  <li>First-order two-zone RC thermal model and simplified shared AHU/chiller power model.</li>
  <li>Baseline schedule/P control versus bounded one-hour candidate search; this is not a trained AI model or full MPC implementation.</li>
  <li>Faults: sensor bias, stuck valve, fouled filter, and after-hours operation.</li>
  <li>BACnet objects and Modbus registers are simulated point metadata only.</li>
</ul>
<h2>Source anchors</h2>
<ul>
  <li><a href="https://www.hko.gov.hk/en/cis/normal/1991_2020/dnormal08.htm">Hong Kong Observatory 1991–2020 August normals</a> — anchors for synthetic summer profile shape.</li>
  <li><a href="https://www.emsd.gov.hk/filemanager/en/content_718/Technical_Guidelines_Retro-commissioning.pdf">EMSD Technical Guidelines on Retro-commissioning</a> — RCx workflow context.</li>
</ul>
<footer>Deterministic project seed: 20260803. Report content is generated from the same APIs used by the dashboard and tests.</footer>
</main></body></html>"""


def render_markdown_report(bundle: ScenarioBundle) -> str:
    optimized = bundle.comparison.loc[bundle.comparison["scenario"] == "optimized"].iloc[0]
    lines = [
        "# SmartBMS-RCx Technical Report",
        "",
        "> **Synthetic-data disclosure:** This proof of concept uses generated weather, loads, faults, and BMS trends. It is not measured building performance or a savings guarantee.",
        "",
        "## Verified scenario result",
        "",
        f"- Energy: {bundle.baseline.metrics.energy_kwh:.3f} → {bundle.optimized.metrics.energy_kwh:.3f} kWh ({optimized['energy_savings_pct']:.3f}% simulated saving)",
        f"- Peak: {bundle.baseline.metrics.peak_kw:.3f} → {bundle.optimized.metrics.peak_kw:.3f} kW ({optimized['peak_reduction_pct']:.3f}% simulated reduction)",
        f"- Optimized occupied comfort: {bundle.optimized.metrics.occupied_comfort_pct:.3f}% inside 22–26 °C",
        f"- RCx detection: {int(bundle.diagnostic_scorecard['detected'].sum())}/4 injected faults; median delay {bundle.diagnostic_scorecard['detection_delay_minutes'].median():.0f} minutes",
        "",
        "## Boundaries",
        "",
        "- Two-zone first-order RC model; simplified fan/chiller energy.",
        "- Bounded predictive candidate search, not a trained model or full MPC.",
        "- Simulated BACnet/Modbus metadata; no live building connection.",
        "- Illustrative tariff; no commercial savings claim.",
        "",
        "## References",
        "",
        "- [HKO 1991–2020 August normals](https://www.hko.gov.hk/en/cis/normal/1991_2020/dnormal08.htm)",
        "- [EMSD Technical Guidelines on Retro-commissioning](https://www.emsd.gov.hk/filemanager/en/content_718/Technical_Guidelines_Retro-commissioning.pdf)",
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
        "deterministic_seed": 20260803,
        "files": sorted(path.name for path in paths) + ["manifest.json"],
        "disclosure": "Synthetic simulation; not measured building performance.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    paths.append(manifest_path)
    return paths
