#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter
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

    evidence = [item for shard in shards for item in shard["positiveSeries"]]
    first = {}
    for row in sorted(evidence, key=lambda x: (x["evidenceDateFiled"], x["seriesId"], x["evidenceFilename"])):
        if row["seriesId"] not in first:
            first[row["seriesId"]] = row
    positive_series = sorted(first.values(), key=lambda x: x["seriesId"])

    nq = {}
    for shard in shards:
        for row in shard["nqPositiveSeriesFilings"]:
            nq[(row["seriesId"], row["accession"])] = row
    nq_rows = [row for row in nq.values() if row["seriesId"] in first]

    snapshots = []
    for month, asof in MONTHS:
        latest = {}
        for row in nq_rows:
            evidence_row = first.get(row["seriesId"])
            if not evidence_row:
                continue
            # Two independent PIT gates are required. The Series must already have strict
            # operational+identity evidence, and the N-Q itself must already be public.
            # Q4 2005 rows receive no special preference; they can win only by being the
            # latest public N-Q for that Series at the same mechanical month-end cutoff.
            if evidence_row["evidenceDateFiled"] > asof or row["dateFiled"] > asof:
                continue
            current = latest.get(row["seriesId"])
            if current is None or (row["dateFiled"], row["accession"]) > (current["dateFiled"], current["accession"]):
                latest[row["seriesId"]] = row
        source = sorted(latest.values(), key=lambda x: (x["seriesId"], x["dateFiled"], x["accession"]))
        period_counts = Counter(row.get("inventoryPeriod", "UNKNOWN") for row in source)
        snapshots.append({
            "signalMonth": month,
            "asOf": asof,
            "sourceSeriesCount": len(source),
            "pre2006SourceSeriesCount": period_counts.get("2005Q4", 0),
            "sourceFilingPeriodCounts": dict(period_counts),
            "sourceFilings": [
                {
                    "seriesId": row["seriesId"],
                    "seriesName": row["seriesName"],
                    "accession": row["accession"],
                    "cik": row["cik"],
                    "registrant": row["company"],
                    "filingDate": row["dateFiled"],
                    "inventoryPeriod": row.get("inventoryPeriod", "UNKNOWN"),
                    "evidenceDateFiled": first[row["seriesId"]]["evidenceDateFiled"],
                    "operationalEvidenceDateFiled": first[row["seriesId"]].get("operationalEvidenceDateFiled"),
                    "seriesMetadataDateFiled": first[row["seriesId"]].get("seriesMetadataDateFiled"),
                    "seriesMetadataInventoryPeriod": first[row["seriesId"]].get("seriesMetadataInventoryPeriod"),
                    "evidenceForm": first[row["seriesId"]]["evidenceForm"],
                    "evidenceFilename": first[row["seriesId"]]["evidenceFilename"],
                    "binding": first[row["seriesId"]]["binding"],
                }
                for row in source
            ],
        })

    prospectus_diagnostics = [x for shard in shards for x in shard["prospectusDiagnostics"]]
    nq_diagnostics = [x for shard in shards for x in shard["nqDiagnostics"]]
    binding_counts = Counter(row["binding"] for row in positive_series)
    pre2006_positive_accessions = {
        row["accession"] for row in nq_rows if row.get("inventoryPeriod") == "2005Q4"
    }
    out = {
        "purpose": (
            "Source-complete sharded H1 2006 historical ETF Series-ID PIT catalog with a Q4 2005 N-Q "
            "lookback. Candidate registrants come only from the market-wide H1 operational prefilter. Strict "
            "ETF Series IDs require validated issuer-own Creation Unit plus exchange-listing/trading evidence. "
            "Q4 2005 N-Q metadata may bridge missing old prospectus Series/Class identity, with the PIT binding "
            "date set to the later public filing. Monthly snapshots then independently select the latest N-Q "
            "public by each month end from Q4 2005 plus H1 2006, requiring the strict Series evidence to also be "
            "public by that cutoff. Loading a lookback filing therefore never automatically makes it a source. "
            "No known source list, holdings outcomes, ranks, returns, or strategy results are used."
        ),
        "source": "SEC_COMPLETE_SUBMISSION_STRICT_SERIES_PIT_CATALOG_V2_Q4_LOOKBACK",
        "inventoryArtifactId": 9946255797,
        "lookbackInventorySource": "SEC_MASTER_Q4_2005_NQ_LOOKBACK_V1",
        "prefilterSourceRunId": 33897558123,
        "candidateRegistrantCount": candidate_count,
        "positiveRegistrantCount": len({row["cik"] for row in positive_series}),
        "positiveSeriesCount": len(positive_series),
        "bindingCounts": dict(binding_counts),
        "positiveSeries": positive_series,
        "sourceNqFilingCount": sum(row.get("sourceNqFilingCount", 0) for row in shards),
        "identityNqFilingCount": sum(row.get("identityNqFilingCount", 0) for row in shards),
        "pre2006IdentityNqFilingCount": sum(row.get("pre2006IdentityNqFilingCount", 0) for row in shards),
        "parsedIdentityNqFilingCount": sum(row.get("parsedIdentityNqFilingCount", 0) for row in shards),
        "parsedPre2006IdentityNqFilingCount": sum(row.get("parsedPre2006IdentityNqFilingCount", 0) for row in shards),
        "pre2006IdentitySeriesRowCount": sum(row.get("pre2006IdentitySeriesRowCount", 0) for row in shards),
        "pre2006PositiveSourceNqFilingCount": len(pre2006_positive_accessions),
        "pre2006PositiveSourceNqSeriesRowCount": sum(
            row.get("inventoryPeriod") == "2005Q4" for row in nq_rows
        ),
        "prospectusInspectedCount": sum(row["prospectusInspectedCount"] for row in shards),
        "prospectusErrorCount": sum(row["prospectusErrorCount"] for row in shards),
        "prospectusDirectEvidenceRecordCount": sum(row["prospectusDirectEvidenceRecordCount"] for row in shards),
        "issuerOwnOperationalFilingCount": sum(row["issuerOwnOperationalFilingCount"] for row in shards),
        "nqFallbackPositiveSeriesCount": sum(row["nqFallbackPositiveSeriesCount"] for row in shards),
        "nqPositiveSeriesFilingCount": len(nq_rows),
        "nqIndexErrorCount": sum(row["nqIndexErrorCount"] for row in shards),
        "januarySourceSeriesCount": snapshots[0]["sourceSeriesCount"],
        "monthSnapshots": snapshots,
        "prospectusDiagnostics": prospectus_diagnostics,
        "nqDiagnostics": nq_diagnostics,
        "shardSummaries": [
            {k: row.get(k) for k in (
                "shardIndex", "selectedRegistrantCount", "sourceNqFilingCount", "identityNqFilingCount",
                "pre2006IdentityNqFilingCount", "parsedPre2006IdentityNqFilingCount",
                "pre2006IdentitySeriesRowCount", "prospectusInspectedCount", "prospectusErrorCount",
                "issuerOwnOperationalFilingCount", "positiveSeriesCount", "nqFallbackPositiveSeriesCount",
                "nqPositiveSeriesFilingCount", "pre2006PositiveSourceNqFilingCount", "nqIndexErrorCount"
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
        "bindingCounts": out["bindingCounts"],
        "pre2006IdentityNqFilingCount": out["pre2006IdentityNqFilingCount"],
        "pre2006IdentitySeriesRowCount": out["pre2006IdentitySeriesRowCount"],
        "pre2006PositiveSourceNqFilingCount": out["pre2006PositiveSourceNqFilingCount"],
        "prospectusInspectedCount": out["prospectusInspectedCount"],
        "prospectusErrorCount": out["prospectusErrorCount"],
        "issuerOwnOperationalFilingCount": out["issuerOwnOperationalFilingCount"],
        "nqFallbackPositiveSeriesCount": out["nqFallbackPositiveSeriesCount"],
        "nqPositiveSeriesFilingCount": out["nqPositiveSeriesFilingCount"],
        "nqIndexErrorCount": out["nqIndexErrorCount"],
        "januarySourceSeriesCount": out["januarySourceSeriesCount"],
    }), flush=True)
    for snap in snapshots:
        print("MONTH", json.dumps({
            k: snap[k] for k in (
                "signalMonth", "asOf", "sourceSeriesCount", "pre2006SourceSeriesCount",
                "sourceFilingPeriodCounts"
            )
        }), flush=True)


if __name__ == "__main__":
    main()
