#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "data/sec-nport/bootstrap.json.gz"
HISTORY = ROOT / "data/universe-history.json"
OUT = ROOT / "data/research/universe-transition-window.json"


def main() -> None:
    with gzip.open(BOOT, "rt", encoding="utf-8") as f:
        nport = json.load(f)
    history = json.loads(HISTORY.read_text())

    report_dates = [x.get("reportDate") for x in nport if x.get("reportDate")]
    filing_dates = [x.get("filingDate") for x in nport if x.get("filingDate")]
    report_months = Counter(x[:7] for x in report_dates)
    filing_months = Counter(x[:7] for x in filing_dates)

    if isinstance(history, dict):
        if isinstance(history.get("months"), list):
            months = history["months"]
        elif isinstance(history.get("history"), list):
            months = history["history"]
        else:
            months = [v for v in history.values() if isinstance(v, dict) and ("signalMonth" in v or "asOf" in v)]
    elif isinstance(history, list):
        months = history
    else:
        months = []
    signal_months = sorted({x.get("signalMonth") for x in months if isinstance(x, dict) and x.get("signalMonth")})

    out = {
        "nportFilings": len(nport),
        "earliestReportDate": min(report_dates) if report_dates else None,
        "latestReportDate": max(report_dates) if report_dates else None,
        "earliestFilingDate": min(filing_dates) if filing_dates else None,
        "latestFilingDate": max(filing_dates) if filing_dates else None,
        "first12ReportMonths": sorted(report_months.items())[:12],
        "first12FilingMonths": sorted(filing_months.items())[:12],
        "universeHistoryRecords": len(months),
        "earliestSignalMonth": signal_months[0] if signal_months else None,
        "first12SignalMonths": signal_months[:12],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
