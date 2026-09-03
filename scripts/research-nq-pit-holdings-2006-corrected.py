#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/research/nq-pit-holdings-2006-corrected.json"

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts" / "research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)

REPORT_DATE = re.compile(r"(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$")
FILING_DATE = re.compile(r"(?im)^\s*FILED AS OF DATE:\s*(\d{8})\s*$")

# Frozen before this correction: these are the exact three N-Q submissions used
# by the prior PIT pilot. Only the page-to-series assignment method changes.
SOURCES = [
    {"company": "SELECT SECTOR SPDR TRUST", "cik": "1064641", "filename": "edgar/data/1064641/0000950135-06-001225.txt"},
    {"company": "RYDEX ETF TRUST", "cik": "1208211", "filename": "edgar/data/1208211/0000950135-06-001815.txt"},
    {"company": "STREETTRACKS SERIES TRUST", "cik": "1064642", "filename": "edgar/data/1064642/0000950135-06-003650.txt"},
]


def iso8(raw: str | None) -> str | None:
    if not raw or len(raw) != 8:
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def accession(filename: str) -> str:
    stem = Path(filename).stem
    if re.fullmatch(r"\d{18}", stem):
        return f"{stem[:10]}-{stem[10:12]}-{stem[12:]}"
    return stem


def parsed_holdings(combined: str) -> tuple[str, list[dict], float]:
    method, _, _, parsed = seg.nqpilot.parse_holdings(combined)
    out = []
    seen = set()
    for h in parsed:
        desc = " ".join(str(h.get("description") or "").split())
        value = max(0.0, float(h.get("marketValue") or 0))
        qty = h.get("quantityOrPrincipal")
        if not desc or value <= 0:
            continue
        key = (desc, qty, value)
        if key in seen:
            continue
        seen.add(key)
        out.append({"description": desc, "marketValue": value, "quantityOrPrincipal": qty})
    total = sum(h["marketValue"] for h in out)
    if total > 0:
        for h in out:
            h["weight"] = 100.0 * h["marketValue"] / total
        out.sort(key=lambda h: h["weight"], reverse=True)
    return method, out, total


def main() -> None:
    records = []
    source_results = []
    for source in SOURCES:
        try:
            _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(source["filename"]))
            report_m = REPORT_DATE.search(submission)
            filed_m = FILING_DATE.search(submission)
            report_date = iso8(report_m.group(1) if report_m else None)
            filing_date = iso8(filed_m.group(1) if filed_m else None)
            series = seg.meta.parse_series_contracts(submission, source["company"])
            etf = [s for s in series if s["isEtf"]]
            by_id = {s.get("seriesId"): s for s in etf if s.get("seriesId")}
            primary, text = seg.embedded_primary_nq(submission)
            grouped, audit = seg.grouped_schedule_blocks(text, etf)
            retained = 0
            for sid, blocks in grouped.items():
                s = by_id.get(sid)
                if not s:
                    continue
                method, holdings, total = parsed_holdings("\n".join(blocks))
                count = len(holdings)
                top10 = sum(h.get("weight", 0.0) for h in holdings[:10]) if holdings else 0.0
                usable = bool(
                    seg.eligible_name(s.get("seriesName") or "")
                    and 10 <= count <= 120
                    and total > 0
                    and top10 >= 25.0
                )
                if not usable:
                    continue
                retained += 1
                record = {
                    "accession": accession(source["filename"]),
                    "cik": source["cik"],
                    "registrant": source["company"],
                    "form": "N-Q",
                    "filingDate": filing_date,
                    "reportDate": report_date,
                    "sourceFilename": source["filename"],
                    "primaryDocument": primary,
                    "seriesId": sid,
                    "seriesName": s.get("seriesName"),
                    "fundTickers": s.get("etfTickers", []),
                    "assignmentRule": "EXPLICIT_SERIES_BOUNDARY_GROUP",
                    "schedulePages": len(blocks),
                    "parseMethod": method,
                    "eligibleByName": True,
                    "parsedMarketValueTotal": total,
                    "top10Weight": top10,
                    "structurallyUsable": True,
                    "holdings": holdings,
                }
                records.append(record)
                print("RETAINED", json.dumps({
                    "seriesName": record["seriesName"],
                    "tickers": record["fundTickers"],
                    "schedulePages": record["schedulePages"],
                    "holdingCount": count,
                    "top10Weight": top10,
                    "topHoldings": [h["description"] for h in holdings[:8]],
                }), flush=True)
            source_results.append({
                **source,
                "registeredEtfSeries": len(etf),
                "assignedScheduleMarkers": sum(1 for a in audit if a["seriesId"]),
                "unassignedScheduleMarkers": sum(1 for a in audit if not a["seriesId"]),
                "groupedSeries": len(grouped),
                "retainedSeries": retained,
            })
        except Exception as e:
            source_results.append({**source, "error": repr(e)})
            print("FAIL", source["company"], repr(e), flush=True)

    holding_counts = [len(r["holdings"]) for r in records]
    out = {
        "year": 2006,
        "purpose": "Corrected point-in-time N-Q ETF-series holdings pilot. Schedule pages are assigned by explicit filing-time series names and grouped before holdings parsing. No returns/performance data used.",
        "sourceRule": "Same three fixed N-Q submissions as the prior pilot; only structurally incorrect schedule-to-series assignment is replaced.",
        "assignmentRule": "Nearest exact registered series title around each schedule marker; continuation pages remain with that explicit series. Holdings/industry words never determine series identity.",
        "weightRule": "Positive parsed market values normalized to 100 within each corrected grouped series.",
        "structuralEligibilityRule": "Production-style name exclusion plus 10-120 corrected grouped holdings, positive parsed market value, and top-10 normalized weight >=25%. Country/issuer-type parity is still unresolved.",
        "sourceResults": source_results,
        "pitSeriesRecords": len(records),
        "medianHoldingsPerRecord": sorted(holding_counts)[len(holding_counts)//2] if holding_counts else None,
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k not in {"records", "sourceResults"}}), flush=True)


if __name__ == "__main__":
    main()
