#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"

PARSER_INVARIANCE = DATA / "nq-holdings-parser-invariance-h1-h2-2007.json"
MAPPING = DATA / "nq-series-id-structural-mapping-h2-2007.json"
COUNTRY = DATA / "nq-series-id-country-pit-h2-2007.json"
COUNTRY_DIAGNOSTIC = DATA / "nq-series-id-country-extension-diagnostic-h2-2007.json"
BUILDER = DATA / "historical-universe-builder-h2-2007.json"
OUT = DATA / "h2-2007-downstream-period-extension-validation.json"

SOURCE_SHA = "9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631"
EXPECTED = [
    ("2007-07", "2007-07-31", 465),
    ("2007-08", "2007-08-31", 469),
    ("2007-09", "2007-09-28", 499),
    ("2007-10", "2007-10-31", 518),
    ("2007-11", "2007-11-30", 531),
    ("2007-12", "2007-12-31", 533),
]
ALLOWED_MAPPING_METHODS = {
    "BASELINE_EXACT",
    "BASELINE_ADR_BASE_UNIQUE",
    "STRUCTURAL_SUFFIX_EXACT",
    "UNIQUE_LONG_PREFIX",
}


def evidence_dates(snapshot: dict):
    for filing in snapshot.get("sourceFilings", []):
        for holding in filing.get("holdings", []):
            if holding.get("legacyAssetSection") != "COMMON_EQUITY":
                continue
            if holding.get("mappingStatus") != "MATCHED_UNIQUE":
                continue
            for evidence in holding.get("countryEvidence") or []:
                date_filed = evidence.get("evidenceDateFiled")
                if date_filed:
                    yield date_filed
            resolution = holding.get("countryResolutionEvidence") or {}
            evidence = resolution.get("resolutionEvidence") or {}
            date_filed = evidence.get("evidenceDateFiled")
            if date_filed:
                yield date_filed


def main() -> None:
    parser_invariance = json.loads(PARSER_INVARIANCE.read_text())
    mapping = json.loads(MAPPING.read_text())
    country = json.loads(COUNTRY.read_text())
    diagnostic = json.loads(COUNTRY_DIAGNOSTIC.read_text())
    builder = json.loads(BUILDER.read_text())

    checks: dict[str, bool] = {}

    checks["parserInvariancePassed"] = (
        parser_invariance.get("passed") is True
        and parser_invariance.get("sourceCatalogOverlapCount") == 258
        and parser_invariance.get("holdingsOverlapCount") == 258
        and parser_invariance.get("exactFullRecordMatchCount") == 258
        and parser_invariance.get("semanticMismatchCount") == 0
        and parser_invariance.get("sourceOnlyMissingFromHoldingsOverlapCount") == 0
        and parser_invariance.get("holdingsOverlapNotInSourceOverlapCount") == 0
    )

    checks["mappingLineageFrozen"] = (
        mapping.get("sourceCatalogArtifactId") == 10041257985
        and mapping.get("sourceCatalogSha256") == SOURCE_SHA
        and mapping.get("holdingsRunId") == 34188353154
        and mapping.get("holdingsArtifactId") == 10041300366
        and mapping.get("npxPitRunId") == 34190105652
        and mapping.get("npxPitArtifactId") == 10041975282
        and mapping.get("npxBaseArtifactId") == 9876020712
        and mapping.get("mappingImplementationBlob") == "690479017fc82dce2480ded5d1ffafbb76721722"
        and set(mapping.get("matchMethodCounts", {})).issubset(ALLOWED_MAPPING_METHODS)
    )

    pit = country.get("npxIssuerVariantPitAudit") or {}
    blocked = pit.get("blockedFutureIssuerVariantOccurrencesBySignal") or {}
    checks["countryLineageFrozen"] = (
        country.get("catalogSha256") == SOURCE_SHA
        and country.get("sourceCatalogSha256") == SOURCE_SHA
        and country.get("sourceCatalogArtifactId") == 10041257985
        and country.get("mappingRunId") == 34190421577
        and country.get("mappingArtifactId") == 10042002365
        and country.get("authoritativeH1CountryRunId") == 34104858455
        and country.get("authoritativeH1CountryArtifactId") == 10012280475
        and country.get("baseCountryEvidenceArtifactId") == 9944538015
        and country.get("structuralCountryEvidenceArtifactId") == 9944797581
        and country.get("npxPitRunId") == 34190105652
        and country.get("npxPitArtifactId") == 10041975282
        and country.get("npxBaseArtifactId") == 9876020712
        and country.get("periodExtensionMasterYears") == [2005, 2006, 2007]
        and pit.get("incrementalRecordCountInDecemberContainer", 0) > 0
        and sum(blocked.values()) > 0
        and blocked.get("2007-12-31", 0) == 0
    )

    checks["builderCatalogFrozen"] = builder.get("catalogSha256") == SOURCE_SHA
    checks["diagnosticCatalogFrozen"] = (
        diagnostic.get("catalogSha256") == SOURCE_SHA
        and diagnostic.get("sourceCatalogSha256") == SOURCE_SHA
        and diagnostic.get("sourceCatalogArtifactId") == 10041257985
        and diagnostic.get("mappingRunId") == 34190421577
        and diagnostic.get("mappingArtifactId") == 10042002365
        and diagnostic.get("npxPitRunId") == 34190105652
        and diagnostic.get("npxPitArtifactId") == 10041975282
    )

    map_months = mapping.get("monthSnapshots", [])
    country_months = country.get("monthSnapshots", [])
    diagnostic_months = diagnostic.get("monthSnapshots", [])
    builder_months = builder.get("monthSnapshots", [])
    checks["sixMonthCoverage"] = all(len(rows) == 6 for rows in (map_months, country_months, diagnostic_months, builder_months))

    monthly = []
    exact_parity = True
    cardinality_ok = True
    no_lookahead = True
    corp_bridge_ok = True

    if checks["sixMonthCoverage"]:
        for expected, mapped, resolved, reference, built in zip(
            EXPECTED, map_months, country_months, diagnostic_months, builder_months
        ):
            month, as_of, source_count = expected
            same_period = all(
                row.get("signalMonth") == month and row.get("asOf") == as_of
                for row in (mapped, resolved, reference, built)
            )
            same_counts = (
                mapped.get("sourceSeriesCount") == source_count
                and resolved.get("sourceSeriesCount") == source_count
                and reference.get("sourceSeriesCount") == source_count
                and built.get("sourceSeriesCount") == source_count
                and mapped.get("commonEquityHoldingCount") == resolved.get("commonEquityHoldingCount")
            )
            cardinality_ok = cardinality_ok and same_period and same_counts

            dates = list(evidence_dates(resolved))
            month_no_lookahead = all(date_filed <= as_of for date_filed in dates)
            no_lookahead = no_lookahead and month_no_lookahead
            month_corp_bridge_ok = resolved.get("corpPositiveNonCorpNameCount") == 0
            corp_bridge_ok = corp_bridge_ok and month_corp_bridge_ok

            month_exact_parity = (
                reference.get("primaryEligibleSourceSeriesCount") == built.get("eligibleSourceSeriesCount")
                and reference.get("primarySymbols") == built.get("symbols")
            )
            exact_parity = exact_parity and month_exact_parity
            monthly.append({
                "signalMonth": month,
                "asOf": as_of,
                "sourceSeriesCount": source_count,
                "eligibleSourceSeriesCount": built.get("eligibleSourceSeriesCount"),
                "universeSize": len(built.get("symbols", [])),
                "maxCountryEvidenceDate": max(dates) if dates else None,
                "corpPositiveNonCorpNameCount": resolved.get("corpPositiveNonCorpNameCount"),
                "exactBuilderParity": month_exact_parity,
            })
    else:
        cardinality_ok = False
        no_lookahead = False
        corp_bridge_ok = False
        exact_parity = False

    checks["periodCardinalityExact"] = cardinality_ok
    checks["countryNoLookahead"] = no_lookahead
    checks["corpBridgeMaterialityInvariant"] = corp_bridge_ok
    checks["frozenBuilderExactParitySixOfSix"] = exact_parity

    passed = all(checks.values())
    report = {
        "purpose": (
            "H2 2007 downstream period-extension validation defined before execution. It verifies fixed source/parser/mapping/country/N-PX lineage, strict PIT country no-lookahead including H2 issuer-variant visibility, and exact six-month parity between the frozen historical-Universe builder and the independent frozen primary-Universe diagnostic extended to Jul-Dec 2007 inputs. No Stage21 returns, ranks, trades, CAGR, MaxDD, Calmar, portfolio outcomes, or strategy outcomes are read."
        ),
        "definition": "docs/research/h2-2007-downstream-period-extension-validation-definition.md",
        "sourceCatalogSha256": SOURCE_SHA,
        "checks": checks,
        "monthly": monthly,
        "passed": passed,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("H2_2007_PERIOD_EXTENSION_VALIDATION", json.dumps(report, separators=(",", ":")), flush=True)
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
