#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'
SOURCE = DATA / 'sec-id-era-strict-series-source-h1-2007.json'
PARSER_INVARIANCE = DATA / 'nq-holdings-parser-invariance-h2-2006-h1-2007.json'
MAPPING = DATA / 'nq-series-id-structural-mapping-h1-2007.json'
COUNTRY = DATA / 'nq-series-id-country-pit-h1-2007.json'
COUNTRY_DIAGNOSTIC = DATA / 'nq-series-id-country-extension-diagnostic-h1-2007.json'
BUILDER = DATA / 'historical-universe-builder-h1-2007.json'
OUT = DATA / 'h1-2007-downstream-period-extension-validation.json'

SOURCE_ARTIFACT_ID = 10040000632
ALLOWED_MAPPING_METHODS = {
    'BASELINE_EXACT',
    'BASELINE_ADR_BASE_UNIQUE',
    'STRUCTURAL_SUFFIX_EXACT',
    'UNIQUE_LONG_PREFIX',
}
EXPECTED_DATES = [
    ('2007-01', '2007-01-31'),
    ('2007-02', '2007-02-28'),
    ('2007-03', '2007-03-30'),
    ('2007-04', '2007-04-30'),
    ('2007-05', '2007-05-31'),
    ('2007-06', '2007-06-29'),
]


def evidence_dates(snapshot: dict):
    for filing in snapshot.get('sourceFilings', []):
        for holding in filing.get('holdings', []):
            if holding.get('legacyAssetSection') != 'COMMON_EQUITY':
                continue
            if holding.get('mappingStatus') != 'MATCHED_UNIQUE':
                continue
            for evidence in holding.get('countryEvidence') or []:
                date_filed = evidence.get('evidenceDateFiled')
                if date_filed:
                    yield date_filed
            resolution = holding.get('countryResolutionEvidence') or {}
            evidence = resolution.get('resolutionEvidence') or {}
            date_filed = evidence.get('evidenceDateFiled')
            if date_filed:
                yield date_filed


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    source = json.loads(source_bytes)
    parser_invariance = json.loads(PARSER_INVARIANCE.read_text())
    mapping = json.loads(MAPPING.read_text())
    country = json.loads(COUNTRY.read_text())
    diagnostic = json.loads(COUNTRY_DIAGNOSTIC.read_text())
    builder = json.loads(BUILDER.read_text())

    source_months = source.get('monthSnapshots', [])
    expected = [
        (snap.get('signalMonth'), snap.get('asOf'), snap.get('sourceSeriesCount'))
        for snap in source_months
    ]

    checks: dict[str, bool] = {}
    checks['sourceLineageFixed'] = (
        len(source_months) == 6
        and [(m, d) for m, d, _ in expected] == EXPECTED_DATES
    )
    checks['parserInvariancePassed'] = (
        parser_invariance.get('passed') is True
        and parser_invariance.get('sourceCatalogOverlapCount', 0) > 0
        and parser_invariance.get('holdingsOverlapCount') == parser_invariance.get('sourceCatalogOverlapCount')
        and parser_invariance.get('semanticMismatchCount') == 0
        and parser_invariance.get('sourceOnlyMissingFromHoldingsOverlapCount') == 0
        and parser_invariance.get('holdingsOverlapNotInSourceOverlapCount') == 0
    )
    checks['mappingLineageFrozen'] = (
        mapping.get('authoritativeH1MappingRunId') == 34090287022
        and mapping.get('authoritativeH1MappingArtifactId') == 10006580498
        and mapping.get('npxArtifactId') == 9876020712
        and int(mapping.get('holdingsRunId') or 0) > 0
        and int(mapping.get('holdingsArtifactId') or 0) > 0
        and set(mapping.get('matchMethodCounts', {})).issubset(ALLOWED_MAPPING_METHODS)
    )
    checks['countryLineageFrozen'] = (
        country.get('catalogSha256') == source_sha
        and country.get('sourceCatalogSha256') == source_sha
        and country.get('sourceCatalogArtifactId') == SOURCE_ARTIFACT_ID
        and int(country.get('mappingRunId') or 0) > 0
        and int(country.get('mappingArtifactId') or 0) > 0
        and country.get('authoritativeH1CountryRunId') == 34104858455
        and country.get('authoritativeH1CountryArtifactId') == 10012280475
        and country.get('baseCountryEvidenceArtifactId') == 9944538015
        and country.get('structuralCountryEvidenceArtifactId') == 9944797581
        and country.get('npxArtifactId') == 9876020712
        and country.get('periodExtensionMasterYears') == [2005, 2006, 2007]
    )
    checks['builderCatalogFrozen'] = builder.get('catalogSha256') == source_sha
    checks['diagnosticCatalogFrozen'] = diagnostic.get('catalogSha256') == source_sha

    map_months = mapping.get('monthSnapshots', [])
    country_months = country.get('monthSnapshots', [])
    diagnostic_months = diagnostic.get('monthSnapshots', [])
    builder_months = builder.get('monthSnapshots', [])
    checks['sixMonthCoverage'] = all(
        len(rows) == 6
        for rows in (source_months, map_months, country_months, diagnostic_months, builder_months)
    )

    monthly = []
    exact_parity = True
    cardinality_ok = checks['sourceLineageFixed'] and checks['sixMonthCoverage']
    no_lookahead = checks['sixMonthCoverage']
    corp_bridge_ok = checks['sixMonthCoverage']

    if checks['sixMonthCoverage'] and checks['sourceLineageFixed']:
        for expected_row, mapped, resolved, reference, built in zip(
            expected, map_months, country_months, diagnostic_months, builder_months
        ):
            month, as_of, source_count = expected_row
            same_period = all(
                row.get('signalMonth') == month and row.get('asOf') == as_of
                for row in (mapped, resolved, reference, built)
            )
            same_counts = (
                mapped.get('sourceSeriesCount') == source_count
                and resolved.get('sourceSeriesCount') == source_count
                and reference.get('sourceSeriesCount') == source_count
                and built.get('sourceSeriesCount') == source_count
                and mapped.get('commonEquityHoldingCount') == resolved.get('commonEquityHoldingCount')
            )
            cardinality_ok = cardinality_ok and same_period and same_counts

            dates = list(evidence_dates(resolved))
            month_no_lookahead = all(date_filed <= as_of for date_filed in dates)
            no_lookahead = no_lookahead and month_no_lookahead
            month_corp_bridge_ok = resolved.get('corpPositiveNonCorpNameCount') == 0
            corp_bridge_ok = corp_bridge_ok and month_corp_bridge_ok

            month_exact_parity = (
                reference.get('primaryEligibleSourceSeriesCount') == built.get('eligibleSourceSeriesCount')
                and reference.get('primarySymbols') == built.get('symbols')
            )
            exact_parity = exact_parity and month_exact_parity
            monthly.append({
                'signalMonth': month,
                'asOf': as_of,
                'sourceSeriesCount': source_count,
                'eligibleSourceSeriesCount': built.get('eligibleSourceSeriesCount'),
                'universeSize': len(built.get('symbols', [])),
                'maxCountryEvidenceDate': max(dates) if dates else None,
                'corpPositiveNonCorpNameCount': resolved.get('corpPositiveNonCorpNameCount'),
                'exactBuilderParity': month_exact_parity,
            })
    else:
        exact_parity = False

    checks['periodCardinalityExact'] = cardinality_ok
    checks['countryNoLookahead'] = no_lookahead
    checks['corpBridgeMaterialityInvariant'] = corp_bridge_ok
    checks['frozenBuilderExactParitySixOfSix'] = exact_parity

    passed = all(checks.values())
    report = {
        'purpose': (
            'H1 2007 downstream period-extension validation under the definition committed before downstream execution. '
            'It verifies exact source/parser/mapping/country lineage, strict PIT country no-lookahead, the explicit CORP '
            'materiality invariant, and exact six-month parity between the frozen historical-Universe builder and the '
            'independent frozen H1 primary-Universe implementation. No Stage21 strategy outcomes are read.'
        ),
        'definition': 'docs/research/h1-2007-downstream-period-extension-validation-definition.md',
        'sourceCatalogArtifactId': SOURCE_ARTIFACT_ID,
        'sourceCatalogSha256': source_sha,
        'checks': checks,
        'monthly': monthly,
        'passed': passed,
    }
    OUT.write_text(json.dumps(report, indent=2) + '\n')
    print('H1_2007_PERIOD_EXTENSION_VALIDATION', json.dumps(report, separators=(',', ':')), flush=True)
    if not passed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
