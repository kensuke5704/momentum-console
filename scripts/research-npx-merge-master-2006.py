#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "research" / "npx-security-master-2006.json"
SUPP = ROOT / "data" / "research" / "npx-security-master-broad-fund-supplement-2006.json"
OUT = ROOT / "data" / "research" / "npx-security-master-2006-merged.json"


def main() -> None:
    base = json.loads(BASE.read_text())
    supp = json.loads(SUPP.read_text())
    rows = list(base.get("records", [])) + list(supp.get("records", []))

    unique = {}
    for row in rows:
        key = (row.get("normalizedIssuer"), row.get("ticker"), row.get("securityId"))
        unique.setdefault(key, row)
    merged = list(unique.values())

    paired = [r for r in merged if r.get("ticker") and r.get("securityId")]
    by_issuer = defaultdict(set)
    for row in paired:
        by_issuer[row["normalizedIssuer"]].add((row["ticker"], row["securityId"]))
    ambiguous = {k: sorted([list(x) for x in v]) for k, v in by_issuer.items() if len(v) > 1}

    out = {
        "year": 2006,
        "purpose": "Merged structural N-PX security master: frozen deterministic baseline plus pre-fixed broad-fund-family supplement. No strategy-return data used.",
        "sampleRule": f"Baseline: {base.get('sampleRule')}; supplement: {supp.get('sourceRule')}",
        "baselinePairedRecords": base.get("pairedRecords"),
        "supplementPairedRecords": supp.get("pairedRecords"),
        "pairedRecords": len(paired),
        "uniqueRecords": len(merged),
        "uniqueTickers": len({r["ticker"] for r in paired}),
        "uniqueSecurityIds": len({r["securityId"] for r in paired}),
        "uniqueNormalizedIssuers": len({r["normalizedIssuer"] for r in paired}),
        "ambiguousNormalizedIssuers": len(ambiguous),
        "records": merged,
        "ambiguousIssuerMappings": ambiguous,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in {"records", "ambiguousIssuerMappings"}}), flush=True)


if __name__ == "__main__":
    main()
