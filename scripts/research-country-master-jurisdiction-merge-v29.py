#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
BASE = R / "nq-hybrid-country-resolved-h1-2006.json"
RECOVERY = R / "country-master-jurisdiction-recovery-v29.json"
OUT = R / "nq-hybrid-country-resolved-h1-2006.json"
AUDIT = R / "country-master-jurisdiction-merge-audit-v29.json"

US_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","X1"
}


def key(ticker, security_id, report_date):
    return ((ticker or "").strip().upper(), security_id or None, report_date or None)


def main() -> None:
    base = json.loads(BASE.read_text())
    recovery = json.loads(RECOVERY.read_text())

    base_unknown = {
        key(r.get("ticker"), r.get("securityId"), r.get("asOfReportDate"))
        for r in base.get("resolutionAudit", [])
        if r.get("classification") == "UNKNOWN"
    }
    if len(base_unknown) != int(base.get("remainingUnknownCount") or len(base_unknown)):
        raise RuntimeError("base UNKNOWN exact-key count does not match remainingUnknownCount")

    promotions = {}
    rejected_non_us_or_unknown = 0
    for row in recovery.get("results", []):
        k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        if k not in base_unknown:
            raise RuntimeError(f"recovery row is not an original strict UNKNOWN key: {k}")
        # Conservative promotion policy: historical master suffix is accepted only when
        # it is an explicit recognized US state/jurisdiction code. Unknown historical
        # suffixes such as NEW/NW/BER are NOT interpreted as NON_US here.
        if row.get("classification") != "US" or row.get("stateCode") not in US_CODES:
            rejected_non_us_or_unknown += 1
            continue
        if row.get("resolutionSource") != "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX":
            raise RuntimeError(f"unexpected recovery source for {k}: {row.get('resolutionSource')}")
        if int(row.get("historicalExactCikCount") or 0) != 1 or not row.get("historicalExactCik"):
            raise RuntimeError(f"US promotion without unique historical CIK: {k}")
        evidence = row.get("evidence") or []
        if not evidence:
            raise RuntimeError(f"US promotion without historical master evidence: {k}")
        report_date = row.get("asOfReportDate")
        if any(not e.get("dateFiled") or e["dateFiled"] > report_date for e in evidence):
            raise RuntimeError(f"future-dated master evidence for {k}")
        codes = {e.get("stateCode") for e in evidence}
        ciks = {str(e.get("cik") or "").zfill(10) for e in evidence}
        if codes != {row.get("stateCode")} or ciks != {str(row.get("historicalExactCik")).zfill(10)}:
            raise RuntimeError(f"inconsistent jurisdiction evidence for {k}")
        if k in promotions and promotions[k] != row:
            raise RuntimeError(f"conflicting recovery rows for {k}")
        promotions[k] = row

    # Promote only original UNKNOWN resolution-audit keys.
    new_resolution = []
    promoted_resolution_count = 0
    for row in base.get("resolutionAudit", []):
        k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        rec = promotions.get(k)
        if rec:
            if row.get("classification") != "UNKNOWN":
                raise RuntimeError(f"attempted overwrite of known country: {k}")
            nr = dict(row)
            nr.update({
                "classification": "US",
                "stateCode": rec["stateCode"],
                "resolutionSource": "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX",
                "seedSource": "HISTORICAL_MASTER_ISSUER_FORM_EXACT_NAME",
                "seedCik": rec["historicalExactCik"],
                "evidenceForm": (rec.get("evidence") or [{}])[0].get("form"),
                "evidenceDateFiled": rec.get("evidenceDateFiled"),
                "historicalMasterJurisdictionEvidence": rec.get("evidence"),
            })
            new_resolution.append(nr)
            promoted_resolution_count += 1
        else:
            new_resolution.append(row)

    if promoted_resolution_count != len(promotions):
        raise RuntimeError(f"promotion coverage mismatch: audit={promoted_resolution_count} promotions={len(promotions)}")

    # Promote matching mapped holdings and recompute all country counts/weights.
    promoted_holding_count = 0
    promoted_holding_weight = 0.0
    snapshots = []
    reason_counts = Counter(base.get("reasonCounts") or {})
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
                    rec = promotions.get(k)
                    if rec:
                        h["countryClassification"] = "US"
                        h["countryReason"] = "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX"
                        h["countryResolutionEvidence"] = rec
                        promoted_holding_count += 1
                        promoted_holding_weight += float(h.get("weight") or 0.0)
                        reason_counts["PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX"] += 1
                classification = h.get("countryClassification") or "UNKNOWN"
                w = float(h.get("weight") or 0.0)
                fcounts[classification] += 1
                fweights[classification] += w
                month_counts[classification] += 1
                month_weights[classification] += w
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
    if len(promotions) > old_unknown:
        raise RuntimeError("promotion count exceeds base UNKNOWN count")

    out = dict(base)
    out["purpose"] = (
        str(base.get("purpose") or "") + " Additional conservative PIT recovery promotes only original UNKNOWN "
        "identity/report-date keys whose historical SEC master-index exact issuer/unique-CIK rows carry one "
        "consistent recognized US jurisdiction suffix. Unrecognized suffixes remain UNKNOWN."
    )
    out["countryEvidenceRule"] = str(base.get("countryEvidenceRule") or "") + " -> PIT_SEC_MASTER_RECOGNIZED_US_JURISDICTION_SUFFIX -> UNKNOWN"
    out["currentTickerFallbackAllowed"] = False
    out["currentTickerFallbackCount"] = 0
    out["resolvedUSCount"] = old_us + len(promotions)
    out["resolvedNonUSCount"] = old_non_us
    out["remainingUnknownCount"] = old_unknown - len(promotions)
    out["reasonCounts"] = dict(reason_counts)
    out["resolutionAudit"] = new_resolution
    out["monthSnapshots"] = snapshots
    out["masterJurisdictionRecoveryAudit"] = {
        "recoveryInputUnknownCount": recovery.get("inputUnknownCount"),
        "recoveryHistoricalExactUniqueCikCount": recovery.get("historicalExactUniqueCikCount"),
        "recoveryRawResolvedCount": recovery.get("resolvedCount"),
        "acceptedUSPromotionCount": len(promotions),
        "rejectedNonUSOrUnrecognizedSuffixCount": rejected_non_us_or_unknown,
        "promotedHoldingOccurrenceCount": promoted_holding_count,
        "promotedHoldingWeightAcrossSnapshots": promoted_holding_weight,
        "acceptedResolutionSource": "PIT_SEC_MASTER_COMPANY_NAME_JURISDICTION_SUFFIX",
        "acceptedStateCodes": sorted({r["stateCode"] for r in promotions.values()}),
        "policy": "Only recognized US_CODES are promoted. No inference is made from unrecognized suffixes; they remain UNKNOWN.",
    }

    if len([r for r in out["resolutionAudit"] if r.get("classification") == "UNKNOWN"]) != out["remainingUnknownCount"]:
        raise RuntimeError("post-merge UNKNOWN count mismatch")
    if out.get("currentTickerFallbackCount") != 0 or out.get("currentTickerFallbackAllowed") is not False:
        raise RuntimeError("current ticker fallback invariant violated")

    OUT.write_text(json.dumps(out, indent=2) + "\n")
    audit = {
        "baseUnknownCount": old_unknown,
        "acceptedUSPromotionCount": len(promotions),
        "remainingUnknownCount": out["remainingUnknownCount"],
        "promotedHoldingOccurrenceCount": promoted_holding_count,
        "promotedHoldingWeightAcrossSnapshots": promoted_holding_weight,
        "currentTickerFallbackCount": 0,
        "productionModified": False,
        "stage21PerformanceConsulted": False,
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n")
    print("MASTER_JURISDICTION_MERGE", json.dumps(audit), flush=True)


if __name__ == "__main__":
    main()
