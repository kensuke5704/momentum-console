#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTRY = ROOT / "data/research/nq-hybrid-country-resolved-h1-2006.json"
RECOVERY_GLOB = str(ROOT / "data/research/country-recovery/country-filing-index-recovery-v29-shard-*.json")
OUT = COUNTRY


def key_from_audit(row: dict):
    return ((row.get("ticker") or "").strip().upper(), row.get("securityId") or None, row.get("asOfReportDate") or None)


def key_from_holding(row: dict, report_date: str | None):
    return ((row.get("mappedTicker") or "").strip().upper(), row.get("mappedSecurityId") or None, report_date)


def main() -> None:
    data = json.loads(COUNTRY.read_text())
    files = sorted(glob.glob(RECOVERY_GLOB))
    if len(files) != 8:
        raise RuntimeError(f"Expected exactly 8 recovery shard files, found {len(files)}")

    original_audit = data.get("resolutionAudit", [])
    original_unknown = {key_from_audit(r) for r in original_audit if r.get("classification") == "UNKNOWN"}
    original_non_unknown = {key_from_audit(r): r.get("classification") for r in original_audit if r.get("classification") in {"US", "NON_US"}}

    promoted = {}
    shard_audit = []
    seen_recovery_keys = set()
    for path in files:
        shard = json.loads(Path(path).read_text())
        shard_audit.append({
            "path": Path(path).name,
            "shardIndex": shard.get("shardIndex"),
            "shardInputUnknownCount": shard.get("shardInputUnknownCount"),
            "resolvedUSCount": shard.get("resolvedUSCount", 0),
            "resolvedNonUSCount": shard.get("resolvedNonUSCount", 0),
            "remainingUnknownCount": shard.get("remainingUnknownCount", 0),
            "fetchErrorCount": shard.get("fetchErrorCount", 0),
        })
        for row in shard.get("results", []):
            k = key_from_audit(row)
            if k in seen_recovery_keys:
                raise RuntimeError(f"Duplicate recovery key across shards: {k}")
            seen_recovery_keys.add(k)
            if k not in original_unknown:
                raise RuntimeError(f"Recovery key was not an original UNKNOWN: {k}")
            cls = row.get("classification")
            if cls in {"US", "NON_US"}:
                promoted[k] = row

    if len(seen_recovery_keys) != len(original_unknown):
        missing = sorted(original_unknown - seen_recovery_keys)[:10]
        extra = sorted(seen_recovery_keys - original_unknown)[:10]
        raise RuntimeError(
            f"Recovery exact-key coverage mismatch: originalUnknown={len(original_unknown)} "
            f"recoveryKeys={len(seen_recovery_keys)} missing={missing} extra={extra}"
        )

    # Promote only original UNKNOWN resolution-audit rows. Existing US/NON_US evidence is immutable.
    updated_audit = []
    for row in original_audit:
        k = key_from_audit(row)
        if k in promoted:
            p = promoted[k]
            if row.get("classification") != "UNKNOWN":
                raise RuntimeError(f"Attempt to overwrite non-UNKNOWN audit row: {k}")
            nr = dict(row)
            nr.update({
                "classification": p["classification"],
                "stateCode": p.get("stateCode"),
                "resolutionSource": p.get("resolutionSource"),
                "historicalEntityName": p.get("historicalEntityName"),
                "evidenceForm": p.get("evidenceForm"),
                "evidenceDateFiled": p.get("evidenceDateFiled"),
                "evidenceIndexUrl": p.get("evidenceIndexUrl"),
                "evidenceTransport": p.get("evidenceTransport"),
                "recoveryEvidence": p,
            })
            updated_audit.append(nr)
        else:
            updated_audit.append(row)

    snapshots = []
    promoted_holding_count = 0
    promoted_holding_weight = 0.0
    for snapshot in data.get("monthSnapshots", []):
        month_counts = Counter()
        month_weights = defaultdict(float)
        filings = []
        for filing in snapshot.get("sourceFilings", []):
            report_date = filing.get("reportDate")
            fcounts = Counter()
            fweights = defaultdict(float)
            holdings = []
            for holding in filing.get("holdings", []):
                row = dict(holding)
                k = key_from_holding(row, report_date)
                if row.get("countryClassification") == "UNKNOWN" and k in promoted:
                    p = promoted[k]
                    row["countryClassification"] = p["classification"]
                    row["countryReason"] = "PIT_FILING_INDEX_ENTITY_STATE"
                    row["countryResolutionEvidence"] = p
                    promoted_holding_count += 1
                    promoted_holding_weight += float(row.get("weight") or 0.0)
                cls = row.get("countryClassification") or "UNKNOWN"
                w = float(row.get("weight") or 0.0)
                fcounts[cls] += 1
                fweights[cls] += w
                month_counts[cls] += 1
                month_weights[cls] += w
                holdings.append(row)
            nf = dict(filing)
            nf["holdings"] = holdings
            nf["countryClassificationCounts"] = dict(fcounts)
            nf["countryClassificationWeights"] = dict(fweights)
            filings.append(nf)
        ns = dict(snapshot)
        ns["sourceFilings"] = filings
        ns["countryClassificationCounts"] = dict(month_counts)
        ns["countryClassificationWeights"] = dict(month_weights)
        snapshots.append(ns)

    classes = Counter(r.get("classification", "UNKNOWN") for r in updated_audit)
    output = dict(data)
    output["resolutionAudit"] = updated_audit
    output["monthSnapshots"] = snapshots
    output["resolvedUSCount"] = classes["US"]
    output["resolvedNonUSCount"] = classes["NON_US"]
    output["remainingUnknownCount"] = classes["UNKNOWN"]
    output["countryEvidenceRule"] = (
        str(data.get("countryEvidenceRule") or "")
        + " -> PIT_FILING_INDEX_ENTITY_STATE (original UNKNOWN only; exact historical CIK/name/accession evidence)"
    )
    output["filingIndexRecoveryAudit"] = {
        "recoveryShardCount": len(files),
        "originalUnknownKeyCount": len(original_unknown),
        "recoveryExactKeyCount": len(seen_recovery_keys),
        "promotedIdentityDateCount": len(promoted),
        "promotedUSIdentityDateCount": sum(x.get("classification") == "US" for x in promoted.values()),
        "promotedNonUSIdentityDateCount": sum(x.get("classification") == "NON_US" for x in promoted.values()),
        "promotedHoldingCount": promoted_holding_count,
        "promotedHoldingWeight": promoted_holding_weight,
        "currentTickerFallbackAllowed": False,
        "shards": shard_audit,
    }
    # Existing non-UNKNOWN classifications must remain exactly unchanged.
    for row in updated_audit:
        k = key_from_audit(row)
        if k in original_non_unknown and row.get("classification") != original_non_unknown[k]:
            raise RuntimeError(f"Existing classification changed: {k}")

    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print("COUNTRY_RECOVERY_MERGE", json.dumps(output["filingIndexRecoveryAudit"]), flush=True)
    print("COUNTRY_RECOVERY_COUNTS", json.dumps({
        "US": output["resolvedUSCount"],
        "NON_US": output["resolvedNonUSCount"],
        "UNKNOWN": output["remainingUnknownCount"],
    }), flush=True)


if __name__ == "__main__":
    main()
