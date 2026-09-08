#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/research"

PARSER_INVARIANCE = DATA / "nq-holdings-parser-invariance-h1-h2-2006.json"
MAPPING = DATA / "nq-series-id-structural-mapping-h2-2006.json"
COUNTRY = DATA / "nq-series-id-country-pit-h2-2006.json"
COUNTRY_DIAGNOSTIC = DATA / "nq-series-id-country-extension-diagnostic-h2-2006.json"
BUILDER = DATA / "historical-universe-builder-h2-2006.json"
OUT = DATA / "h2-2006-downstream-period-extension-validation.json"

SOURCE_SHA = "f79f8d9e6d7fe45cb115a9c7f087dcca00622ff602cc0147e70e860f3528417d"
EXPECTED = [
    ("2006-07", "2006-07-31", 199),
    ("2006-08", "2006-08-31", 221),
    ("2006-09", "2006-09-29", 242),
    ("2006-10", "2006-10-31", 242),
    ("2006-11", "2006-11-30", 245),
    ("2006-12", "2006-12-29", 251),
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
        and parser_invariance.get("h1ArtifactId") == 10006530879
        and parser_invariance.get("h2ArtifactId") == 10038557328
        and parser_invariance.get("overlapCount") == 120
        and parser_invariance.get("semanticMismatchCount") == 0
    )

    checks["mappingLineageFrozen"] = (
        mapping.get("holdingsRunId") == 34179821383
        and mapping.get("holdingsArtifactId") == 10038557328
        and mapping.get("authoritativeH1MappingRunId") == 34090287022
        and mapping.get("authoritativeH1MappingArtifactId") == 10006580498
        and mapping.get("npxArtifactId") == 9876020712
        and set(mapping.get("matchMethodCounts", {})).issubset(ALLOWED_MAPPING_METHODS)
    )

    checks["countryLineageFrozen"] = (
        country.get("catalogSha256") == SOURCE_SHA
        and country.get("sourceCatalogSha256") == SOURCE_SHA
        and country.get("sourceCatalogArtifactId") == 10038284691
        and country.get("mappingRunId") == 34180122700
        and country.get("mappingArtifactId") == 10038597826
        and country.get("authoritativeH1CountryRunId") == 34104858455
        and country.get("authoritativeH1CountryArtifactId") == 10012280475
        and country.get("baseCountryEvidenceArtifactId") == 9944538015
        and country.get("structuralCountryEvidenceArtifactId") == 9944797581
    )

    checks["builderCatalogFrozen"] = builder.get("catalogSha256") == SOURCE_SHA
    checks["diagnosticCatalogFrozen"] = diagnostic.get("catalogSha256") == SOURCE_SHA

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
            "H2 2006 downstream period-extension validation defined before execution. It verifies fixed source/parser/mapping/country lineage, strict PIT country no-lookahead, and exact six-month parity between the frozen historical-Universe builder and the independent frozen H1 primary-Universe implementation extended to Jul-Dec inputs. No Stage21 returns, trades, CAGR, MaxDD, Calmar, or strategy outcomes are read."
        ),
        "definition": "docs/research/h2-2006-downstream-period-extension-validation-definition.md",
        "sourceCatalogSha256": SOURCE_SHA,
        "checks": checks,
        "monthly": monthly,
        "passed": passed,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("H2_PERIOD_EXTENSION_VALIDATION", json.dumps(report, separators=(",", ":")), flush=True)
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
