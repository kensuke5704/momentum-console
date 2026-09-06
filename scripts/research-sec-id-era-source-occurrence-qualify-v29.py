#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get(
    "POST_ID_CATALOG_PATH",
    str(ROOT / "data/research/sec-id-era-strict-series-source-h1-2006.json"),
))
OUT = ROOT / "data/research/sec-id-era-strict-series-source-h1-2006-v29qualified.json"
MONTHS = [
    ("2006-02", "2006-02-28"),
    ("2006-03", "2006-03-31"),
    ("2006-04", "2006-04-28"),
    ("2006-05", "2006-05-31"),
    ("2006-06", "2006-06-30"),
]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


seg = load("seg", ROOT / "scripts/research-nq-series-segmentation-2006.py")
h2diag = load("h2diag", ROOT / "scripts/research-sec-complete-portfolio-title-diagnostic-h2-2005.py")


def filing_key(row: dict) -> tuple[str, str, str]:
    return (str(row.get("cik") or "").zfill(10), row.get("accession") or "", row["filename"])


def main() -> None:
    source = json.loads(SRC.read_text())
    positives = {row["seriesId"]: row for row in source["positiveSeries"]}

    by_filing: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in source["sourceOccurrences"]:
        by_filing[filing_key(row)].append(row)

    qualified = []
    filing_audit = []
    assignment_rule_counts = Counter()

    for index, key in enumerate(sorted(by_filing), 1):
        rows = by_filing[key]
        first = rows[0]
        audit = {
            "cik": str(first.get("cik") or "").zfill(10),
            "accession": first.get("accession"),
            "filename": first.get("filename"),
            "company": first.get("company"),
            "form": first.get("form"),
            "dateFiled": first.get("dateFiled"),
            "candidateSeriesIds": sorted({row["seriesId"] for row in rows}),
        }
        try:
            submission, transport = h2diag.fetch(first["filename"])
            primary, description, primary_text, primary_type = h2diag.primary_document(submission, first["form"])
            all_series = seg.meta.parse_series_contracts(submission, first["company"])
            grouped, assignment_audit = seg.grouped_schedule_blocks(primary_text, all_series)
            for entry in assignment_audit:
                assignment_rule_counts[entry.get("assignmentRule") or "UNKNOWN"] += 1

            grouped_ids = sorted(series_id for series_id, blocks in grouped.items() if blocks)
            candidate_ids = set(audit["candidateSeriesIds"])
            qualified_ids = sorted(candidate_ids & set(grouped_ids))
            missing_ids = sorted(candidate_ids - set(grouped_ids))

            audit.update({
                "transport": transport,
                "primaryDocument": primary,
                "primaryDocumentType": primary_type,
                "documentDescription": description,
                "registeredSeriesCount": len(all_series),
                "scheduleMarkerCount": len(assignment_audit),
                "assignedScheduleMarkerCount": sum(bool(row.get("seriesId")) for row in assignment_audit),
                "unassignedScheduleMarkerCount": sum(not row.get("seriesId") for row in assignment_audit),
                "groupedSeriesIds": grouped_ids,
                "qualifiedSeriesIds": qualified_ids,
                "missingSeriesIds": missing_ids,
                "assignmentAudit": assignment_audit,
            })

            for row in rows:
                if row["seriesId"] in qualified_ids:
                    qualified.append(row)

            print("FILING", json.dumps({
                "index": index,
                "total": len(by_filing),
                "accession": first.get("accession"),
                "form": first.get("form"),
                "candidateSeries": len(candidate_ids),
                "qualifiedSeries": len(qualified_ids),
                "missingSeries": len(missing_ids),
            }), flush=True)
        except Exception as exc:
            audit.update({
                "error": type(exc).__name__,
                "errorDetail": str(exc)[:1400],
                "qualifiedSeriesIds": [],
                "missingSeriesIds": audit["candidateSeriesIds"],
            })
            print("FILING_ERROR", json.dumps({
                "index": index,
                "total": len(by_filing),
                "accession": first.get("accession"),
                "error": type(exc).__name__,
            }), flush=True)
        filing_audit.append(audit)

    dedup = {}
    for row in qualified:
        dedup[(row["seriesId"], row.get("accession") or "", row["filename"])] = row
    occurrences = sorted(dedup.values(), key=lambda row: (
        row["seriesId"], row["dateFiled"], row.get("accession") or "", row["filename"]
    ))

    snapshots = []
    for month, as_of in MONTHS:
        latest = {}
        for row in occurrences:
            evidence = positives.get(row["seriesId"])
            if not evidence:
                continue
            if evidence["evidenceDateFiled"] > as_of or row["dateFiled"] > as_of:
                continue
            current = latest.get(row["seriesId"])
            if current is None or (row["dateFiled"], row.get("accession") or "") > (
                current["dateFiled"], current.get("accession") or ""
            ):
                latest[row["seriesId"]] = row

        selected = sorted(latest.values(), key=lambda row: (
            row["seriesId"], row["dateFiled"], row.get("accession") or ""
        ))
        snapshots.append({
            "signalMonth": month,
            "asOf": as_of,
            "sourceSeriesCount": len(selected),
            "sourceFilings": [{
                "seriesId": row["seriesId"],
                "seriesName": row["seriesName"],
                "cik": row["cik"],
                "registrant": row["company"],
                "form": row["form"],
                "filingDate": row["dateFiled"],
                "accession": row.get("accession"),
                "filename": row["filename"],
                "evidenceDateFiled": positives[row["seriesId"]]["evidenceDateFiled"],
                "binding": positives[row["seriesId"]]["binding"],
            } for row in selected],
        })

    form_counts = Counter(row["form"] for row in occurrences)
    candidate_pairs = {(row["seriesId"], row.get("accession") or "") for row in source["sourceOccurrences"]}
    qualified_pairs = {(row["seriesId"], row.get("accession") or "") for row in occurrences}
    removed_pairs = sorted(candidate_pairs - qualified_pairs)

    output = {
        **{
            key: value for key, value in source.items()
            if key not in {"sourceOccurrences", "monthSnapshots", "sourceOccurrenceCount", "sourceFormCounts"}
        },
        "purpose": (
            "Post-ID v2.9 source-occurrence qualification. Positive ETF Series identities are preserved, but a "
            "complete-portfolio filing is eligible to replace a prior holdings source for a Series only when the "
            "same filing's primary document has at least one schedule block deterministically assigned to that exact "
            "Series ID using filing-time Series names. Filing-wide schedule presence is insufficient. This enforces "
            "the frozen rule that an amendment without a complete portfolio schedule for the Series does not replace "
            "the underlying holdings source. No holdings outcomes, ranks, returns, fuzzy names, or later identity "
            "backfill are used."
        ),
        "sourceOccurrenceQualificationRule": (
            "Exact Series-ID schedule grouping in the same primary filing document; unassigned or other-Series "
            "schedule markers do not qualify the occurrence."
        ),
        "preQualificationSourceOccurrenceCount": len(source["sourceOccurrences"]),
        "sourceOccurrenceCount": len(occurrences),
        "removedSourceOccurrenceCount": len(removed_pairs),
        "removedSeriesAccessionPairs": [
            {"seriesId": series_id, "accession": accession}
            for series_id, accession in removed_pairs
        ],
        "sourceFormCounts": dict(sorted(form_counts.items())),
        "scheduleAssignmentRuleCounts": dict(sorted(assignment_rule_counts.items())),
        "sourceQualificationFetchErrorCount": sum("error" in row for row in filing_audit),
        "sourceOccurrences": occurrences,
        "monthSnapshots": snapshots,
        "sourceOccurrenceQualificationAudit": filing_audit,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "positiveSeriesCount": output.get("positiveSeriesCount"),
        "preQualificationSourceOccurrenceCount": output["preQualificationSourceOccurrenceCount"],
        "sourceOccurrenceCount": output["sourceOccurrenceCount"],
        "removedSourceOccurrenceCount": output["removedSourceOccurrenceCount"],
        "sourceQualificationFetchErrorCount": output["sourceQualificationFetchErrorCount"],
        "sourceFormCounts": output["sourceFormCounts"],
        "scheduleAssignmentRuleCounts": output["scheduleAssignmentRuleCounts"],
    }), flush=True)
    for snapshot in snapshots:
        print("MONTH", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "sourceSeriesCount": snapshot["sourceSeriesCount"],
        }), flush=True)


if __name__ == "__main__":
    main()
