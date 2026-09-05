#!/usr/bin/env python3
from __future__ import annotations

import html
import importlib.util
import json
import os
import re
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path(os.environ.get(
    "CATALOG_PATH",
    str(ROOT / "data/research/sec-hybrid-etf-source-catalog-h1-2006.json"),
))
OUT = ROOT / "data/research/nq-pit-holdings-hybrid-h1-2006.json"
SOURCE_CATALOG_RUN_ID = os.environ.get("SOURCE_CATALOG_RUN_ID")
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}
MAX_BYTES = 25_000_000
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
ec = load_module("ec", ROOT / "scripts/research-nq-per-holding-ec-2006.py")
legacy = load_module("legacy", ROOT / "scripts/research-sec-legacy-etf-series-source-h2-2005.py")
h2diag = legacy.h2diag


def norm(raw: str | None) -> str:
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", html.unescape(raw or "").upper()).split())


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


def source_key(row: dict) -> tuple[str, str, str]:
    return str(row["cik"]).zfill(10), row.get("accession") or "", row["filename"]


def identity_key(row: dict) -> str:
    return row["canonicalIdentity"]


def annotate_sections(holdings: list[dict], combined: str) -> tuple[list[dict], dict, dict]:
    vis = seg.visible(combined)
    counts = Counter()
    weights = defaultdict(float)
    out = []
    for holding in holdings:
        section, alias = ec.locate_section(vis, holding["description"])
        row = {**holding, "legacyAssetSection": section}
        if alias:
            row["matchedSourceAlias"] = alias
        counts[section] += 1
        weights[section] += float(holding.get("weight") or 0.0)
        out.append(row)
    return out, dict(counts), dict(weights)


def parse_blocks(blocks: list[str], base_record: dict) -> dict:
    if not blocks:
        return {
            **base_record,
            "schedulePages": 0,
            "parseStatus": "NO_GROUPED_SCHEDULE",
            "holdings": [],
        }
    combined = "\n".join(blocks)
    method, holdings, total = corrected.parsed_holdings(combined)
    holdings, section_count, section_weight = annotate_sections(holdings, combined)
    top10 = sum(h.get("weight", 0.0) for h in holdings[:10]) if holdings else 0.0
    return {
        **base_record,
        "schedulePages": len(blocks),
        "parseMethod": method,
        "parseStatus": "PARSED" if holdings else "PARSED_ZERO_HOLDINGS",
        "parsedHoldingCount": len(holdings),
        "parsedMarketValueTotal": total,
        "rawTop10WeightDiagnostic": top10,
        "legacyAssetSectionCount": section_count,
        "legacyAssetSectionWeight": section_weight,
        "holdings": holdings,
    }


def legacy_grouped_schedule_blocks(primary_text: str, targets: dict[str, dict]) -> tuple[dict[str, list[str]], list[dict]]:
    """Assign historical pre-ID schedules without inventing a Series ID.

    A target can start only when its exact normalized catalog name is present among
    the same deterministic nearby title candidates used by the pre-ID source
    resolver. Marker pages with no meaningful title continue the preceding target;
    a marker carrying a different meaningful title closes that continuation. This
    uses no holdings content to determine identity.
    """
    visible = h2diag.line_text(primary_text)
    markers = list(h2diag.SCHEDULE.finditer(visible))
    target_by_norm = {row["normalizedSeriesName"]: iid for iid, row in targets.items()}
    grouped: dict[str, list[str]] = defaultdict(list)
    audit: list[dict] = []
    carry: str | None = None

    for idx, marker in enumerate(markers):
        next_start = markers[idx + 1].start() if idx + 1 < len(markers) else len(visible)
        before = visible[max(0, marker.start() - 1800):marker.start()].splitlines()[-18:]
        after = visible[marker.end():min(len(visible), marker.end() + 1800)].splitlines()[:18]
        window = {
            "markerIndex": idx,
            "marker": marker.group(0),
            "beforeLines": before,
            "afterLines": after,
        }
        candidates = legacy.title_candidates(window)
        exact = sorted({target_by_norm[c["normalizedTitle"]] for c in candidates if c["normalizedTitle"] in target_by_norm})
        meaningful_titles = sorted({c["normalizedTitle"] for c in candidates})

        rule = "UNASSIGNED"
        assigned: str | None = None
        if len(exact) == 1:
            carry = exact[0]
            assigned = carry
            rule = "EXACT_NORMALIZED_TITLE_AT_MARKER"
        elif len(exact) > 1:
            carry = None
            rule = "AMBIGUOUS_EXACT_TARGETS"
        elif meaningful_titles:
            carry = None
            rule = "DIFFERENT_MEANINGFUL_TITLE_BOUNDARY"
        elif carry:
            assigned = carry
            rule = "UNTITLED_CONTINUATION_OF_EXACT_TARGET"

        if assigned:
            start = max(0, marker.start() - 1600) if rule == "EXACT_NORMALIZED_TITLE_AT_MARKER" else marker.start()
            grouped[assigned].append(visible[start:next_start])

        audit.append({
            "markerIndex": idx,
            "marker": marker.group(0),
            "candidateTitles": meaningful_titles,
            "exactTargetIdentities": exact,
            "assignedIdentity": assigned,
            "assignmentRule": rule,
        })

    return dict(grouped), audit


def main() -> None:
    catalog = json.loads(CATALOG.read_text())

    requested: dict[tuple[str, str, str], dict] = {}
    for snap in catalog["monthSnapshots"]:
        for source in snap["sourceFilings"]:
            key = source_key(source)
            item = requested.setdefault(
                key,
                {
                    "cik": str(source["cik"]).zfill(10),
                    "accession": source.get("accession"),
                    "filename": source["filename"],
                    "registrant": source["registrant"],
                    "form": source["form"],
                    "filingDate": source["filingDate"],
                    "targets": {},
                    "months": set(),
                },
            )
            iid = identity_key(source)
            item["targets"][iid] = source
            item["months"].add(snap["signalMonth"])

    parsed: dict[tuple[str, str, str], dict[str, dict]] = {}
    filing_audit: list[dict] = []

    for i, key in enumerate(sorted(requested), 1):
        request = requested[key]
        target_rows = request["targets"]
        audit_row = {
            "cik": request["cik"],
            "accession": request["accession"],
            "filename": request["filename"],
            "registrant": request["registrant"],
            "form": request["form"],
            "filingDate": request["filingDate"],
            "targetIdentities": sorted(target_rows),
            "months": sorted(request["months"]),
        }
        try:
            submission, transport, attempts = fetch_submission(request["filename"])
            audit_row["transport"] = transport
            audit_row["transportAttempts"] = attempts
            report_m = REPORT_DATE.search(submission)
            filed_m = FILING_DATE.search(submission)
            audit_row["reportDate"] = iso8(report_m.group(1) if report_m else None)
            audit_row["headerFilingDate"] = iso8(filed_m.group(1) if filed_m else None)

            primary, description, primary_text, doc_type = h2diag.primary_document(submission, request["form"])
            audit_row["primaryDocument"] = primary
            audit_row["primaryDocumentType"] = doc_type
            audit_row["documentDescription"] = description

            legacy_targets = {iid: row for iid, row in target_rows.items() if row["identityRegime"] == "LEGACY_PRE_ID"}
            series_targets = {iid: row for iid, row in target_rows.items() if row["identityRegime"] == "SERIES_ID"}
            by_identity: dict[str, dict] = {}

            if series_targets:
                all_series = seg.meta.parse_series_contracts(submission, request["registrant"])
                all_by_id = {s.get("seriesId"): s for s in all_series if s.get("seriesId")}
                grouped, assignment_audit = seg.grouped_schedule_blocks(primary_text, all_series)
                audit_row["registeredSeriesCount"] = len(all_series)
                audit_row["seriesIdAssignmentAudit"] = assignment_audit
                audit_row["seriesIdScheduleMarkerCount"] = len(assignment_audit)
                for iid, source in sorted(series_targets.items()):
                    sid = source["seriesId"]
                    s = all_by_id.get(sid)
                    base_record = {
                        "canonicalIdentity": iid,
                        "identityRegime": "SERIES_ID",
                        "legacyIdentity": source.get("legacyIdentity"),
                        "seriesId": sid,
                        "seriesName": (s or {}).get("seriesName") or source["seriesName"],
                        "normalizedSeriesName": source["normalizedSeriesName"],
                        "accession": request["accession"],
                        "cik": request["cik"],
                        "registrant": request["registrant"],
                        "form": request["form"],
                        "filingDate": request["filingDate"],
                        "reportDate": audit_row["reportDate"],
                        "sourceFilename": request["filename"],
                        "primaryDocument": primary,
                        "assignmentRule": "EXPLICIT_SERIES_ID_BOUNDARY_GROUP_ALL_REGISTERED_SERIES",
                    }
                    by_identity[iid] = parse_blocks(grouped.get(sid, []), base_record)

            if legacy_targets:
                legacy_grouped, legacy_audit = legacy_grouped_schedule_blocks(primary_text, legacy_targets)
                audit_row["legacyAssignmentAudit"] = legacy_audit
                audit_row["legacyScheduleMarkerCount"] = len(legacy_audit)
                audit_row["legacyExactAssignedMarkerCount"] = sum(
                    x["assignmentRule"] == "EXACT_NORMALIZED_TITLE_AT_MARKER" for x in legacy_audit
                )
                audit_row["legacyContinuationAssignedMarkerCount"] = sum(
                    x["assignmentRule"] == "UNTITLED_CONTINUATION_OF_EXACT_TARGET" for x in legacy_audit
                )
                audit_row["legacyAmbiguousMarkerCount"] = sum(
                    x["assignmentRule"] == "AMBIGUOUS_EXACT_TARGETS" for x in legacy_audit
                )
                for iid, source in sorted(legacy_targets.items()):
                    base_record = {
                        "canonicalIdentity": iid,
                        "identityRegime": "LEGACY_PRE_ID",
                        "legacyIdentity": source["legacyIdentity"],
                        "seriesId": source.get("seriesId"),
                        "seriesName": source["seriesName"],
                        "normalizedSeriesName": source["normalizedSeriesName"],
                        "accession": request["accession"],
                        "cik": request["cik"],
                        "registrant": request["registrant"],
                        "form": request["form"],
                        "filingDate": request["filingDate"],
                        "reportDate": audit_row["reportDate"],
                        "sourceFilename": request["filename"],
                        "primaryDocument": primary,
                        "assignmentRule": "EXACT_NORMALIZED_PRE_ID_TITLE_WITH_UNTITLED_CONTINUATION_ONLY",
                    }
                    by_identity[iid] = parse_blocks(legacy_grouped.get(iid, []), base_record)

            parsed[key] = by_identity
            audit_row["parsedTargetCount"] = sum(x.get("parseStatus") == "PARSED" for x in by_identity.values())
            audit_row["zeroHoldingTargetCount"] = sum(x.get("parseStatus") == "PARSED_ZERO_HOLDINGS" for x in by_identity.values())
            audit_row["noGroupedScheduleTargetCount"] = sum(x.get("parseStatus") == "NO_GROUPED_SCHEDULE" for x in by_identity.values())
            print("FILING", json.dumps({
                "index": i,
                "total": len(requested),
                "accession": request["accession"],
                "form": request["form"],
                "legacyTargets": len(legacy_targets),
                "seriesIdTargets": len(series_targets),
                "parsedTargets": audit_row["parsedTargetCount"],
                "noGrouped": audit_row["noGroupedScheduleTargetCount"],
            }), flush=True)
        except Exception as exc:
            audit_row["error"] = type(exc).__name__
            audit_row["errorDetail"] = str(exc)[:1400]
            print("FILING_ERROR", json.dumps({
                "accession": request["accession"], "error": type(exc).__name__
            }), flush=True)
        filing_audit.append(audit_row)
        time.sleep(0.08)

    snapshots = []
    for snap in catalog["monthSnapshots"]:
        records = []
        missing = []
        for source in snap["sourceFilings"]:
            key = source_key(source)
            iid = identity_key(source)
            record = parsed.get(key, {}).get(iid)
            if record is None:
                missing.append({
                    "canonicalIdentity": iid,
                    "identityRegime": source["identityRegime"],
                    "seriesId": source.get("seriesId"),
                    "legacyIdentity": source.get("legacyIdentity"),
                    "accession": source.get("accession"),
                })
                continue
            records.append(record)
        snapshots.append({
            "signalMonth": snap["signalMonth"],
            "asOf": snap["asOf"],
            "catalogSourceSeriesCount": snap["sourceSeriesCount"],
            "catalogLegacySourceCount": snap.get("legacySourceCount"),
            "catalogSeriesIdSourceCount": snap.get("seriesIdSourceCount"),
            "parsedSourceSeriesCount": sum(x.get("parseStatus") == "PARSED" for x in records),
            "parsedLegacySourceCount": sum(x.get("parseStatus") == "PARSED" and x["identityRegime"] == "LEGACY_PRE_ID" for x in records),
            "parsedSeriesIdSourceCount": sum(x.get("parseStatus") == "PARSED" and x["identityRegime"] == "SERIES_ID" for x in records),
            "missingParsedSeries": missing,
            "sourceFilings": records,
        })
        print("MONTH", json.dumps({
            "signalMonth": snap["signalMonth"],
            "catalog": snap["sourceSeriesCount"],
            "records": len(records),
            "parsed": sum(x.get("parseStatus") == "PARSED" for x in records),
            "legacyParsed": sum(x.get("parseStatus") == "PARSED" and x["identityRegime"] == "LEGACY_PRE_ID" for x in records),
            "seriesIdParsed": sum(x.get("parseStatus") == "PARSED" and x["identityRegime"] == "SERIES_ID" for x in records),
            "missing": len(missing),
        }), flush=True)

    all_unique_records = [row for values in parsed.values() for row in values.values()]
    all_holdings = [h for row in all_unique_records for h in row.get("holdings", [])]
    section_counts = Counter(h.get("legacyAssetSection", "UNKNOWN") for h in all_holdings)
    section_weights = defaultdict(float)
    for h in all_holdings:
        section_weights[h.get("legacyAssetSection", "UNKNOWN")] += float(h.get("weight") or 0.0)

    out = {
        "purpose": (
            "Hybrid-catalog-driven H1 2006 raw complete-portfolio holdings extraction. Source filings are taken "
            "exclusively from the frozen hybrid PIT ETF source catalog. Post-ID rows use explicit SEC Series IDs. "
            "Pre-ID rows use only the exact normalized historical Series/Fund title already accepted by the "
            "independent source catalog, plus untitled continuation markers until another meaningful title boundary. "
            "Holdings content never determines source identity. No known registrant list, ticker, fuzzy matching, "
            "rank, return, or strategy outcome is used."
        ),
        "sourceCatalogPath": str(CATALOG.relative_to(ROOT)) if CATALOG.is_relative_to(ROOT) else str(CATALOG),
        "sourceCatalogRunId": int(SOURCE_CATALOG_RUN_ID) if SOURCE_CATALOG_RUN_ID else None,
        "uniqueSourceFilingCount": len(requested),
        "legacyRequestedIdentityCount": sum(
            row["identityRegime"] == "LEGACY_PRE_ID"
            for req in requested.values() for row in req["targets"].values()
        ),
        "seriesIdRequestedIdentityCount": sum(
            row["identityRegime"] == "SERIES_ID"
            for req in requested.values() for row in req["targets"].values()
        ),
        "filingFetchSuccessCount": sum("error" not in x for x in filing_audit),
        "filingFetchErrorCount": sum("error" in x for x in filing_audit),
        "legacyAssignmentRule": (
            "Exact normalized pre-ID catalog title among deterministic schedule-marker title candidates; "
            "untitled markers may continue the immediately preceding exact target, while any different meaningful "
            "title closes continuation. Ambiguous exact targets are never assigned."
        ),
        "seriesIdAssignmentRule": (
            "All filing-time registered Series IDs participate in explicit schedule-boundary grouping; "
            "only hybrid-catalog target Series IDs are retained."
        ),
        "legacyAssetSectionRule": (
            "Each already-parsed holding inherits only the nearest preceding explicit COMMON/PREFERRED/SHORT-TERM/DEBT "
            "heading in its assigned schedule; otherwise UNKNOWN. No holding is filtered at this raw stage."
        ),
        "uniqueParsedHoldingCount": len(all_holdings),
        "legacyAssetSectionCounts": dict(section_counts),
        "legacyAssetSectionWeights": dict(section_weights),
        "eligibilityStatus": (
            "DEFERRED. Historical source ETF structural eligibility is applied only after COMMON_EQUITY and "
            "conservative issuer-country mapping, matching Production ordering as closely as the legacy forms permit."
        ),
        "filingAudit": filing_audit,
        "monthSnapshots": snapshots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "uniqueSourceFilingCount": out["uniqueSourceFilingCount"],
        "legacyRequestedIdentityCount": out["legacyRequestedIdentityCount"],
        "seriesIdRequestedIdentityCount": out["seriesIdRequestedIdentityCount"],
        "filingFetchSuccessCount": out["filingFetchSuccessCount"],
        "filingFetchErrorCount": out["filingFetchErrorCount"],
        "uniqueParsedHoldingCount": out["uniqueParsedHoldingCount"],
        "legacyAssetSectionCounts": out["legacyAssetSectionCounts"],
    }), flush=True)


if __name__ == "__main__":
    main()
