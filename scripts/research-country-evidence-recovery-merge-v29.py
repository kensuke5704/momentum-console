#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
BASE = R / "nq-hybrid-country-resolved-h1-2006.json"
MASTER_RECOVERY = R / "country-master-jurisdiction-recovery-v29.json"
CIK_GLOB = str(R / "country-jina-submission-cik-recovery-v29-shard-*.json")
OUT = R / "nq-hybrid-country-resolved-h1-2006.json"
AUDIT = R / "country-evidence-recovery-merge-audit-v29.json"

US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}


def key(ticker, security_id, report_date):
    return ((ticker or "").strip().upper(), security_id or None, report_date or None)


def validate_pre_report(evidence_date: str | None, report_date: str | None, k) -> None:
    if not evidence_date or not report_date or evidence_date > report_date:
        raise RuntimeError(f"future or missing evidence date for {k}: {evidence_date} > {report_date}")


def main() -> None:
    base = json.loads(BASE.read_text())
    master = json.loads(MASTER_RECOVERY.read_text())
    shard_paths = sorted(glob.glob(CIK_GLOB))
    if len(shard_paths) != 8:
        raise RuntimeError(f"expected 8 CIK recovery shards, found {len(shard_paths)}")
    shards = [json.loads(Path(p).read_text()) for p in shard_paths]
    shard_indices = sorted(int(s.get("shardIndex")) for s in shards)
    if shard_indices != list(range(8)):
        raise RuntimeError(f"unexpected shard indices: {shard_indices}")

    original_unknown = {
        key(r.get("ticker"), r.get("securityId"), r.get("asOfReportDate"))
        for r in base.get("resolutionAudit", [])
        if r.get("classification") == "UNKNOWN"
    }
    if len(original_unknown) != int(base.get("remainingUnknownCount") or 0):
        raise RuntimeError("base UNKNOWN exact-key count mismatch")

    candidates: dict[tuple, list[dict]] = defaultdict(list)

    # Source 1: conservative historical master suffix. Accept recognized US codes only.
    master_accepted = 0
    for row in master.get("results", []):
        k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        if k not in original_unknown:
            raise RuntimeError(f"master recovery key not original UNKNOWN: {k}")
        if row.get("classification") == "US" and row.get("stateCode") in US_CODES:
            if row.get("resolutionSource") != "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX":
                raise RuntimeError(f"unexpected master recovery source: {k}")
            if int(row.get("historicalExactCikCount") or 0) != 1 or not row.get("historicalExactCik"):
                raise RuntimeError(f"master promotion lacks unique historical CIK: {k}")
            evidence = row.get("evidence") or []
            if not evidence:
                raise RuntimeError(f"master promotion lacks evidence: {k}")
            for e in evidence:
                validate_pre_report(e.get("dateFiled"), row.get("asOfReportDate"), k)
                if e.get("stateCode") != row.get("stateCode"):
                    raise RuntimeError(f"master state conflict: {k}")
            candidates[k].append({
                "classification": "US",
                "stateCode": row["stateCode"],
                "resolutionSource": "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX",
                "seedSource": "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME",
                "seedCik": row["historicalExactCik"],
                "evidenceDateFiled": row.get("evidenceDateFiled"),
                "historicalMasterJurisdictionEvidence": evidence,
                "sourcePriority": 1,
            })
            master_accepted += 1

    # Source 2: stronger pre-report complete-submission header, identity bound by the already accepted unique historical CIK.
    cik_query_keys = set()
    cik_resolved = Counter()
    for shard in shards:
        for row in shard.get("results", []):
            k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
            if k not in original_unknown:
                raise RuntimeError(f"CIK recovery key not original UNKNOWN: {k}")
            if k in cik_query_keys:
                raise RuntimeError(f"duplicate CIK recovery key across shards: {k}")
            cik_query_keys.add(k)
            classification = row.get("classification")
            if classification not in {"US", "NON_US"}:
                continue
            if row.get("resolutionSource") != "PIT_JINA_SUBMISSION_HEADER_UNIQUE_HISTORICAL_CIK_STATE":
                raise RuntimeError(f"unexpected CIK recovery source: {k}")
            if not row.get("historicalExactCik") or not row.get("stateCode") or not row.get("evidenceFilename"):
                raise RuntimeError(f"CIK recovery incomplete evidence: {k}")
            validate_pre_report(row.get("evidenceDateFiled"), row.get("asOfReportDate"), k)
            expected = "US" if row.get("stateCode") in US_CODES else "NON_US"
            if classification != expected:
                raise RuntimeError(f"CIK state/classification mismatch: {k}")
            candidates[k].append({
                "classification": classification,
                "stateCode": row["stateCode"],
                "resolutionSource": row["resolutionSource"],
                "seedSource": "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME",
                "seedCik": row["historicalExactCik"],
                "historicalEntityName": row.get("historicalEntityName"),
                "evidenceForm": row.get("evidenceForm"),
                "evidenceDateFiled": row.get("evidenceDateFiled"),
                "evidenceFilename": row.get("evidenceFilename"),
                "evidenceTransport": row.get("evidenceTransport"),
                "sourcePriority": 2,
            })
            cik_resolved[classification] += 1

    promotions = {}
    conflicts = []
    for k, evidence_rows in candidates.items():
        classes = {e["classification"] for e in evidence_rows}
        states = {e["stateCode"] for e in evidence_rows}
        if len(classes) > 1:
            conflicts.append({"key": list(k), "classifications": sorted(classes), "states": sorted(states)})
            continue
        # Stronger submission-header evidence wins metadata when it agrees with master suffix.
        promotions[k] = max(evidence_rows, key=lambda e: e["sourcePriority"])
    if conflicts:
        raise RuntimeError(f"country recovery evidence conflicts: {len(conflicts)} sample={conflicts[:5]}")

    # Resolution audit promotion.
    resolution = []
    promoted_resolution = 0
    for row in base.get("resolutionAudit", []):
        k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        ev = promotions.get(k)
        if ev:
            if row.get("classification") != "UNKNOWN":
                raise RuntimeError(f"attempted overwrite of known country: {k}")
            nr = dict(row)
            nr.update({kk: vv for kk, vv in ev.items() if kk != "sourcePriority"})
            resolution.append(nr)
            promoted_resolution += 1
        else:
            resolution.append(row)
    if promoted_resolution != len(promotions):
        raise RuntimeError("resolution promotion coverage mismatch")

    # Snapshot holdings promotion and recomputation.
    reason_counts = Counter(base.get("reasonCounts") or {})
    promoted_holdings = 0
    promoted_weight = 0.0
    snapshots = []
    for snapshot in base.get("monthSnapshots", []):
        month_counts = Counter()
        month_weights = defaultdict(float)
        filings = []
        for filing in snapshot.get("sourceFilings", []):
            report_date = filing.get("reportDate")
            fcounts = Counter()
            fweights = defaultdict(float)
            holdings = []
            for holding in filing.get("holdings", []):
                h = dict(holding)
                if h.get("mappingStatus") == "MATCHED_UNIQUE" and h.get("countryClassification") == "UNKNOWN":
                    k = key(h.get("mappedTicker"), h.get("mappedSecurityId"), report_date)
                    ev = promotions.get(k)
                    if ev:
                        h["countryClassification"] = ev["classification"]
                        h["countryReason"] = ev["resolutionSource"]
                        h["countryResolutionEvidence"] = {kk:vv for kk,vv in ev.items() if kk != "sourcePriority"}
                        promoted_holdings += 1
                        promoted_weight += float(h.get("weight") or 0.0)
                        reason_counts[ev["resolutionSource"]] += 1
                cls = h.get("countryClassification") or "UNKNOWN"
                w = float(h.get("weight") or 0.0)
                fcounts[cls] += 1; fweights[cls] += w
                month_counts[cls] += 1; month_weights[cls] += w
                holdings.append(h)
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

    old_us = int(base.get("resolvedUSCount") or 0)
    old_non_us = int(base.get("resolvedNonUSCount") or 0)
    old_unknown = int(base.get("remainingUnknownCount") or 0)
    p_us = sum(e["classification"] == "US" for e in promotions.values())
    p_non_us = sum(e["classification"] == "NON_US" for e in promotions.values())

    out = dict(base)
    out["purpose"] = str(base.get("purpose") or "") + " Additional globally applied PIT recovery uses recognized-US historical SEC master jurisdiction suffixes and pre-report complete-submission header state bound to an already unique historical CIK."
    out["countryEvidenceRule"] = str(base.get("countryEvidenceRule") or "") + " -> PIT_SEC_MASTER_RECOGNIZED_US_SUFFIX / PIT_SUBMISSION_UNIQUE_HISTORICAL_CIK_STATE -> UNKNOWN"
    out["resolvedUSCount"] = old_us + p_us
    out["resolvedNonUSCount"] = old_non_us + p_non_us
    out["remainingUnknownCount"] = old_unknown - len(promotions)
    out["currentTickerFallbackAllowed"] = False
    out["currentTickerFallbackCount"] = 0
    out["reasonCounts"] = dict(reason_counts)
    out["resolutionAudit"] = resolution
    out["monthSnapshots"] = snapshots
    out["evidenceRecoveryAudit"] = {
        "baseUnknownCount": old_unknown,
        "masterRecognizedUSCandidateCount": master_accepted,
        "cikRecoveryQueryCoverageCount": len(cik_query_keys),
        "cikRecoveryResolvedUSCount": cik_resolved["US"],
        "cikRecoveryResolvedNonUSCount": cik_resolved["NON_US"],
        "mergedPromotionCount": len(promotions),
        "mergedPromotionUSCount": p_us,
        "mergedPromotionNonUSCount": p_non_us,
        "remainingUnknownCount": out["remainingUnknownCount"],
        "promotedHoldingOccurrenceCount": promoted_holdings,
        "promotedHoldingWeightAcrossSnapshots": promoted_weight,
        "conflictCount": 0,
        "currentTickerFallbackCount": 0,
        "stage21PerformanceConsulted": False,
        "productionModified": False,
    }

    if sum(r.get("classification") == "UNKNOWN" for r in resolution) != out["remainingUnknownCount"]:
        raise RuntimeError("post-merge UNKNOWN count mismatch")
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    AUDIT.write_text(json.dumps(out["evidenceRecoveryAudit"], indent=2) + "\n")
    print("EVIDENCE_RECOVERY_MERGE", json.dumps(out["evidenceRecoveryAudit"]), flush=True)


if __name__ == "__main__":
    main()
