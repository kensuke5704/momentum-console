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

lspec = importlib.util.spec_from_file_location("legacy_holdings", ROOT / "scripts" / "research-legacy-holdings-parser.py")
legacy_holdings = importlib.util.module_from_spec(lspec)
lspec.loader.exec_module(legacy_holdings)

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


def _normalize(parsed: list[dict]) -> tuple[list[dict], float]:
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
        positive.sort(key=lambda h: h["weight"], reverse=True)
    return positive, total


def _year_header_artifact(holdings: list[dict], total: float) -> bool:
    # Observed in legacy iShares N-Q tables: the old parser returned exactly one
    # pseudo-holding with market value equal to the prior report year (e.g. 2007,
    # 2009) because the Schedule heading was outside the HTML <TR> rows.
    return len(holdings) == 1 and total.is_integer() and 1900 <= total <= 2100


def normalized_holdings(block: str) -> tuple[str, list[dict], float]:
    method, _, _, parsed = seg.nqpilot.parse_holdings(block)
    positive, total = _normalize(parsed)

    # Preserve the established parser by default. The HTML fallback is permitted
    # only for the specific structural year-header artifact proven in 2008/2010
    # iShares filings. This avoids changing valid SPDR/plain-table parses merely
    # because another parser happens to yield more rows.
    if _year_header_artifact(positive, total):
        fallback_raw = legacy_holdings.parse_html_table(block)
        fallback, fallback_total = _normalize(fallback_raw)
        if len(fallback) >= 2 and fallback_total > 0 and legacy_holdings.structural_sanity(fallback):
            return "html-year-artifact-fallback", fallback, fallback_total

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
                mapping_context = text[max(0, start - 5000):min(end, start + 2500)]
                s, score = seg.map_schedule_to_series(mapping_context, etf)
                if not s or not s.get("seriesId"):
                    unmapped += 1
                    continue
                method, holdings, total = normalized_holdings(block)
                count = len(holdings)
                top10_weight = sum(h["weight"] for h in holdings[:10]) if holdings else 0.0
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
                    "top10Weight": top10_weight,
                    "holdings": holdings,
                }
                candidate["structurallyUsable"] = bool(
                    candidate["eligibleByName"]
                    and 10 <= count <= 120
                    and total > 0
                    and top10_weight >= 25.0
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
            print(f"{i}/{len(chosen)} {x['company'][:42]} mapped={len(mapped)} usable={len(usable)} recordsTotal={len(records)}", flush=True)
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
        "structuralEligibilityRule": "Production name exclusions plus 10 <= parsed holdings <= 120 and normalized top-10 weight >= 25%. N-Q lacks direct N-PORT US/CORP/EC fields, so country/issuer/asset parity remains unresolved.",
        "tickerMappingStatus": "Holdings issuer descriptions are intentionally left unmapped here; issuer/security-id/ticker mapping is a separate validation stage.",
        "seriesMappingRule": "Tight pre/post schedule-heading context; exact filing-time series name preferred; ambiguous ties and near-ties rejected.",
        "parserFallbackRule": "Established parser retained by default. HTML fallback is used only for an observed one-row year-header artifact (single pseudo-holding with total market value 1900..2100) and only when fallback rows pass structural sanity.",
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
