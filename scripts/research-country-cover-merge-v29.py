#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
COUNTRY = R / "nq-hybrid-country-resolved-h1-2006.json"
RECOVERY_DIR = R / "country-cover-recovery"
OUT = R / "nq-hybrid-country-resolved-h1-2006.json"


def identity_key(ticker, security_id, report_date):
    return ((ticker or "").strip().upper(), security_id or None, report_date or None)


def main() -> None:
    country = json.loads(COUNTRY.read_text())
    files = sorted(RECOVERY_DIR.glob("country-filing-cover-recovery-v29-shard-*.json"))
    if len(files) != 8:
        raise RuntimeError(f"Expected 8 filing-cover recovery shards, found {len(files)}")

    recovered: dict[tuple, dict] = {}
    all_recovery_keys = set()
    input_count = 0
    resolved_count = 0
    for path in files:
        data = json.loads(path.read_text())
        input_count += int(data.get("inputCount") or 0)
        for row in data.get("results", []):
            key = identity_key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
            if key in all_recovery_keys:
                raise RuntimeError(f"Duplicate recovery key across shards: {key}")
            all_recovery_keys.add(key)
            cls = row.get("classification")
            if cls not in {"US", "NON_US"}:
                continue
            if row.get("resolutionSource") != "PIT_FILING_PRIMARY_DOCUMENT_COVER_JURISDICTION":
                raise RuntimeError(f"Unexpected recovery source for {key}: {row.get('resolutionSource')}")
            if not row.get("historicalExactCik") or not row.get("evidenceFilename") or not row.get("evidenceDocumentUrl"):
                raise RuntimeError(f"Incomplete filing-cover evidence for {key}")
            if key in recovered and recovered[key].get("classification") != cls:
                raise RuntimeError(f"Conflicting filing-cover country evidence for {key}")
            recovered[key] = row
            resolved_count += 1

    audit_rows = country.get("resolutionAudit", [])
    strict_keys = {
        identity_key(r.get("ticker"), r.get("securityId"), r.get("asOfReportDate"))
        for r in audit_rows
    }
    unknown_keys_before = {
        identity_key(r.get("ticker"), r.get("securityId"), r.get("asOfReportDate"))
        for r in audit_rows if r.get("classification") == "UNKNOWN"
    }
    extra = set(recovered) - strict_keys
    non_unknown_targets = set(recovered) - unknown_keys_before
    if extra:
        raise RuntimeError(f"Recovery keys absent from strict country audit: {list(sorted(extra))[:5]}")
    if non_unknown_targets:
        raise RuntimeError(f"Recovery attempted to overwrite non-UNKNOWN strict rows: {list(sorted(non_unknown_targets))[:5]}")

    promoted_audit = 0
    for row in audit_rows:
        key = identity_key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        evidence = recovered.get(key)
        if not evidence:
            continue
        row.update({
            "classification": evidence["classification"],
            "stateCode": evidence.get("jurisdiction"),
            "resolutionSource": "PIT_FILING_PRIMARY_DOCUMENT_COVER_JURISDICTION",
            "seedCik": evidence.get("historicalExactCik"),
            "evidenceForm": evidence.get("evidenceForm"),
            "evidenceDateFiled": evidence.get("evidenceDateFiled"),
            "evidenceFilename": evidence.get("evidenceFilename"),
            "evidenceDocumentUrl": evidence.get("evidenceDocumentUrl"),
            "filingCoverRecoveryEvidence": evidence,
        })
        promoted_audit += 1
    if promoted_audit != len(recovered):
        raise RuntimeError(f"Audit promotion mismatch: {promoted_audit} vs {len(recovered)}")

    promoted_holdings = 0
    promoted_holding_keys = set()
    snapshots = []
    for snapshot in country.get("monthSnapshots", []):
        month_counts = Counter()
        month_weights = defaultdict(float)
        filings = []
        for filing in snapshot.get("sourceFilings", []):
            report_date = filing.get("reportDate")
            fcounts = Counter()
            fweights = defaultdict(float)
            holdings = []
            for h0 in filing.get("holdings", []):
                h = dict(h0)
                cls = h.get("countryClassification", "UNKNOWN")
                if cls == "UNKNOWN" and h.get("mappingStatus") == "MATCHED_UNIQUE":
                    key = identity_key(h.get("mappedTicker"), h.get("mappedSecurityId"), report_date)
                    evidence = recovered.get(key)
                    if evidence:
                        cls = evidence["classification"]
                        h["countryClassification"] = cls
                        h["countryReason"] = "PIT_FILING_COVER_JURISDICTION"
                        h["countryResolutionEvidence"] = evidence
                        promoted_holdings += 1
                        promoted_holding_keys.add(key)
                weight = float(h.get("weight") or 0.0)
                fcounts[cls] += 1
                fweights[cls] += weight
                month_counts[cls] += 1
                month_weights[cls] += weight
                holdings.append(h)
            filings.append({
                **{k:v for k,v in filing.items() if k not in {"holdings", "countryClassificationCounts", "countryClassificationWeights"}},
                "countryClassificationCounts": dict(fcounts),
                "countryClassificationWeights": dict(fweights),
                "holdings": holdings,
            })
        snapshots.append({
            **{k:v for k,v in snapshot.items() if k not in {"sourceFilings", "countryClassificationCounts", "countryClassificationWeights"}},
            "countryClassificationCounts": dict(month_counts),
            "countryClassificationWeights": dict(month_weights),
            "sourceFilings": filings,
        })

    # A recovered identity/date need not appear in every monthly snapshot, but every promoted holding must have audit evidence.
    unexpected_holding_keys = promoted_holding_keys - set(recovered)
    if unexpected_holding_keys:
        raise RuntimeError(f"Promoted holdings without recovery evidence: {list(unexpected_holding_keys)[:5]}")

    country["monthSnapshots"] = snapshots
    country["resolvedUSCount"] = sum(r.get("classification") == "US" for r in audit_rows)
    country["resolvedNonUSCount"] = sum(r.get("classification") == "NON_US" for r in audit_rows)
    country["remainingUnknownCount"] = sum(r.get("classification") == "UNKNOWN" for r in audit_rows)
    country["filingCoverRecoveryAudit"] = {
        "rule": (
            "Promote only strict-country UNKNOWN exact identity/report-date keys when a pre-report-date historical SEC "
            "filing primary document in the already established unique historical CIK accession explicitly supplies "
            "the cover-page jurisdiction of incorporation/organization. No current metadata, fuzzy matching, US default, "
            "ranks, returns or performance are used."
        ),
        "recoveryShardCount": len(files),
        "recoveryInputCount": input_count,
        "recoveredIdentityDateCount": len(recovered),
        "recoveredUSCount": sum(r.get("classification") == "US" for r in recovered.values()),
        "recoveredNonUSCount": sum(r.get("classification") == "NON_US" for r in recovered.values()),
        "promotedAuditCount": promoted_audit,
        "promotedHoldingOccurrenceCount": promoted_holdings,
        "remainingUnknownCount": country["remainingUnknownCount"],
        "currentTickerFallbackAllowed": False,
        "outcomeDataConsulted": False,
    }
    country["currentTickerFallbackAllowed"] = False
    country["currentTickerFallbackCount"] = 0
    OUT.write_text(json.dumps(country, indent=2) + "\n")
    print("COVER_COUNTRY_MERGE", json.dumps(country["filingCoverRecoveryAudit"]), flush=True)


if __name__ == "__main__":
    main()
