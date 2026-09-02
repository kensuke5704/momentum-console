#!/usr/bin/env python3
from __future__ import annotations

import gzip
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "data" / "sec-nport" / "bootstrap.json.gz"
OUT = ROOT / "data" / "research" / "nq-nport-overlap-window-2019.json"

spec = importlib.util.spec_from_file_location("bridge2019", ROOT / "scripts" / "research-nq-bridge-2019.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def month(s: str | None) -> str | None:
    return s[:7] if isinstance(s, str) and len(s) >= 7 else None


def main() -> None:
    nq = [x for x in bridge.index_2019() if x.get("form") == "N-Q"]
    nq_by_month = Counter(month(x.get("dateFiled")) for x in nq)
    nq_by_month.pop(None, None)

    with gzip.open(BOOTSTRAP, "rt", encoding="utf-8") as f:
        payload = json.load(f)
    filings = payload.get("snapshots") or payload.get("filings") or []
    nport_2019 = [x for x in filings if str(x.get("filingDate") or "").startswith("2019-")]
    nport_by_filing_month = Counter(month(x.get("filingDate")) for x in nport_2019)
    nport_by_report_month = Counter(month(x.get("reportDate")) for x in nport_2019)
    nport_by_filing_month.pop(None, None)
    nport_by_report_month.pop(None, None)

    nq_months = set(nq_by_month)
    nport_months = set(nport_by_filing_month)
    same_filing_months = sorted(nq_months & nport_months)

    all_nport_dates = sorted(str(x.get("filingDate")) for x in nport_2019 if x.get("filingDate"))
    all_nport_reports = sorted(str(x.get("reportDate")) for x in nport_2019 if x.get("reportDate"))
    all_nq_dates = sorted(str(x.get("dateFiled")) for x in nq if x.get("dateFiled"))

    out = {
        "year": 2019,
        "purpose": "Determine the literal public-filing overlap window between legacy Form N-Q and the repository N-PORT bootstrap before any universe-fidelity or strategy-performance comparison.",
        "nq": {
            "filings": len(nq),
            "firstFilingDate": all_nq_dates[0] if all_nq_dates else None,
            "lastFilingDate": all_nq_dates[-1] if all_nq_dates else None,
            "filingMonthCounts": dict(sorted(nq_by_month.items())),
        },
        "nport": {
            "filings2019": len(nport_2019),
            "firstFilingDate": all_nport_dates[0] if all_nport_dates else None,
            "lastFilingDate": all_nport_dates[-1] if all_nport_dates else None,
            "firstReportDate": all_nport_reports[0] if all_nport_reports else None,
            "lastReportDate": all_nport_reports[-1] if all_nport_reports else None,
            "filingMonthCounts": dict(sorted(nport_by_filing_month.items())),
            "reportMonthCounts": dict(sorted(nport_by_report_month.items())),
        },
        "sameFilingMonths": same_filing_months,
        "sameFilingMonthCount": len(same_filing_months),
        "interpretation": "Only months in sameFilingMonths are candidates for a literal contemporaneous public-filing overlap test. If empty or sparse, use a transition-boundary validation rather than pretending there is a broad simultaneous regime.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
