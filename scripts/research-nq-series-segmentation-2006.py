#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "data" / "research" / "nq-index-2006.json"
OUT = ROOT / "data" / "research" / "nq-series-segmentation-2006.json"

spec = importlib.util.spec_from_file_location("meta", ROOT / "scripts" / "research-nq-series-metadata-2006.py")
meta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(meta)

TARGET = re.compile(r"SELECT SECTOR SPDR|STREETTRACKS|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)
SCHEDULE = re.compile(r"SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", s.upper()).strip()


def occurrences(text: str, series_name: str) -> list[int]:
    n = norm(series_name)
    if not n:
        return []
    # Search a tolerant regex built from significant tokens.
    toks = [re.escape(t) for t in n.split() if len(t) > 1]
    if not toks:
        return []
    pat = re.compile(r"\b" + r"\W+".join(toks) + r"\b", re.I)
    return [m.start() for m in pat.finditer(text)]


def main() -> None:
    idx = json.loads(IDX.read_text())
    filings = [x for x in idx["filings"] if x.get("form") == "N-Q" and TARGET.search(str(x.get("company") or ""))]
    # One deterministic filing per registrant.
    chosen = []
    seen = set()
    for x in filings:
        if x["cik"] in seen:
            continue
        seen.add(x["cik"])
        chosen.append(x)

    results = []
    for i, x in enumerate(chosen, 1):
        try:
            _, text = meta.fetch_prefix(meta.sec_url(x["filename"]))
            series = meta.parse_series_contracts(text, x["company"])
            etf = [s for s in series if s["isEtf"]]
            sched = [m.start() for m in SCHEDULE.finditer(text)]
            rows = []
            uniquely_locatable = 0
            for s in etf:
                name = s.get("seriesName") or ""
                hits = occurrences(text, name)
                # A series is locally segmentable when at least one name occurrence lies reasonably
                # close to a schedule marker; no investment-return information is used.
                nearest = min((abs(h - q) for h in hits for q in sched), default=None)
                local = bool(hits and nearest is not None and nearest <= 12000)
                uniquely_locatable += int(local)
                rows.append({
                    "seriesId": s.get("seriesId"),
                    "seriesName": name,
                    "tickers": s.get("etfTickers", []),
                    "nameOccurrences": len(hits),
                    "nearestScheduleChars": nearest,
                    "locallySegmentable": local,
                })
            r = {
                "company": x["company"],
                "cik": x["cik"],
                "dateFiled": x["dateFiled"],
                "seriesCount": len(etf),
                "scheduleMarkers": len(sched),
                "segmentableSeries": uniquely_locatable,
                "segmentableRate": uniquely_locatable / len(etf) if etf else None,
                "series": rows,
            }
            print(f"{i}/{len(chosen)} {x['company'][:42]} ETFseries={len(etf)} schedules={len(sched)} segmentable={uniquely_locatable}", flush=True)
        except Exception as e:
            r = {"company": x.get("company"), "cik": x.get("cik"), "error": repr(e)}
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}", flush=True)
        results.append(r)

    ok = [r for r in results if "error" not in r and r.get("seriesCount")]
    total_series = sum(r["seriesCount"] for r in ok)
    total_segmentable = sum(r["segmentableSeries"] for r in ok)
    summary = {
        "year": 2006,
        "sampleRule": "One deterministic N-Q filing per known ETF registrant; no return/performance selection.",
        "registrants": len(chosen),
        "fetchSuccess": len([r for r in results if "error" not in r]),
        "totalEtfSeries": total_series,
        "segmentableSeries": total_segmentable,
        "segmentableRate": total_segmentable / total_series if total_series else None,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
