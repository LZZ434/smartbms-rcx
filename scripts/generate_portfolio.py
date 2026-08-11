"""Generate all SmartBMS-RCx report and trend artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smartbms.reporting import export_portfolio
from smartbms.scenarios import run_portfolio_scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated",
        help="Directory for HTML, Markdown, CSV, and manifest outputs",
    )
    args = parser.parse_args()
    bundle = run_portfolio_scenarios()
    paths = export_portfolio(bundle, args.output)
    optimized = bundle.comparison.loc[bundle.comparison.scenario == "optimized"].iloc[0]
    print(
        "Verified synthetic result: "
        f"{optimized.energy_savings_pct:.3f}% energy saving, "
        f"{bundle.optimized.metrics.occupied_comfort_pct:.1f}% occupied comfort, "
        f"{int(bundle.diagnostic_scorecard.detected.sum())}/4 faults detected."
    )
    for path in paths:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
