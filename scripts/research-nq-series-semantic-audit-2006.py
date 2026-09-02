#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NQ = ROOT / "data/research/nq-pit-holdings-2006.json"
OUT = ROOT / "data/research/nq-series-semantic-audit-2006.json"

# Filing-structure regression anchors only. These are not selected from returns
# or strategy outcomes. The purpose is to detect obvious neighboring-series
# assignment errors in known 2006 ETF schedules.
AUDITS = {
    "XLE": {
        "minAnchors": 3,
        "anchors": ["EXXON", "CHEVRON", "CONOCOPHILLIPS", "HALLIBURTON", "SCHLUMBERGER"],
    },
    "XLI": {
        "minAnchors": 3,
        "anchors": ["GENERAL ELECTRIC", "UNITED PARCEL", "3M", "BOEING", "CATERPILLAR"],
    },
    "XLB": {
        "minAnchors": 3,
        "anchors": ["DOW CHEMICAL", "DU PONT", "DUPONT", "ALCOA", "NEWMONT"],
    },
    "XLK": {
        "minAnchors": 3,
        "anchors": ["MICROSOFT", "INTEL", "IBM", "CISCO", "HEWLETT"],
    },
    "KBE": {
        "minAnchors": 3,
        "anchors": ["JPMORGAN", "BANK OF AMERICA", "CITIGROUP", "WELLS FARGO"],
    },
    "KCE": {
        "minAnchors": 3,
        "anchors": ["GOLDMAN", "MERRILL", "MORGAN STANLEY", "LEHMAN"],
    },
    "KIE": {
        "minAnchors": 3,
        "anchors": ["AIG", "AMERICAN INTERNATIONAL", "PRUDENTIAL", "ALLSTATE", "METLIFE"],
    },
}


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s.upper()).split())


def main() -> None:
    nq = json.loads(NQ.read_text())
    by_ticker = {}
    for record in nq.get("records", []):
        for ticker in record.get("fundTickers", []):
            by_ticker[ticker] = record

    results = []
    failures = []
    for ticker, rule in AUDITS.items():
        record = by_ticker.get(ticker)
        if not record:
            results.append({"ticker": ticker, "status": "NOT_RETAINED", "passed": True})
            continue
        holdings = [norm(h.get("description") or "") for h in record.get("holdings", [])]
        matched = []
        for anchor in rule["anchors"]:
            a = norm(anchor)
            if any(a in h for h in holdings):
                matched.append(anchor)
        passed = len(matched) >= int(rule["minAnchors"])
        row = {
            "ticker": ticker,
            "seriesName": record.get("seriesName"),
            "holdingCount": len(holdings),
            "matchedAnchors": matched,
            "requiredAnchors": rule["minAnchors"],
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
        }
        results.append(row)
        if not passed:
            failures.append(row)

    out = {
        "year": 2006,
        "purpose": "Deterministic semantic regression audit for N-Q schedule-to-series assignment. No price, return, or strategy-performance data used.",
        "rule": "For retained known ETF series, require multiple canonical issuer-name anchors that should be present in the corresponding 2006 sector schedule. Non-retained series do not fail the audit.",
        "auditedRetainedSeries": sum(1 for r in results if r["status"] != "NOT_RETAINED"),
        "failedSeries": len(failures),
        "passed": not failures,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "results"}), flush=True)
    for row in results:
        print("AUDIT", json.dumps(row), flush=True)
    if failures:
        raise SystemExit(f"semantic audit failed for {len(failures)} retained series")


if __name__ == "__main__":
    main()
