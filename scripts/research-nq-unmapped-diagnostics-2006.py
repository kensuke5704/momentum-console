#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/research/nq-npx-mapping-2006.json"
OUT = ROOT / "data/research/nq-npx-unmapped-diagnostics-2006.json"

ADR_RE = re.compile(r"\bADR\b|DEPOSITARY|DEPOSITORY", re.I)
CLASS_RE = re.compile(r"\bPFD\b|PREFERRED|\bPREF\b|\bCLASS\s+[A-Z]\b|\bCL\s+[A-Z]\b", re.I)


def category(row: dict) -> str:
    desc = row.get("description", "")
    cands = row.get("diagnosticCandidates", [])
    max_sim = max((float(x.get("similarity") or 0) for x in cands), default=0.0)
    if ADR_RE.search(desc):
        return "ADR_OR_DEPOSITARY"
    if CLASS_RE.search(desc):
        return "SECURITY_CLASS_OR_PREFERRED"
    if not cands:
        return "NO_MASTER_CANDIDATE"
    if max_sim >= 0.90:
        return "HIGH_SIMILARITY_NAME_GAP"
    if max_sim >= 0.82:
        return "MEDIUM_SIMILARITY_NAME_GAP"
    return "WEAK_SIMILARITY_CANDIDATE"


def main() -> None:
    src = json.loads(SRC.read_text())
    rows = [x for x in src.get("details", []) if x.get("status") == "UNMAPPED"]
    buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "weight": 0.0, "rows": []})
    for row in rows:
        cat = category(row)
        b = buckets[cat]
        b["count"] += 1
        b["weight"] += float(row.get("weight") or 0)
        b["rows"].append({
            "seriesId": row.get("seriesId"),
            "fundTickers": row.get("fundTickers", []),
            "description": row.get("description"),
            "weight": row.get("weight"),
            "normalizedAliases": row.get("normalizedAliases", []),
            "diagnosticCandidates": row.get("diagnosticCandidates", []),
        })
    for b in buckets.values():
        b["rows"] = sorted(b["rows"], key=lambda x: float(x.get("weight") or 0), reverse=True)
    total_weight = sum(float(x.get("weight") or 0) for x in rows)
    summary = {
        k: {
            "count": v["count"],
            "weight": v["weight"],
            "countShareOfUnmapped": v["count"] / len(rows) if rows else None,
            "weightShareOfUnmapped": v["weight"] / total_weight if total_weight else None,
        }
        for k, v in sorted(buckets.items())
    }
    out = {
        "year": 2006,
        "purpose": "Structural diagnosis of remaining N-Q to N-PX mapping gaps. Categories are diagnostic only; no fuzzy candidate is accepted as an identity.",
        "classificationRule": "ADR/security-class markers first; otherwise classify by presence and maximum string similarity of diagnostic N-PX issuer candidates. Similarity is not an acceptance rule.",
        "unmappedCount": len(rows),
        "unmappedWeight": total_weight,
        "summary": summary,
        "categories": dict(buckets),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({"unmappedCount": len(rows), "unmappedWeight": total_weight, "categories": summary}), flush=True)


if __name__ == "__main__":
    main()
