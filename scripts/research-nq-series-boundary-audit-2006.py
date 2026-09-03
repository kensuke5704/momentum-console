#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/nq-series-boundary-audit-2006.json"
SOURCE = {"company": "STREETTRACKS SERIES TRUST", "filename": "edgar/data/1064642/0000950135-06-003650.txt"}

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts/research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)


def find_explicit_series(raw: str, series: list[dict]) -> list[dict]:
    vis = seg.visible(raw)
    nvis = seg.norm(vis)
    hits = []
    for s in series:
        name = s.get("seriesName") or ""
        nn = seg.norm(name)
        if nn and nn in nvis:
            hits.append({"seriesId": s.get("seriesId"), "seriesName": name, "tickers": s.get("etfTickers", [])})
    return hits


def main() -> None:
    _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(SOURCE["filename"]))
    series = seg.meta.parse_series_contracts(submission, SOURCE["company"])
    etf = [s for s in series if s["isEtf"]]
    primary, text = seg.embedded_primary_nq(submission)
    markers = list(seg.SCHEDULE.finditer(text))

    rows = []
    last_explicit = None
    explicit_boundaries = 0
    continuation_inherited = 0
    ambiguous = 0
    for j, marker in enumerate(markers):
        start = marker.start()
        # The fund title may be immediately before or after the schedule heading.
        window = text[max(0, start - 2500): min(len(text), start + 2500)]
        hits = find_explicit_series(window, etf)
        marker_text = seg.visible(text[start:min(len(text), start + 120)])
        is_cont = bool(re.search(r"SCHEDULE OF INVESTMENTS\s*\(CONTINUED\)|PORTFOLIO OF INVESTMENTS\s*\(CONTINUED\)|STATEMENT OF INVESTMENTS\s*\(CONTINUED\)", marker_text, re.I))
        chosen = None
        status = "NO_EXPLICIT"
        if len(hits) == 1:
            chosen = hits[0]
            last_explicit = chosen
            status = "EXPLICIT"
            explicit_boundaries += 1
        elif len(hits) > 1:
            status = "AMBIGUOUS_EXPLICIT"
            ambiguous += 1
        elif is_cont and last_explicit:
            chosen = last_explicit
            status = "INHERITED_CONTINUED"
            continuation_inherited += 1
        row = {
            "scheduleIndex": j,
            "markerText": marker_text,
            "isContinued": is_cont,
            "status": status,
            "explicitHits": hits,
            "chosen": chosen,
            "before": seg.visible(text[max(0, start - 800):start])[-600:],
            "after": seg.visible(text[start:min(len(text), start + 1000)])[:800],
        }
        rows.append(row)
        print("BOUNDARY", json.dumps({k: row[k] for k in ("scheduleIndex", "isContinued", "status", "explicitHits", "chosen")}), flush=True)
        print(" BEFORE", row["before"][-350:], flush=True)
        print(" AFTER ", row["after"][:350], flush=True)

    explicit_series = {h["seriesId"] for r in rows for h in r["explicitHits"]}
    out = {
        "year": 2006,
        "purpose": "Structural audit of explicit ETF-series titles around N-Q schedule markers. No holdings-content similarity and no returns used for assignment.",
        "source": SOURCE,
        "primaryDocument": primary,
        "registeredEtfSeries": len(etf),
        "scheduleMarkers": len(markers),
        "uniqueExplicitSeries": len(explicit_series),
        "explicitBoundaryMarkers": explicit_boundaries,
        "continuedInheritedMarkers": continuation_inherited,
        "ambiguousExplicitMarkers": ambiguous,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
