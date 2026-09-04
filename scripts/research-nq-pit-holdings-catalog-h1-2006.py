#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/research/sec-historical-etf-series-source-catalog-h1-2006.json"
INVENTORY = ROOT / "data/research/sec-marketwide-nq-inventory-h1-2006.json"
OUT = ROOT / "data/research/nq-pit-holdings-catalog-h1-2006.json"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}
MAX_BYTES = 24_000_000
REPORT_DATE = re.compile(r"(?im)^\s*CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$")
FILING_DATE = re.compile(r"(?im)^\s*FILED AS OF DATE:\s*(\d{8})\s*$")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


seg = load_module("seg", ROOT / "scripts/research-nq-series-segmentation-2006.py")
corrected = load_module("corrected", ROOT / "scripts/research-nq-pit-holdings-2006-corrected.py")


def iso8(raw: str | None) -> str | None:
    if not raw or len(raw) != 8:
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def fetch_submission(filename: str) -> tuple[str, str, list[dict]]:
    sec_url = "https://www.sec.gov/Archives/" + filename.lstrip("/")
    attempts: list[dict] = []
    for url in (sec_url, "https://r.jina.ai/" + sec_url):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read(MAX_BYTES)
            attempts.append({"transport": url, "status": "SUCCESS", "bytesRead": len(payload)})
            encoding = "utf-8" if url.startswith("https://r.jina.ai/") else "latin-1"
            return payload.decode(encoding, "replace"), url, attempts
        except Exception as exc:
            attempts.append({"transport": url, "status": "ERROR", "error": type(exc).__name__})
    raise RuntimeError(json.dumps(attempts))


def source_key(row: dict) -> tuple[str, str]:
    return str(row["cik"]).zfill(10), row["accession"]


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    inventory = json.loads(INVENTORY.read_text())
    inv_by_key = {source_key(row): row for row in inventory["rows"]}

    requested: dict[tuple[str, str], dict] = {}
    for snap in catalog["monthSnapshots"]:
        for source in snap["sourceFilings"]:
            key = source_key(source)
            item = requested.setdefault(
                key,
                {
                    "cik": str(source["cik"]).zfill(10),
                    "accession": source["accession"],
                    "registrant": source["registrant"],
                    "series": {},
                    "months": set(),
                },
            )
            item["series"][source["seriesId"]] = source["seriesName"]
            item["months"].add(snap["signalMonth"])

    parsed: dict[tuple[str, str], dict[str, dict]] = {}
    filing_audit = []
    for i, key in enumerate(sorted(requested), 1):
        request = requested[key]
        inv = inv_by_key.get(key)
        if inv is None:
            filing_audit.append({**request, "months": sorted(request["months"]), "error": "INVENTORY_ROW_NOT_FOUND"})
            continue
        target_ids = set(request["series"])
        audit_row = {
            "cik": request["cik"],
            "accession": request["accession"],
            "registrant": request["registrant"],
            "filename": inv["filename"],
            "targetSeriesIds": sorted(target_ids),
            "months": sorted(request["months"]),
        }
        try:
            submission, transport, attempts = fetch_submission(inv["filename"])
            audit_row["transport"] = transport
            audit_row["transportAttempts"] = attempts
            report_m = REPORT_DATE.search(submission)
            filed_m = FILING_DATE.search(submission)
            audit_row["reportDate"] = iso8(report_m.group(1) if report_m else None)
            audit_row["headerFilingDate"] = iso8(filed_m.group(1) if filed_m else None)

            # Parse every filing-time registered series for boundary assignment. Do not use
            # the old registrant-name ETF heuristic; the strict catalog alone determines
            # which Series IDs may be retained.
            all_series = seg.meta.parse_series_contracts(submission, request["registrant"])
            all_by_id = {s.get("seriesId"): s for s in all_series if s.get("seriesId")}
            primary, text = seg.embedded_primary_nq(submission)
            grouped, assignment_audit = seg.grouped_schedule_blocks(text, all_series)
            audit_row["primaryDocument"] = primary
            audit_row["registeredSeriesCount"] = len(all_series)
            audit_row["scheduleMarkerCount"] = len(assignment_audit)
            audit_row["assignedScheduleMarkerCount"] = sum(bool(x.get("seriesId")) for x in assignment_audit)
            audit_row["unassignedScheduleMarkerCount"] = sum(not bool(x.get("seriesId")) for x in assignment_audit)
            audit_row["targetSeriesPresentInHeader"] = sorted(target_ids & set(all_by_id))
            audit_row["targetSeriesWithGroupedSchedule"] = sorted(target_ids & set(grouped))
            audit_row["assignmentAudit"] = assignment_audit

            by_series: dict[str, dict] = {}
            for sid in sorted(target_ids):
                s = all_by_id.get(sid)
                name = (s or {}).get("seriesName") or request["series"].get(sid) or ""
                blocks = grouped.get(sid, [])
                if not blocks:
                    by_series[sid] = {
                        "seriesId": sid,
                        "seriesName": name,
                        "accession": request["accession"],
                        "cik": request["cik"],
                        "registrant": request["registrant"],
                        "filingDate": inv["dateFiled"],
                        "reportDate": audit_row["reportDate"],
                        "sourceFilename": inv["filename"],
                        "primaryDocument": primary,
                        "schedulePages": 0,
                        "eligible": False,
                        "eligibilityReason": "NO_GROUPED_SCHEDULE",
                        "holdings": [],
                    }
                    continue

                method, holdings, total = corrected.parsed_holdings("\n".join(blocks))
                count = len(holdings)
                top10 = sum(h.get("weight", 0.0) for h in holdings[:10]) if holdings else 0.0
                name_ok = seg.eligible_name(name)
                eligible = bool(name_ok and 10 <= count <= 120 and total > 0 and top10 >= 25.0)
                reasons = []
                if not name_ok:
                    reasons.append("NAME_EXCLUSION")
                if count < 10:
                    reasons.append("HOLDING_COUNT_LT_10")
                if count > 120:
                    reasons.append("HOLDING_COUNT_GT_120")
                if total <= 0:
                    reasons.append("NONPOSITIVE_PARSED_VALUE")
                if top10 < 25.0:
                    reasons.append("TOP10_LT_25")
                by_series[sid] = {
                    "seriesId": sid,
                    "seriesName": name,
                    "accession": request["accession"],
                    "cik": request["cik"],
                    "registrant": request["registrant"],
                    "filingDate": inv["dateFiled"],
                    "reportDate": audit_row["reportDate"],
                    "sourceFilename": inv["filename"],
                    "primaryDocument": primary,
                    "assignmentRule": "EXPLICIT_SERIES_BOUNDARY_GROUP_ALL_REGISTERED_SERIES",
                    "schedulePages": len(blocks),
                    "parseMethod": method,
                    "parsedHoldingCount": count,
                    "parsedMarketValueTotal": total,
                    "top10Weight": top10,
                    "eligibleByName": name_ok,
                    "eligible": eligible,
                    "eligibilityReason": "ELIGIBLE" if eligible else "+".join(reasons),
                    "holdings": holdings,
                }
            parsed[key] = by_series
            audit_row["parsedTargetSeriesCount"] = len(by_series)
            audit_row["eligibleTargetSeriesCount"] = sum(bool(x["eligible"]) for x in by_series.values())
            print(
                "FILING",
                json.dumps(
                    {
                        "index": i,
                        "total": len(requested),
                        "accession": request["accession"],
                        "targets": len(target_ids),
                        "groupedTargets": len(target_ids & set(grouped)),
                        "eligibleTargets": audit_row["eligibleTargetSeriesCount"],
                    }
                ),
                flush=True,
            )
        except Exception as exc:
            audit_row["error"] = type(exc).__name__
            audit_row["errorDetail"] = str(exc)[:1200]
            print("FILING_ERROR", json.dumps({"accession": request["accession"], "error": type(exc).__name__}), flush=True)
        filing_audit.append(audit_row)
        time.sleep(0.08)

    snapshots = []
    for snap in catalog["monthSnapshots"]:
        all_records = []
        eligible_records = []
        missing = []
        for source in snap["sourceFilings"]:
            key = source_key(source)
            record = parsed.get(key, {}).get(source["seriesId"])
            if record is None:
                missing.append({"seriesId": source["seriesId"], "accession": source["accession"]})
                continue
            all_records.append(record)
            if record["eligible"]:
                eligible_records.append(record)
        snapshots.append(
            {
                "signalMonth": snap["signalMonth"],
                "asOf": snap["asOf"],
                "catalogSourceSeriesCount": snap["sourceSeriesCount"],
                "parsedSourceSeriesCount": len(all_records),
                "eligibleSourceSeriesCount": len(eligible_records),
                "missingParsedSeries": missing,
                "sourceFilings": all_records,
                "eligibleSourceFilings": eligible_records,
            }
        )
        print(
            "MONTH",
            json.dumps(
                {
                    "signalMonth": snap["signalMonth"],
                    "catalog": snap["sourceSeriesCount"],
                    "parsed": len(all_records),
                    "eligible": len(eligible_records),
                    "missing": len(missing),
                }
            ),
            flush=True,
        )

    out = {
        "purpose": (
            "Catalog-driven H1 2006 N-Q holdings extraction. Source selection comes exclusively from the "
            "strict historical ETF Series-ID PIT catalog. Every filing-time registered series is used only "
            "for explicit schedule-boundary assignment; only catalog-positive Series IDs are retained. "
            "For each monthly snapshot the catalog has already selected the latest N-Q/N-Q-A public by the "
            "month end, after which Production-style source-filing eligibility is applied. No known "
            "registrant regex, holdings-based source discovery, ranks, returns, or strategy outcomes are used."
        ),
        "sourceCatalogRunId": 33898993220,
        "sourceInventoryArtifactId": 9946255797,
        "uniqueSourceFilingCount": len(requested),
        "filingFetchSuccessCount": sum("error" not in x for x in filing_audit),
        "filingFetchErrorCount": sum("error" in x for x in filing_audit),
        "assignmentRule": "Exact filing-time registered series title around each schedule marker; all registered series participate in boundary assignment, but only strict-catalog Series IDs are retained.",
        "eligibilityRule": "After latest public filing selection per Series ID: Production name exclusions, 10-120 positive parsed holdings, positive parsed market value, normalized top-10 weight >=25%. Weights remain parser-relative until later EC/identity validation.",
        "filingAudit": filing_audit,
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(
        "SUMMARY",
        json.dumps(
            {
                "uniqueSourceFilingCount": out["uniqueSourceFilingCount"],
                "filingFetchSuccessCount": out["filingFetchSuccessCount"],
                "filingFetchErrorCount": out["filingFetchErrorCount"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
