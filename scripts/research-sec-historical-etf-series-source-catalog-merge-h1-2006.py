#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"
SHARD_COUNT = int(os.environ.get("SHARD_COUNT", "8"))
OUT = DATA / "sec-historical-etf-series-source-catalog-complete-h1-2006.json"
MONTHS = [
    ("2006-01", "2006-01-31"),
    ("2006-02", "2006-02-28"),
    ("2006-03", "2006-03-31"),
    ("2006-04", "2006-04-28"),
    ("2006-05", "2006-05-31"),
    ("2006-06", "2006-06-30"),
]


def main() -> None:
    paths = sorted(DATA.glob("sec-historical-etf-series-source-catalog-h1-2006-shard-*.json"))
    if len(paths) != SHARD_COUNT:
        raise ValueError(f"expected {SHARD_COUNT} shard files, found {len(paths)}")
    shards = [json.loads(path.read_text()) for path in paths]
    indices = sorted(row["shardIndex"] for row in shards)
    if indices != list(range(SHARD_COUNT)):
        raise ValueError(f"unexpected shard indices: {indices}")
    if any(row["shardCount"] != SHARD_COUNT for row in shards):
        raise ValueError("shardCount mismatch")
    candidate_counts = {row["candidateRegistrantCount"] for row in shards}
    if len(candidate_counts) != 1:
        raise ValueError(f"candidate registrant count mismatch: {candidate_counts}")
    selected_ciks = [cik for row in shards for cik in row["selectedCiks"]]
    if len(selected_ciks) != len(set(selected_ciks)):
        raise ValueError("duplicate candidate CIK across shards")
    candidate_count = candidate_counts.pop()
    if len(selected_ciks) != candidate_count:
        raise ValueError(f"candidate CIK coverage mismatch: {len(selected_ciks)} != {candidate_count}")

    evidence = []
    for row in shards:
        evidence.extend(row["positiveSeries"])
    first = {}
    for row in sorted(evidence, key=lambda x: (x["evidenceDateFiled"], x["seriesId"], x["evidenceFilename"])):
        if row["seriesId"] not in first:
            first[row["seriesId"]] = row
    positive_series = sorted(first.values(), key=lambda x: x["seriesId"])

    nq = {}
    for shard in shards:
        for row in shard["nqPositiveSeriesFilings"]:
            nq[(row["seriesId"], row["accession"])] = row
    nq_rows = list(nq.values())
    positive_ids = set(first)
    # A shard only emits N-Q rows for Series IDs with positive evidence in the same CIK.
    # Retain only globally accepted positive IDs as an additional merge guard.
    nq_rows = [row for row in nq_rows if row["seriesId"] in positive_ids]

    snapshots = []
    for month, asof in MONTHS:
        latest = {}
        for row in nq_rows:
            evidence_row = first.get(row["seriesId"])
            if not evidence_row:
                continue
            if evidence_row["evidenceDateFiled"] > asof or row["dateFiled"] > asof:
                continue
            current = latest.get(row["seriesId"])
            if current is None or (row["dateFiled"], row["accession"]) > (current["dateFiled"], current["accession"]):
                latest[row["seriesId"]] = row
        source = sorted(latest.values(), key=lambda x: (x["seriesId"], x["dateFiled"], x["accession"]))
        snapshots.append({
            "signalMonth": month,
            "asOf": asof,
            "sourceSeriesCount": len(source),
            "sourceFilings": [
                {
                    "seriesId": row["seriesId"],
                    "seriesName": row["seriesName"],
                    "accession": row["accession"],
                    "cik": row["cik"],
                    "registrant": row["company"],
                    "filingDate": row["dateFiled"],
                    "evidenceDateFiled": first[row["seriesId"]]["evidenceDateFiled"],
                    "evidenceForm": first[row["seriesId"]]["evidenceForm"],
                    "evidenceFilename": first[row["seriesId"]]["evidenceFilename"],
                    "binding": first[row["seriesId"]]["binding"],
                }
                for row in source
            ],
        })

    prospectus_diagnostics = [x for shard in shards for x in shard["prospectusDiagnostics"]]
    nq_diagnostics = [x for shard in shards for x in shard["nqDiagnostics"]]
    out = {
        "purpose": (
            "Source-complete sharded H1 2006 historical ETF Series-ID PIT catalog. Candidate registrants "
            "come only from the market-wide H1 operational prefilter. Every core 485/N-1A filing through "
            "2006-06-30 plus the latest 497 supplement in each filing month is inspected. Positive Series IDs "
            "require the validated issuer-own Creation Unit plus exchange-listing/trading conjunction and "
            "structural filing-index binding. Monthly source snapshots use only evidence and N-Q/N-Q-A filings "
            "public by month end, selecting the latest public N-Q filing per Series ID. No known source list, "
            "holdings outcomes, ranks, returns, or strategy results are used for selection."
        ),
        "inventoryArtifactId": 9946255797,
        "prefilterSourceRunId": 33897558123,
        "candidateRegistrantCount": candidate_count,
        "positiveRegistrantCount": len({row["cik"] for row in positive_series}),
        "positiveSeriesCount": len(positive_series),
        "positiveSeries": positive_series,
        "prospectusInspectedCount": sum(row["prospectusInspectedCount"] for row in shards),
        "prospectusErrorCount": sum(row["prospectusErrorCount"] for row in shards),
        "prospectusEvidenceRecordCount": sum(row["prospectusEvidenceRecordCount"] for row in shards),
        "nqPositiveSeriesFilingCount": len(nq_rows),
        "nqIndexErrorCount": sum(row["nqIndexErrorCount"] for row in shards),
        "monthSnapshots": snapshots,
        "prospectusDiagnostics": prospectus_diagnostics,
        "nqDiagnostics": nq_diagnostics,
        "shardSummaries": [
            {k: row[k] for k in (
                "shardIndex", "selectedRegistrantCount", "prospectusInspectedCount",
                "prospectusErrorCount", "positiveSeriesCount", "nqPositiveSeriesFilingCount", "nqIndexErrorCount"
            )}
            for row in shards
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({
        "candidateRegistrantCount": out["candidateRegistrantCount"],
        "positiveRegistrantCount": out["positiveRegistrantCount"],
        "positiveSeriesCount": out["positiveSeriesCount"],
        "prospectusInspectedCount": out["prospectusInspectedCount"],
        "prospectusErrorCount": out["prospectusErrorCount"],
        "nqPositiveSeriesFilingCount": out["nqPositiveSeriesFilingCount"],
        "nqIndexErrorCount": out["nqIndexErrorCount"],
    }), flush=True)
    for snap in snapshots:
        print("MONTH", json.dumps({k: snap[k] for k in ("signalMonth", "asOf", "sourceSeriesCount")}), flush=True)


if __name__ == "__main__":
    main()
