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

pspec = importlib.util.spec_from_file_location("nqpilot", ROOT / "scripts" / "research-nq-parser-pilot.py")
nqpilot = importlib.util.module_from_spec(pspec)
pspec.loader.exec_module(nqpilot)

TARGET = re.compile(r"SELECT SECTOR SPDR|STREETTRACKS|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)
SCHEDULE = re.compile(r"SCHEDULE OF INVESTMENTS|PORTFOLIO OF INVESTMENTS|PORTFOLIO HOLDINGS|STATEMENT OF INVESTMENTS", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", s.upper()).strip()


def occurrences(text: str, series_name: str) -> list[int]:
    n = norm(series_name)
    if not n:
        return []
    toks = [re.escape(t) for t in n.split() if len(t) > 1]
    if not toks:
        return []
    pat = re.compile(r"\b" + r"\W+".join(toks) + r"\b", re.I)
    return [m.start() for m in pat.finditer(text)]


def best_anchor(hits: list[int], schedules: list[int]) -> tuple[int | None, int | None]:
    pairs = [(abs(h - q), h, q) for h in hits for q in schedules]
    if not pairs:
        return None, None
    _, h, q = min(pairs)
    if abs(h - q) > 12000:
        return None, None
    # Start a little before the earlier of the series title and schedule marker.
    return max(0, min(h, q) - 1500), abs(h - q)


def parse_segment(text: str) -> tuple[str, int, float]:
    method, _, _, holdings = nqpilot.parse_holdings(text)
    # Structural screen only. Current N-PORT eligibility also requires 10-120 holdings.
    count = len(holdings)
    total_value = sum(max(0.0, float(h.get("marketValue") or 0)) for h in holdings)
    return method, count, total_value


def main() -> None:
    idx = json.loads(IDX.read_text())
    filings = [x for x in idx["filings"] if x.get("form") == "N-Q" and TARGET.search(str(x.get("company") or ""))]
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

            anchors = []
            raw = []
            for s in etf:
                name = s.get("seriesName") or ""
                hits = occurrences(text, name)
                anchor, nearest = best_anchor(hits, sched)
                raw.append((s, hits, anchor, nearest))
                if anchor is not None:
                    anchors.append(anchor)
            boundaries = sorted(set(anchors))

            rows = []
            segmentable = 0
            parsed = 0
            structurally_usable = 0
            for s, hits, anchor, nearest in raw:
                local = anchor is not None
                segmentable += int(local)
                method = None
                parsed_holdings = 0
                parsed_value = 0.0
                if local:
                    next_candidates = [a for a in boundaries if a > anchor]
                    end = next_candidates[0] if next_candidates else min(len(text), anchor + 180000)
                    # Avoid tiny/empty slices from duplicate nearby titles.
                    if end - anchor < 2500:
                        end = min(len(text), anchor + 180000)
                    method, parsed_holdings, parsed_value = parse_segment(text[anchor:end])
                    parsed += int(parsed_holdings > 0)
                    structurally_usable += int(10 <= parsed_holdings <= 120 and parsed_value > 0)
                rows.append({
                    "seriesId": s.get("seriesId"),
                    "seriesName": s.get("seriesName"),
                    "tickers": s.get("etfTickers", []),
                    "nameOccurrences": len(hits),
                    "nearestScheduleChars": nearest,
                    "locallySegmentable": local,
                    "parseMethod": method,
                    "parsedHoldings": parsed_holdings,
                    "parsedMarketValueTotal": parsed_value,
                    "structurallyUsable": bool(10 <= parsed_holdings <= 120 and parsed_value > 0),
                })
            r = {
                "company": x["company"],
                "cik": x["cik"],
                "dateFiled": x["dateFiled"],
                "seriesCount": len(etf),
                "scheduleMarkers": len(sched),
                "segmentableSeries": segmentable,
                "parsedSeries": parsed,
                "structurallyUsableSeries": structurally_usable,
                "series": rows,
            }
            print(
                f"{i}/{len(chosen)} {x['company'][:42]} ETFseries={len(etf)} schedules={len(sched)} "
                f"segmentable={segmentable} parsed={parsed} usable10to120={structurally_usable}",
                flush=True,
            )
        except Exception as e:
            r = {"company": x.get("company"), "cik": x.get("cik"), "error": repr(e)}
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}", flush=True)
        results.append(r)

    ok = [r for r in results if "error" not in r and r.get("seriesCount")]
    total_series = sum(r["seriesCount"] for r in ok)
    total_segmentable = sum(r["segmentableSeries"] for r in ok)
    total_parsed = sum(r["parsedSeries"] for r in ok)
    total_usable = sum(r["structurallyUsableSeries"] for r in ok)
    summary = {
        "year": 2006,
        "sampleRule": "One deterministic N-Q filing per known ETF registrant; no return/performance selection.",
        "registrants": len(chosen),
        "fetchSuccess": len([r for r in results if "error" not in r]),
        "totalEtfSeries": total_series,
        "segmentableSeries": total_segmentable,
        "segmentableRate": total_segmentable / total_series if total_series else None,
        "parsedSeries": total_parsed,
        "parsedRate": total_parsed / total_series if total_series else None,
        "structurallyUsableSeries": total_usable,
        "structurallyUsableRate": total_usable / total_series if total_series else None,
        "structuralEligibilityRule": "10 <= parsed holdings <= 120 and positive parsed market value; no returns used.",
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
