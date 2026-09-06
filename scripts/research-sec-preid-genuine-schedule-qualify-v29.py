#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get(
    "PREID_CATALOG_PATH",
    str(ROOT / "data/research/sec-legacy-etf-series-source-preid-v29canonical-2006.json"),
))
OUT = ROOT / "data/research/sec-legacy-etf-series-source-preid-v29genuine-2006.json"
MONTHS = [("2006-01", "2006-01-31"), ("2006-02", "2006-02-28")]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


hybrid = load("hybrid", ROOT / "scripts/research-nq-pit-holdings-hybrid-h1-2006.py")
grouping = load("grouping", ROOT / "scripts/research-nq-hybrid-grouping-v29.py")


def filing_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("cik") or "").zfill(10),
        row.get("sourceAccession") or "",
        row.get("sourceFilename") or "",
    )


def main() -> None:
    source = json.loads(SRC.read_text())
    occurrences = source["sourceOccurrences"]
    by_filing: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        by_filing[filing_key(row)].append(row)

    qualified_keys: set[tuple[tuple[str, str, str], str]] = set()
    audit = []
    fetch_errors = 0

    for idx, (key, rows) in enumerate(sorted(by_filing.items()), 1):
        first = rows[0]
        record = {
            "cik": key[0],
            "accession": key[1],
            "filename": key[2],
            "form": first.get("sourceForm"),
            "filingDate": first.get("sourceFilingDate"),
            "registrant": first.get("registrant"),
            "candidateNormalizedSeriesNames": sorted({r["normalizedSeriesName"] for r in rows}),
        }
        try:
            submission, transport, attempts = hybrid.fetch_submission(key[2])
            primary, description, text, doc_type = hybrid.h2diag.primary_document(submission, first["sourceForm"])
            targets = {
                normalized: {"normalizedSeriesName": normalized}
                for normalized in record["candidateNormalizedSeriesNames"]
            }
            grouped, assignment_audit = grouping.legacy_grouped_schedule_blocks(text, targets)
            qualified_names = sorted(name for name, blocks in grouped.items() if blocks)
            for name in qualified_names:
                qualified_keys.add((key, name))
            record.update({
                "transport": transport,
                "transportAttempts": attempts,
                "primaryDocument": primary,
                "primaryDocumentType": doc_type,
                "documentDescription": description,
                "genuineScheduleMarkerCount": len(assignment_audit),
                "qualifiedNormalizedSeriesNames": qualified_names,
                "rejectedNormalizedSeriesNames": sorted(set(record["candidateNormalizedSeriesNames"]) - set(qualified_names)),
                "ambiguousAssignedMarkerCount": sum(
                    1 for x in assignment_audit
                    if x.get("assignmentRule") == "AMBIGUOUS_EXACT_TARGETS" and x.get("assignedIdentity") is not None
                ),
            })
        except Exception as exc:
            fetch_errors += 1
            record["error"] = type(exc).__name__
            record["errorDetail"] = str(exc)[:1200]
        audit.append(record)
        print("FILING", json.dumps({
            "index": idx,
            "total": len(by_filing),
            "accession": key[1],
            "candidates": len(rows),
            "qualified": len(record.get("qualifiedNormalizedSeriesNames", [])),
            "rejected": len(record.get("rejectedNormalizedSeriesNames", [])),
            "error": record.get("error"),
        }), flush=True)
        time.sleep(0.04)

    qualified_occurrences = [
        row for row in occurrences
        if (filing_key(row), row["normalizedSeriesName"]) in qualified_keys
    ]
    qualified_identity_ids = {row["legacyIdentity"] for row in qualified_occurrences}

    by_identity_occ: dict[str, list[dict]] = defaultdict(list)
    for row in qualified_occurrences:
        by_identity_occ[row["legacyIdentity"]].append(row)

    positive = []
    for identity in source["positiveIdentities"]:
        lid = identity["legacyIdentity"]
        if lid not in qualified_identity_ids:
            continue
        rows = sorted(
            by_identity_occ[lid],
            key=lambda r: (r["sourceFilingDate"], r.get("sourceAccession") or ""),
        )
        chosen = rows[-1]
        updated = dict(identity)
        for src_key, dst_key in [
            ("sourceAccession", "sourceAccession"),
            ("sourceFilingDate", "sourceFilingDate"),
            ("sourceForm", "sourceForm"),
            ("sourceFilename", "sourceFilename"),
        ]:
            updated[dst_key] = chosen.get(src_key)
        positive.append(updated)

    snapshots = []
    for month, asof in MONTHS:
        latest = {}
        for row in qualified_occurrences:
            if row["sourceFilingDate"] > asof or row["evidenceDateFiled"] > asof:
                continue
            lid = row["legacyIdentity"]
            cur = latest.get(lid)
            if cur is None or (row["sourceFilingDate"], row.get("sourceAccession") or "") > (
                cur["sourceFilingDate"], cur.get("sourceAccession") or ""
            ):
                latest[lid] = row
        rows = sorted(latest.values(), key=lambda r: (r["cik"], r["legacyIdentity"]))
        snapshots.append({
            "signalMonth": month,
            "asOf": asof,
            "sourceSeriesCount": len(rows),
            "sourceFilings": rows,
        })

    rejected_occ = [row for row in occurrences if row not in qualified_occurrences]
    rejected_identity_ids = sorted({row["legacyIdentity"] for row in source["positiveIdentities"] if row["legacyIdentity"] not in qualified_identity_ids})

    out = {
        **{k: v for k, v in source.items() if k not in {
            "positiveIdentityCount", "sourceOccurrenceCount", "positiveIdentities", "sourceOccurrences",
            "monthSnapshots", "sourceAudit"
        }},
        "purpose": (
            "Pre-Series-ID ETF source catalog requalified on genuine complete-holdings headings only. "
            "References such as 'Notes to the Schedule of Investments' are not schedule boundaries. "
            "Each retained occurrence requires the same exact normalized contemporaneous fund title at a genuine "
            "schedule marker. No holdings names, ticker inference, future Series IDs, fuzzy matching, ranks, returns "
            "or strategy outcomes are used."
        ),
        "genuineScheduleQualificationRule": "EXACT_NORMALIZED_PRE_ID_TITLE_AT_NON_NOTES_COMPLETE_HOLDINGS_MARKER",
        "preQualificationPositiveIdentityCount": source["positiveIdentityCount"],
        "preQualificationSourceOccurrenceCount": source["sourceOccurrenceCount"],
        "positiveIdentityCount": len(positive),
        "sourceOccurrenceCount": len(qualified_occurrences),
        "genuineRejectedOccurrenceCount": len(rejected_occ),
        "genuineRejectedIdentityCount": len(rejected_identity_ids),
        "genuineRejectedIdentityIds": rejected_identity_ids,
        "genuineScheduleFetchErrorCount": fetch_errors,
        "positiveIdentities": positive,
        "sourceOccurrences": qualified_occurrences,
        "monthSnapshots": snapshots,
        "genuineScheduleAudit": audit,
        "sourceAudit": source.get("sourceAudit", []),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "prePositiveIdentityCount": source["positiveIdentityCount"],
        "positiveIdentityCount": len(positive),
        "preSourceOccurrenceCount": source["sourceOccurrenceCount"],
        "sourceOccurrenceCount": len(qualified_occurrences),
        "rejectedOccurrenceCount": len(rejected_occ),
        "rejectedIdentityCount": len(rejected_identity_ids),
        "rejectedIdentityIds": rejected_identity_ids,
        "fetchErrorCount": fetch_errors,
        "monthCounts": {s["signalMonth"]: s["sourceSeriesCount"] for s in snapshots},
    }), flush=True)
    if fetch_errors:
        raise SystemExit(f"pre-ID genuine schedule qualification had fetch errors: {fetch_errors}")
    if any(row.get("ambiguousAssignedMarkerCount") for row in audit):
        raise SystemExit("ambiguous pre-ID marker was assigned")


if __name__ == "__main__":
    main()
