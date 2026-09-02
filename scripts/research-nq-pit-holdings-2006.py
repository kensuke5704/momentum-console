#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDX = ROOT / "data" / "research" / "nq-index-2006.json"
OUT = ROOT / "data" / "research" / "nq-pit-holdings-2006.json"

sspec = importlib.util.spec_from_file_location("seg", ROOT / "scripts" / "research-nq-series-segmentation-2006.py")
seg = importlib.util.module_from_spec(sspec)
sspec.loader.exec_module(seg)

REPORT_DATE = re.compile(r"(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$")
TARGET = re.compile(r"SELECT SECTOR SPDR|STREETTRACKS|POWERSHARES EXCHANGE TRADED|RYDEX ETF TRUST|PROSHARES", re.I)


def iso_yyyymmdd(raw: str | None) -> str | None:
    if not raw or len(raw) != 8:
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def accession_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    if re.fullmatch(r"\d{18}", stem):
        return f"{stem[:10]}-{stem[10:12]}-{stem[12:]}"
    return stem


def normalized_holdings(block: str) -> tuple[str, list[dict], float]:
    method, _, _, parsed = seg.nqpilot.parse_holdings(block)
    positive = []
    for h in parsed:
        value = max(0.0, float(h.get("marketValue") or 0))
        description = " ".join(str(h.get("description") or "").split())
        if value <= 0 or not description:
            continue
        positive.append({
            "description": description,
            "marketValue": value,
            "quantityOrPrincipal": h.get("quantityOrPrincipal"),
        })
    total = sum(h["marketValue"] for h in positive)
    if total > 0:
        for h in positive:
            h["weight"] = 100.0 * h["marketValue"] / total
    return method, positive, total


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

    records = []
    filing_results = []
    for i, x in enumerate(chosen, 1):
        try:
            _, submission = seg.meta.fetch_prefix(seg.meta.sec_url(x["filename"]))
            report_m = REPORT_DATE.search(submission)
            report_date = iso_yyyymmdd(report_m.group(1) if report_m else None)
            series = seg.meta.parse_series_contracts(submission, x["company"])
            etf = [s for s in series if s["isEtf"]]
            primary_name, text = seg.embedded_primary_nq(submission)
            markers = list(seg.SCHEDULE.finditer(text))
            mapped: dict[str, dict] = {}
            unmapped = 0

            for j, marker in enumerate(markers):
                start = marker.start()
                end = markers[j + 1].start() if j + 1 < len(markers) else min(len(text), start + 300000)
                block = text[start:end]
                s, score = seg.map_schedule_to_series(block, etf)
                if not s or not s.get("seriesId"):
                    unmapped += 1
                    continue
                method, holdings, total = normalized_holdings(block)
                count = len(holdings)
                candidate = {
                    "accession": accession_from_filename(x["filename"]),
                    "cik": x["cik"],
                    "registrant": x["company"],
                    "form": x["form"],
                    "filingDate": x["dateFiled"],
                    "reportDate": report_date,
                    "sourceFilename": x["filename"],
                    "primaryDocument": primary_name,
                    "seriesId": s.get("seriesId"),
                    "seriesName": s.get("seriesName"),
                    "fundTickers": s.get("etfTickers", []),
                    "mappingScore": score,
                    "parseMethod": method,
                    "eligibleByName": seg.eligible_name(s.get("seriesName") or ""),
                    "parsedMarketValueTotal": total,
                    "holdings": holdings,
                }
                candidate["structurallyUsable"] = bool(
                    candidate["eligibleByName"] and 10 <= count <= 120 and total > 0
                )
                current = mapped.get(s["seriesId"])
                if current is None or (count, score) > (len(current["holdings"]), current["mappingScore"]):
                    mapped[s["seriesId"]] = candidate

            usable = [r for r in mapped.values() if r["structurallyUsable"]]
            records.extend(usable)
            filing_results.append({
                "company": x["company"],
                "cik": x["cik"],
                "filingDate": x["dateFiled"],
                "reportDate": report_date,
                "registeredEtfSeries": len(etf),
                "scheduleMarkers": len(markers),
                "mappedSeries": len(mapped),
                "usableSeries": len(usable),
                "unmappedScheduleBlocks": unmapped,
            })
            print(
                f"{i}/{len(chosen)} {x['company'][:42]} mapped={len(mapped)} usable={len(usable)} recordsTotal={len(records)}",
                flush=True,
            )
        except Exception as e:
            filing_results.append({"company": x.get("company"), "cik": x.get("cik"), "error": repr(e)})
            print(f"{i}/{len(chosen)} FAIL {x.get('company')} {e!r}", flush=True)

    holding_counts = [len(r["holdings"]) for r in records]
    weight_sum_errors = [abs(sum(h["weight"] for h in r["holdings"]) - 100.0) for r in records]
    summary = {
        "year": 2006,
        "purpose": "Point-in-time legacy N-Q ETF-series holdings representation pilot. No return/performance data used.",
        "sampleRule": "One deterministic N-Q filing per known ETF registrant, identical registrant sample to the segmentation pilot.",
        "weightRule": "Positive parsed market values normalized to 100 within each mapped series. These are parser-relative weights, not yet validated against reported net assets.",
        "tickerMappingStatus": "Holdings issuer descriptions are intentionally left unmapped here; issuer/security-id/ticker mapping is a separate validation stage.",
        "filingsAttempted": len(chosen),
        "filingsSucceeded": sum(1 for r in filing_results if "error" not in r),
        "pitSeriesRecords": len(records),
        "medianHoldingsPerRecord": sorted(holding_counts)[len(holding_counts) // 2] if holding_counts else None,
        "maxWeightSumError": max(weight_sum_errors) if weight_sum_errors else None,
        "records": records,
        "filingResults": filing_results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k not in {"records", "filingResults"}}), flush=True)


if __name__ == "__main__":
    main()
