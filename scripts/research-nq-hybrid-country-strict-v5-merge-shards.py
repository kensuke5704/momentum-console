#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
MAPPING = R / "nq-hybrid-structural-mapping-h1-2006.json"
SHARDS = R / "country-shards"
OUT = R / "nq-hybrid-country-resolved-h1-2006.json"

spec = importlib.util.spec_from_file_location(
    "strict_country_base",
    ROOT / "scripts/research-nq-hybrid-country-strict-v5-h1-2006.py",
)
strict = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(strict)


def main() -> None:
    mapping = json.loads(MAPPING.read_text())
    shard_files = sorted(SHARDS.glob("country-resolution-shard-*.json"))
    if not shard_files:
        raise SystemExit("no country shard files")
    audits = []
    expected_total = None
    shard_count = None
    shard_indexes = set()
    for path in shard_files:
        data = json.loads(path.read_text())
        if expected_total is None:
            expected_total = int(data["unresolvedTotalCount"])
            shard_count = int(data["shardCount"])
        if int(data["unresolvedTotalCount"]) != expected_total or int(data["shardCount"]) != shard_count:
            raise RuntimeError("country shard metadata mismatch")
        shard_indexes.add(int(data["shardIndex"]))
        audits.extend(data["resolutionAudit"])
    if shard_indexes != set(range(shard_count or 0)):
        raise RuntimeError(f"missing country shards: got={sorted(shard_indexes)} expected={list(range(shard_count or 0))}")

    resolved = {}
    for row in audits:
        key = strict.identity_key(row.get("ticker"), row.get("securityId"))
        ukey = (key[0], key[1], row.get("asOfReportDate"))
        if ukey in resolved:
            raise RuntimeError(f"duplicate resolved country key {ukey}")
        resolved[ukey] = row
    if len(resolved) != expected_total:
        raise RuntimeError(f"resolved key coverage mismatch: {len(resolved)} != {expected_total}")

    reason_counts = Counter()
    snapshots = []
    consumed = set()
    for snapshot in mapping["monthSnapshots"]:
        month_counts = Counter()
        month_weights = defaultdict(float)
        filings = []
        for filing in snapshot["sourceFilings"]:
            report_date = filing.get("reportDate")
            fcounts = Counter()
            fweights = defaultdict(float)
            holdings = []
            for holding in filing.get("holdings", []):
                row = dict(holding)
                classification = "UNKNOWN"
                reason = "UNRESOLVED"
                if row.get("mappingStatus") == "MATCHED_UNIQUE":
                    explicit = row.get("legacyCountryClassification")
                    if explicit in {"US", "NON_US"}:
                        classification = explicit
                        reason = "NQ_EXPLICIT_COUNTRY_SECTION"
                    elif strict.non_us_cins(row.get("mappedSecurityId")):
                        classification = "NON_US"
                        reason = "NON_US_CINS"
                    elif strict.RECEIPT.search(str(row.get("description") or "")):
                        classification = "NON_US"
                        reason = "EXPLICIT_DEPOSITARY_RECEIPT"
                    else:
                        key = strict.identity_key(row.get("mappedTicker"), row.get("mappedSecurityId"))
                        ukey = (key[0], key[1], report_date)
                        evidence = resolved.get(ukey)
                        if evidence is None:
                            raise RuntimeError(f"missing strict country shard result {ukey}")
                        consumed.add(ukey)
                        if evidence.get("classification") in {"US", "NON_US"}:
                            classification = evidence["classification"]
                            reason = "PIT_SUBMISSION_HEADER_EXACT_HISTORICAL_NAME"
                            row["countryResolutionEvidence"] = evidence
                row["countryClassification"] = classification
                row["countryReason"] = reason
                reason_counts[reason] += 1
                weight = float(row.get("weight") or 0.0)
                fcounts[classification] += 1
                fweights[classification] += weight
                month_counts[classification] += 1
                month_weights[classification] += weight
                holdings.append(row)
            filings.append({
                **{k:v for k,v in filing.items() if k not in {"holdings","countryClassificationCounts","countryClassificationWeights"}},
                "countryClassificationCounts": dict(fcounts),
                "countryClassificationWeights": dict(fweights),
                "holdings": holdings,
            })
        snapshots.append({
            **{k:v for k,v in snapshot.items() if k != "sourceFilings"},
            "countryClassificationCounts": dict(month_counts),
            "countryClassificationWeights": dict(month_weights),
            "sourceFilings": filings,
        })
    if consumed != set(resolved):
        extras = sorted(set(resolved) - consumed)[:20]
        raise RuntimeError(f"country shard results not consumed exactly: extra={extras}")

    output = {
        "purpose": (
            "Strict PIT H1 2006 country classification merged from deterministic parallel shards. Evidence order "
            "and acceptance rules are identical to the single-run strict resolver. Previously accepted historical "
            "SEC submission evidence is reused only when its exact historical evidence query is eligible; all other "
            "queries are freshly resolved. Current ticker fallback, US default, modern state/country, fuzzy matching, "
            "ranks, returns and strategy outcomes are forbidden."
        ),
        "countryEvidenceRule": (
            "NQ_EXPLICIT -> NON_US_CINS/EXPLICIT_RECEIPT -> HISTORICAL_EXACT_ISSUER_FORM_UNIQUE_CIK -> "
            "PIT_SEC_HEADER_STATE -> UNKNOWN"
        ),
        "currentTickerFallbackAllowed": False,
        "currentTickerFallbackCount": 0,
        "masterYears": [2005, 2006],
        "masterIndexTransports": {},
        "unresolvedInputCount": len(resolved),
        "resolvedUSCount": sum(x.get("classification") == "US" for x in audits),
        "resolvedNonUSCount": sum(x.get("classification") == "NON_US" for x in audits),
        "remainingUnknownCount": sum(x.get("classification") == "UNKNOWN" for x in audits),
        "reasonCounts": dict(reason_counts),
        "resolutionAudit": sorted(audits, key=lambda x: (x.get("ticker") or "", x.get("securityId") or "", x.get("asOfReportDate") or "")),
        "monthSnapshots": snapshots,
        "parallelShardAudit": {
            "shardCount": shard_count,
            "resolvedKeyCount": len(resolved),
            "exactCoverage": len(resolved) == expected_total,
        },
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("STRICT_COUNTRY_MERGE_SUMMARY", json.dumps({
        "unresolvedInputCount": output["unresolvedInputCount"],
        "resolvedUSCount": output["resolvedUSCount"],
        "resolvedNonUSCount": output["resolvedNonUSCount"],
        "remainingUnknownCount": output["remainingUnknownCount"],
        "shardCount": shard_count,
    }), flush=True)
    for snapshot in snapshots:
        print("MONTH_COUNTRY", json.dumps({
            "signalMonth": snapshot["signalMonth"],
            "counts": snapshot["countryClassificationCounts"],
            "weights": snapshot["countryClassificationWeights"],
        }), flush=True)


if __name__ == "__main__":
    main()
