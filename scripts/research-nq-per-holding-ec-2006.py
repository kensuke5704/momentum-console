#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIT = ROOT / "data/research/nq-pit-holdings-2006-corrected.json"
OUT = ROOT / "data/research/nq-per-holding-ec-2006.json"

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts" / "research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)

SECTION_PATTERNS = [
    ("COMMON_EQUITY", re.compile(r"\bCOMMON\s+(?:STOCKS?|SHARES?)\b", re.I)),
    ("PREFERRED", re.compile(r"\bPREFERRED\s+(?:STOCKS?|SHARES?|SECURITIES)\b", re.I)),
    ("SHORT_TERM", re.compile(r"\bSHORT[- ]TERM\s+INVESTMENTS?\b|\bMONEY\s+MARKET\b", re.I)),
    ("DEBT", re.compile(r"\b(?:CORPORATE\s+)?(?:BONDS?|NOTES?|DEBENTURES?|FIXED\s+INCOME)\b", re.I)),
]


def ntext(s: str) -> str:
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", s.upper()).split())


def holding_aliases(desc: str) -> list[str]:
    vals = [desc]
    # Remove N-Q footnote markers and security-class parentheticals only for
    # locating the already-parsed holding in its source text; this does not map identity.
    x = re.sub(r"\s*\([a-z](?:,[a-z])*\)\s*$", "", desc, flags=re.I)
    if x != desc:
        vals.append(x)
    x2 = re.sub(r"\s*\((?:CLASS|CL)\s+[A-Z0-9]+\)\s*", " ", x, flags=re.I)
    if x2 != x:
        vals.append(x2)
    out = []
    for v in vals:
        nv = ntext(v)
        if len(nv) >= 5 and nv not in out:
            out.append(nv)
    return out


def section_positions(vis: str) -> list[tuple[int, str]]:
    nv = ntext(vis)
    positions = []
    for sec, pat in SECTION_PATTERNS:
        for m in pat.finditer(nv):
            positions.append((m.start(), sec))
    return sorted(positions)


def locate_section(vis: str, desc: str) -> tuple[str, str | None]:
    nv = ntext(vis)
    positions = section_positions(vis)
    best_pos = None
    best_alias = None
    for alias in holding_aliases(desc):
        start = 0
        while True:
            pos = nv.find(alias, start)
            if pos < 0:
                break
            if best_pos is None or pos < best_pos:
                best_pos = pos
                best_alias = alias
            start = pos + max(1, len(alias))
    if best_pos is None:
        return "UNKNOWN", None
    prior = [(p, s) for p, s in positions if p < best_pos]
    if not prior:
        return "UNKNOWN", best_alias
    return max(prior, key=lambda x: x[0])[1], best_alias


def main() -> None:
    pit = json.loads(PIT.read_text())
    by_source = defaultdict(list)
    for record in pit["records"]:
        by_source[record["sourceFilename"]].append(record)

    results = []
    totals = defaultdict(float)
    for filename, records in by_source.items():
        company = records[0]["registrant"]
        _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(filename))
        series = seg.meta.parse_series_contracts(submission, company)
        etf = [s for s in series if s["isEtf"]]
        _, text = seg.embedded_primary_nq(submission)
        grouped, _ = seg.grouped_schedule_blocks(text, etf)

        for record in records:
            combined = "\n".join(grouped.get(record["seriesId"], []))
            vis = seg.visible(combined)
            section_count = defaultdict(int)
            section_weight = defaultdict(float)
            details = []
            for h in record["holdings"]:
                sec, alias = locate_section(vis, h["description"])
                w = float(h.get("weight") or 0)
                section_count[sec] += 1
                section_weight[sec] += w
                totals["count"] += 1
                totals["weight"] += w
                totals[f"count:{sec}"] += 1
                totals[f"weight:{sec}"] += w
                details.append({
                    "description": h["description"],
                    "weight": w,
                    "section": sec,
                    "matchedSourceAlias": alias,
                })
            row = {
                "seriesId": record["seriesId"],
                "seriesName": record["seriesName"],
                "fundTickers": record.get("fundTickers", []),
                "holdingCount": len(record["holdings"]),
                "sectionCount": dict(section_count),
                "sectionWeight": dict(section_weight),
                "knownCountRate": 1 - section_count.get("UNKNOWN", 0) / len(record["holdings"]) if record["holdings"] else None,
                "knownWeightRate": 1 - section_weight.get("UNKNOWN", 0.0) / 100.0 if record["holdings"] else None,
                "commonEquityCountRate": section_count.get("COMMON_EQUITY", 0) / len(record["holdings"]) if record["holdings"] else None,
                "commonEquityWeight": section_weight.get("COMMON_EQUITY", 0.0),
                "unknownExamples": [d["description"] for d in details if d["section"] == "UNKNOWN"][:12],
            }
            results.append(row)
            print("SERIES", json.dumps(row), flush=True)

    total_count = int(totals["count"])
    total_weight = totals["weight"]
    known_count = total_count - int(totals["count:UNKNOWN"])
    known_weight = total_weight - totals["weight:UNKNOWN"]
    out = {
        "year": 2006,
        "purpose": "Per-holding structural attribution of corrected N-Q PIT holdings to explicit schedule asset sections as a candidate legacy analogue for N-PORT ASSET_CAT=EC. No returns/performance data used.",
        "rule": "Locate each already-parsed holding description back in its corrected explicit-series source schedule and inherit only the nearest preceding explicit COMMON/PREFERRED/SHORT-TERM/DEBT heading. If source location or prior heading is not explicit, retain UNKNOWN.",
        "status": "Diagnostic only; no historical universe filtering yet.",
        "seriesCount": len(results),
        "holdingCount": total_count,
        "knownSectionCount": known_count,
        "knownSectionCountRate": known_count / total_count if total_count else None,
        "knownSectionWeightRate": known_weight / total_weight if total_weight else None,
        "commonEquityCount": int(totals["count:COMMON_EQUITY"]),
        "commonEquityCountRate": totals["count:COMMON_EQUITY"] / total_count if total_count else None,
        "commonEquityWeightRate": totals["weight:COMMON_EQUITY"] / total_weight if total_weight else None,
        "series": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "series"}), flush=True)


if __name__ == "__main__":
    main()
