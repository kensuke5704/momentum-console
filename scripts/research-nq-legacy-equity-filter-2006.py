#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "data/research/nq-npx-mapping-2006.json"
OUT = ROOT / "data/research/nq-legacy-equity-filter-2006.json"

ADR_GDR = re.compile(r"\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b", re.I)
NON_EQUITY = re.compile(
    r"\b(?:BOND|BONDS|NOTE|NOTES|DEBENTURE|DEBENTURES|PREFERRED|PREF\.|WARRANT|WARRANTS|RIGHT|RIGHTS|OPTION|OPTIONS|CONVERTIBLE\s+NOTE|SR\s+NT|SUB\s+NT)\b",
    re.I,
)
NON_CORP_LEGAL = re.compile(r"\b(?:L\.?P\.?|LIMITED PARTNERSHIP|LLC|L\.L\.C\.)\s*$", re.I)


def classify(description: str, status: str) -> tuple[str, str]:
    if status == "PARSER_ARTIFACT":
        return "EXCLUDE_PARSER_ARTIFACT", "parser_artifact"
    if status not in {"TIER_A", "TIER_B"}:
        return "EXCLUDE_UNRESOLVED_IDENTITY", status.lower()
    if ADR_GDR.search(description):
        return "EXCLUDE_NON_US_PROXY", "adr_or_gdr"
    if NON_EQUITY.search(description):
        return "EXCLUDE_NON_EC_PROXY", "debt_preferred_derivative_or_right"
    if NON_CORP_LEGAL.search(description.strip()):
        return "EXCLUDE_NON_CORP_PROXY", "partnership_or_llc"
    return "LEGACY_EQUITY_CANDIDATE", "no_structural_exclusion_detected"


def ratio(n: float, d: float):
    return n / d if d else None


def main() -> None:
    mapping = json.loads(MAPPING.read_text())
    details = []
    counts = Counter()
    weights = defaultdict(float)
    total_weight = 0.0
    accepted_identity_weight = 0.0

    for row in mapping.get("details", []):
        description = str(row.get("description") or "")
        status = str(row.get("status") or "")
        weight = float(row.get("weight") or 0.0)
        bucket, reason = classify(description, status)
        counts[bucket] += 1
        weights[bucket] += weight
        total_weight += weight
        if status in {"TIER_A", "TIER_B"}:
            accepted_identity_weight += weight
        details.append({
            "seriesId": row.get("seriesId"),
            "fundTickers": row.get("fundTickers", []),
            "reportDate": row.get("reportDate"),
            "description": description,
            "weight": weight,
            "identityStatus": status,
            "legacyEligibility": bucket,
            "reason": reason,
            "identities": row.get("identities"),
            "ticker": row.get("ticker"),
        })

    candidate = counts["LEGACY_EQUITY_CANDIDATE"]
    candidate_weight = weights["LEGACY_EQUITY_CANDIDATE"]
    out = {
        "year": 2006,
        "purpose": "Structural legacy proxy for N-PORT US/CORP/EC eligibility using only filing descriptors and accepted historical identities. No return/performance data used.",
        "policy": {
            "identity": "Require Tier A or Tier B from the N-Q to N-PX mapping stage.",
            "US": "Exclude explicit ADR/GDR/depositary-receipt descriptions. Do not infer issuer domicile from company-name spelling or ticker.",
            "EC": "Exclude explicit debt, preferred, option, warrant, right, and similar non-common-equity descriptors.",
            "CORP": "Exclude explicit LP/limited-partnership/LLC legal forms. Do not exclude words such as Trust inside a corporate name because of false positives such as Northern Trust Corp.",
            "unknown": "Items without an explicit structural exclusion remain LEGACY_EQUITY_CANDIDATE; this is a proxy, not asserted N-PORT field parity.",
        },
        "mappingRule": mapping.get("mappingRule"),
        "nqPitSeriesRecords": mapping.get("nqPitSeriesRecords"),
        "holdingCount": len(details),
        "totalParserRelativeWeight": total_weight,
        "acceptedIdentityWeight": accepted_identity_weight,
        "acceptedIdentityWeightRate": ratio(accepted_identity_weight, total_weight),
        "legacyEquityCandidateCount": candidate,
        "legacyEquityCandidateWeight": candidate_weight,
        "legacyEquityCandidateWeightRate": ratio(candidate_weight, total_weight),
        "bucketCounts": dict(counts),
        "bucketWeights": dict(weights),
        "details": details,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("SUMMARY", json.dumps({k: v for k, v in out.items() if k != "details"}), flush=True)


if __name__ == "__main__":
    main()
