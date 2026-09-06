#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"


def pearson_rank_correlation(a: list[dict], b: list[dict]) -> float | None:
    """Spearman for two top lists = Pearson correlation of their rank numbers on common symbols.

    The common symbols may occupy non-contiguous original ranks because symbols absent from
    the other list leave gaps. Therefore the shortcut 1-6*sum(d^2)/(n*(n^2-1)) is invalid
    here unless ranks are first reranked contiguously. We intentionally preserve original
    universe rank positions and compute their Pearson correlation directly.
    """
    ar = {x["symbol"]: float(x["universeRank"]) for x in a}
    br = {x["symbol"]: float(x["universeRank"]) for x in b}
    common = sorted(set(ar) & set(br))
    if len(common) < 2:
        return 1.0 if len(common) == len(ar) == len(br) else None
    xs = [ar[s] for s in common]
    ys = [br[s] for s in common]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return cov / math.sqrt(vx * vy)


def compare(a: list[dict], b: list[dict]) -> dict:
    ar = {x["symbol"]: x["universeRank"] for x in a}
    br = {x["symbol"]: x["universeRank"] for x in b}
    common = set(ar) & set(br)
    k = min(len(a), len(b), 80)
    overlap = len(common) / k if k else 1.0
    top = [x["symbol"] for x in a[:2]]
    retention = sum(s in br for s in top) / len(top) if top else 1.0
    return {
        "overlap": overlap,
        "spearman": pearson_rank_correlation(a, b),
        "top2Retention": retention,
        "commonCount": len(common),
        "k": k,
        "primaryTop2": top,
    }


def main() -> None:
    sa = json.loads((R / "momentum-v2-9-authoritative-source-audit-v6-h1-2006.json").read_text())
    pa = json.loads((R / "momentum-v2-9-authoritative-holdings-audit-v5-h1-2006.json").read_text())
    mp = json.loads((R / "nq-hybrid-structural-mapping-h1-2006.json").read_text())
    co = json.loads((R / "nq-hybrid-country-resolved-h1-2006.json").read_text())
    pr = json.loads((R / "nq-hybrid-universe-h1-2006.json").read_text())
    up = json.loads((R / "nq-hybrid-universe-country-upper-bound-h1-2006.json").read_text())
    aid = int((R / "authoritative-holdings-v8-artifact-id.txt").read_text())

    # Frozen, already-accepted structural evidence. These values are not recomputed or
    # tuned here and contain no Stage21 return/performance outcome.
    accepted = {
        "gateA": {
            "medianTopKOverlap": 0.9375,
            "minimumTopKOverlap": 0.925,
            "medianSpearman": 0.9996,
            "productionTop2IndividualRetention": 1.0,
            "bothTop2RetainedRate": 1.0,
        },
        "transitionSourceFidelity": {
            "LRGE": {"count": 0.929, "weight": 0.959},
            "GFIN": {"count": 0.942, "weight": 0.974},
            "PPTY": {"count": 0.939, "weight": 0.980},
        },
        "transitionAggregate2020_01": {
            "productionNamesRecovered": 8,
            "productionNameCount": 9,
            "overlap": 8 / 9,
            "spearman": 0.842,
            "productionTop2Retained": 2,
            "productionTop2Count": 2,
        },
        "transitionCorpBridge": {"ecUsCorpCount": 226, "ecUsCount": 226},
    }
    accepted_evidence_pass = (
        accepted["gateA"]["medianTopKOverlap"] >= 0.80
        and accepted["gateA"]["minimumTopKOverlap"] >= 0.70
        and accepted["gateA"]["medianSpearman"] >= 0.75
        and accepted["gateA"]["productionTop2IndividualRetention"] >= 0.85
        and accepted["gateA"]["bothTop2RetainedRate"] >= 0.75
        and accepted["transitionAggregate2020_01"]["overlap"] >= 0.80
        and accepted["transitionAggregate2020_01"]["spearman"] >= 0.75
        and accepted["transitionAggregate2020_01"]["productionTop2Retained"] == 2
    )

    allowed = {"BASELINE_EXACT", "BASELINE_ADR_BASE_UNIQUE", "STRUCTURAL_SUFFIX_EXACT", "UNIQUE_LONG_PREFIX"}
    unexpected = sorted(set(mp.get("matchMethodCounts") or {}) - allowed)
    mm = {x["signalMonth"]: x for x in mp["monthSnapshots"]}
    cm = {x["signalMonth"]: x for x in co["monthSnapshots"]}
    pm = {x["signalMonth"]: x for x in pr["monthSnapshots"]}
    um = {x["signalMonth"]: x for x in up["monthSnapshots"]}
    months = []

    for month in sorted(pm):
        m, c, p, u = mm[month], cm[month], pm[month], um[month]
        mapped = known = 0
        mapped_weight = known_weight = 0.0
        for filing in c["sourceFilings"]:
            for holding in filing.get("holdings", []):
                if holding.get("mappingStatus") != "MATCHED_UNIQUE":
                    continue
                mapped += 1
                weight = float(holding.get("weight") or 0.0)
                mapped_weight += weight
                if holding.get("countryClassification") in {"US", "NON_US"}:
                    known += 1
                    known_weight += weight
        months.append({
            "signalMonth": month,
            "commonEquityHoldingCount": m["commonEquityHoldingCount"],
            "uniqueMappedCount": m["uniqueMappedCount"],
            "uniqueMappedCountRate": m["uniqueMappedCountRate"],
            "uniqueMappedWeightRate": m["uniqueMappedWeightRate"],
            "ambiguousCount": m["ambiguousCount"],
            "ambiguousWeight": m["ambiguousWeight"],
            "unmappedCount": m["unmappedCount"],
            "unmappedWeight": m["unmappedWeight"],
            "mappedCountryKnownCountRate": known / mapped if mapped else None,
            "mappedCountryKnownWeightRate": known_weight / mapped_weight if mapped_weight else None,
            "eligibleSourceSeriesCount": p["eligibleSourceSeriesCount"],
            "primaryUniverseSize": len(p["symbols"]),
            "upperUniverseSize": len(u["symbols"]),
            "upperComparison": compare(p["symbols"], u["symbols"]),
        })

    conflicts: list[str] = []
    if not accepted_evidence_pass:
        conflicts.append("FROZEN_ACCEPTED_EVIDENCE_THRESHOLD")
    if any(sa.get(k) for k in (
        "umbrellaIdentityCount", "internationalGrowthCount", "vanguardAliasGroupCount",
        "iSharesTrailingFundAliasGroupCount", "ambiguousBridgeCount", "postIdBoundaryQualificationFetchErrorCount",
    )):
        conflicts.append("SOURCE_IDENTITY_BOUNDARY_OR_BRIDGE")
    parser_fields = (
        "filingFetchErrorCount", "missingCurrentSourceKeyCount", "extraOutputSourceKeyCount",
        "uniqueZeroHoldingTargetCount", "uniqueNoGroupedTargetCount", "ambiguousAssignedMarkerCount",
        "badFinancialTextHoldingCount", "temporalLabelHoldingCount", "summaryAggregateHoldingCount",
    )
    if any(pa.get(k) for k in parser_fields):
        conflicts.append("PARSER_STRUCTURAL_ERROR")
    if unexpected:
        conflicts.append("UNAPPROVED_NPX_MAPPING_METHOD")
    if co.get("currentTickerFallbackAllowed") is not False or co.get("currentTickerFallbackCount") != 0:
        conflicts.append("CURRENT_TICKER_COUNTRY_FALLBACK")
    if any(x["eligibleSourceSeriesCount"] == 0 or x["primaryUniverseSize"] == 0 for x in months):
        conflicts.append("EMPTY_SOURCE_OR_UNIVERSE")

    # This is a deliberately conservative uncertainty diagnostic: every month must retain
    # >=70% of Top-K, rank correlation >=0.75 where defined, and both primary Top2 names
    # under the extreme assumption that every deterministically mapped UNKNOWN is US.
    stable = all(
        x["upperComparison"]["overlap"] >= 0.70
        and (x["upperComparison"]["spearman"] is None or x["upperComparison"]["spearman"] >= 0.75)
        and x["upperComparison"]["top2Retention"] >= 0.80
        for x in months
    )
    if not stable:
        conflicts.append("COUNTRY_UPPER_BOUND_MATERIAL")

    out = {
        "purpose": "Final return-independent Gate B v10 decision for Momentum v2.9 H1 2006 historical Universe reconstruction. Combines frozen accepted transition evidence with corrected source-v6, authoritative holdings-v8, deterministic N-PX mapping, strict PIT country and conservative UNKNOWN upper-bound sensitivity.",
        "authoritativeHoldingsArtifactId": aid,
        "frozenNpxMasterArtifactId": 9876020712,
        "acceptedStructuralEvidence": accepted,
        "acceptedStructuralEvidencePass": accepted_evidence_pass,
        "sourceIdentity": sa,
        "parsing": {k: pa.get(k) for k in (
            "uniqueSourceFilingCount", "filingFetchSuccessCount", "filingFetchErrorCount",
            "uniqueParsedHoldingCount", "assetSectionCounts", "parseMethodCountsAcrossSnapshots",
            "catalogKeyCount", "outputKeyCount", "missingCurrentSourceKeyCount", "extraOutputSourceKeyCount",
            "uniqueZeroHoldingTargetCount", "uniqueNoGroupedTargetCount", "ambiguousAssignedMarkerCount",
            "badFinancialTextHoldingCount", "temporalLabelHoldingCount", "summaryAggregateHoldingCount",
        )},
        "mappingMethodCounts": mp.get("matchMethodCounts"),
        "unexpectedMappingMethods": unexpected,
        "mappingUncertaintyPolicy": "AMBIGUOUS_AND_UNMAPPED_EXCLUDED_NOT_AUTO_ASSIGNED",
        "country": {k: co.get(k) for k in (
            "countryEvidenceRule", "currentTickerFallbackAllowed", "currentTickerFallbackCount",
            "unresolvedInputCount", "resolvedUSCount", "resolvedNonUSCount", "remainingUnknownCount",
        )},
        "countryUncertaintyPolicy": "UNKNOWN_EXCLUDED_PRIMARY; MAPPED_UNKNOWN_TO_US_ONLY_IN_UPPER_BOUND_SENSITIVITY",
        "countryUpperBoundSpearmanMethod": "PEARSON_CORRELATION_OF_ORIGINAL_RANK_NUMBERS_ON_COMMON_SYMBOLS",
        "months": months,
        "countryUpperBoundSensitivityStable": stable,
        "structuralConflicts": conflicts,
        "gateBPass": not conflicts,
        "universeReconstructionConfirmed": not conflicts,
        "stage21PerformanceConsulted": False,
        "productionModified": False,
    }
    (R / "momentum-v2-9-final-gate-b-v10-h1-2006.json").write_text(json.dumps(out, indent=2) + "\n")
    print("GATE_B_V10", json.dumps({k: v for k, v in out.items() if k != "months"}), flush=True)
    for x in months:
        print("MONTH", json.dumps(x), flush=True)
    if conflicts:
        raise SystemExit("Gate B v10 blockers: " + ",".join(conflicts))


if __name__ == "__main__":
    main()
