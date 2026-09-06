#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = Path(os.environ.get("STRICT_COUNTRY_ACCEPTED_EVIDENCE", ROOT / "data/research/accepted-country-evidence.json"))

spec = importlib.util.spec_from_file_location(
    "strict_country_resolution_cache",
    ROOT / "scripts/research-nq-hybrid-country-strict-v5-indexed-resolution-cache.py",
)
wrapped = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wrapped)
strict = wrapped.strict
base_resolve = wrapped.cached_exact_historical_resolve

accepted: dict[tuple[tuple[str, ...], str | None], dict] = {}
rejected_rows = 0
if OLD.exists():
    old = json.loads(OLD.read_text())
    for row in old.get("resolutionAudit", []):
        cls = row.get("classification")
        ev = row.get("resolutionEvidence") or {}
        if cls not in {"US", "NON_US"}:
            continue
        if ev.get("seedSource") != "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME":
            rejected_rows += 1
            continue
        if ev.get("resolutionSource") != "PIT_SUBMISSION_FLAT_HEADER_ENTITY_STATE":
            rejected_rows += 1
            continue
        if not ev.get("seedCik") or not ev.get("stateCode") or not ev.get("evidenceDateFiled"):
            rejected_rows += 1
            continue
        key = (
            tuple(str(x) for x in row.get("issuerVariants", [])),
            row.get("asOfReportDate"),
        )
        evidence = {
            "classification": cls,
            "stateCode": ev.get("stateCode"),
            "resolutionSource": ev.get("resolutionSource"),
            "seedSource": ev.get("seedSource"),
            "seedCik": ev.get("seedCik"),
            "issuerForm": row.get("countryIdentityFormUsed") or ev.get("issuer"),
            "evidenceForm": ev.get("evidenceForm"),
            "evidenceDateFiled": ev.get("evidenceDateFiled"),
            "acceptanceDate": ev.get("acceptanceDate"),
            "submissionUrl": ev.get("submissionUrl"),
            "historicalEntityName": ev.get("historicalEntityName"),
            "attempts": row.get("attempts", []),
            "acceptedEvidenceReuse": True,
        }
        previous = accepted.get(key)
        if previous and previous.get("classification") != cls:
            raise RuntimeError(f"accepted historical evidence conflict for {key}: {previous.get('classification')} vs {cls}")
        accepted[key] = evidence

reuse_count = 0
fresh_count = 0


def seeded_resolve(row: dict, master_rows: list[dict]) -> dict:
    global reuse_count, fresh_count
    key = (tuple(str(x) for x in row.get("issuerVariants", [])), row.get("asOfReportDate"))
    hit = accepted.get(key)
    if hit:
        reuse_count += 1
        return {**row, **hit}
    fresh_count += 1
    return base_resolve(row, master_rows)


strict.exact_historical_resolve = seeded_resolve

if __name__ == "__main__":
    strict.main()
    print(
        "STRICT_COUNTRY_ACCEPTED_EVIDENCE_CACHE_SUMMARY",
        json.dumps({
            "acceptedEvidenceFile": str(OLD),
            "acceptedResolvedQueryCount": len(accepted),
            "rejectedEvidenceRows": rejected_rows,
            "reusedResolutionCount": reuse_count,
            "freshResolutionCount": fresh_count,
            "freshResolutionCacheSize": len(wrapped._resolution_cache),
            "submissionCacheSize": len(wrapped.indexed._submission_cache),
        }),
        flush=True,
    )
