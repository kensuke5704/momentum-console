#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"
H1 = DATA / "nq-pit-holdings-hybrid-h1-2006.json"
H2 = DATA / "nq-pit-holdings-series-id-h2-2006.json"
OUT = DATA / "nq-holdings-parser-invariance-h1-h2-2006.json"

H1_ARTIFACT_ID = 10006530879
H2_ARTIFACT_ID = 10038557328
EXPECTED_OVERLAP_COUNT = 120


def filing_key(row: dict) -> tuple[str, str, str]:
    return (
        row.get("seriesId") or row.get("canonicalIdentity") or "",
        row.get("accession") or "",
        row.get("sourceFilename") or "",
    )


def unique_series_id_records(payload: dict) -> dict[tuple[str, str, str], dict]:
    out: dict[tuple[str, str, str], dict] = {}
    for snapshot in payload.get("monthSnapshots", []):
        for row in snapshot.get("sourceFilings", []):
            if row.get("identityRegime") != "SERIES_ID":
                continue
            key = filing_key(row)
            if not all(key):
                raise RuntimeError(f"incomplete Series-ID filing key: {key}")
            previous = out.get(key)
            if previous is not None and previous != row:
                raise RuntimeError(f"same filing key has non-identical repeated record: {key}")
            out[key] = row
    return out


def parser_semantic_view(row: dict) -> dict:
    # H1 hybrid rows may carry a pre-ID bridge label while the H2 strict Series-ID
    # adapter intentionally sets legacyIdentity=None. That field is source-catalog
    # lineage metadata, not parser output. Every other record field must be exact.
    return {key: value for key, value in row.items() if key != "legacyIdentity"}


def main() -> None:
    h1 = json.loads(H1.read_text())
    h2 = json.loads(H2.read_text())
    left = unique_series_id_records(h1)
    right = unique_series_id_records(h2)
    overlap = sorted(set(left) & set(right))

    semantic_mismatches = []
    legacy_identity_differences = []
    exact_full_record_matches = 0
    for key in overlap:
        lrow = left[key]
        rrow = right[key]
        if lrow == rrow:
            exact_full_record_matches += 1
        elif lrow.get("legacyIdentity") != rrow.get("legacyIdentity"):
            legacy_identity_differences.append({
                "seriesId": key[0],
                "accession": key[1],
                "sourceFilename": key[2],
                "h1LegacyIdentity": lrow.get("legacyIdentity"),
                "h2LegacyIdentity": rrow.get("legacyIdentity"),
            })

        lsemantic = parser_semantic_view(lrow)
        rsemantic = parser_semantic_view(rrow)
        if lsemantic != rsemantic:
            differing_fields = sorted(
                field
                for field in set(lsemantic) | set(rsemantic)
                if lsemantic.get(field) != rsemantic.get(field)
            )
            semantic_mismatches.append({
                "seriesId": key[0],
                "accession": key[1],
                "sourceFilename": key[2],
                "differingFields": differing_fields,
            })

    report = {
        "purpose": (
            "Explicit parser-invariance audit for the authoritative H1 raw holdings artifact and the validated H2 raw holdings artifact. "
            "For identical Series-ID + accession + SEC source-file keys, every parser-derived and filing-derived record field must be byte-value equivalent after excluding only legacyIdentity, which is H1 hybrid bridge metadata deliberately absent from the H2 strict Series-ID adapter."
        ),
        "h1ArtifactId": H1_ARTIFACT_ID,
        "h2ArtifactId": H2_ARTIFACT_ID,
        "h1UniqueSeriesIdFilingRecordCount": len(left),
        "h2UniqueSeriesIdFilingRecordCount": len(right),
        "overlapCount": len(overlap),
        "expectedOverlapCount": EXPECTED_OVERLAP_COUNT,
        "exactFullRecordMatchCount": exact_full_record_matches,
        "legacyIdentityOnlyDifferenceCount": len(legacy_identity_differences),
        "semanticMismatchCount": len(semantic_mismatches),
        "legacyIdentityOnlyDifferences": legacy_identity_differences,
        "semanticMismatches": semantic_mismatches,
        "passed": len(overlap) == EXPECTED_OVERLAP_COUNT and not semantic_mismatches,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("PARSER_INVARIANCE", json.dumps({
        key: report[key]
        for key in (
            "h1UniqueSeriesIdFilingRecordCount",
            "h2UniqueSeriesIdFilingRecordCount",
            "overlapCount",
            "exactFullRecordMatchCount",
            "legacyIdentityOnlyDifferenceCount",
            "semanticMismatchCount",
            "passed",
        )
    }), flush=True)

    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
