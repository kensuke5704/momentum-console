#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/research'
MAPPING = DATA / 'nq-series-id-structural-mapping-h1-2008.json'
COUNTRY = DATA / 'nq-series-id-country-pit-h1-2008.json'
DIAGNOSTIC = DATA / 'nq-series-id-country-extension-diagnostic-h1-2008.json'
BUILDER = DATA / 'historical-universe-builder-h1-2008.json'
OUT = DATA / 'h1-2008-downstream-period-extension-validation.json'

SOURCE_SHA = '31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc'
SOURCE_ARTIFACT_ID = 10088832684
HOLDINGS_RUN_ID = 34320051180
HOLDINGS_ARTIFACT_ID = 10091627801
MAPPING_RUN_ID = 34320498530
MAPPING_ARTIFACT_ID = 10091673514
NPX_RUN_ID = 34320224950
NPX_ARTIFACT_ID = 10091573844
EXPECTED = [
    ('2008-01','2008-01-31'),('2008-02','2008-02-29'),('2008-03','2008-03-31'),
    ('2008-04','2008-04-30'),('2008-05','2008-05-30'),('2008-06','2008-06-30'),
]
ALLOWED_MAPPING_METHODS = {'BASELINE_EXACT','BASELINE_ADR_BASE_UNIQUE','STRUCTURAL_SUFFIX_EXACT','UNIQUE_LONG_PREFIX'}


def evidence_dates(snapshot: dict):
    for filing in snapshot.get('sourceFilings', []):
        for holding in filing.get('holdings', []):
            if holding.get('legacyAssetSection') != 'COMMON_EQUITY' or holding.get('mappingStatus') != 'MATCHED_UNIQUE':
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
    mapping = json.loads(MAPPING.read_text())
    country = json.loads(COUNTRY.read_text())
    diagnostic = json.loads(DIAGNOSTIC.read_text())
    builder = json.loads(BUILDER.read_text())
    checks: dict[str,bool] = {}

    checks['mappingLineageFrozen'] = (
        mapping.get('sourceCatalogArtifactId') == SOURCE_ARTIFACT_ID
        and mapping.get('sourceCatalogSha256') == SOURCE_SHA
        and mapping.get('holdingsRunId') == HOLDINGS_RUN_ID
        and mapping.get('holdingsArtifactId') == HOLDINGS_ARTIFACT_ID
        and mapping.get('npxPitRunId') == NPX_RUN_ID
        and mapping.get('npxPitArtifactId') == NPX_ARTIFACT_ID
        and mapping.get('npxBaseArtifactId') == 10041975282
        and mapping.get('mappingImplementationBlob') == '690479017fc82dce2480ded5d1ffafbb76721722'
        and set(mapping.get('matchMethodCounts',{})).issubset(ALLOWED_MAPPING_METHODS)
    )

    checks['countryLineageFrozen'] = (
        country.get('catalogSha256') == SOURCE_SHA
        and country.get('sourceCatalogArtifactId') == SOURCE_ARTIFACT_ID
        and country.get('sourceCatalogSha256') == SOURCE_SHA
        and country.get('mappingRunId') == MAPPING_RUN_ID
        and country.get('mappingArtifactId') == MAPPING_ARTIFACT_ID
        and country.get('npxPitRunId') == NPX_RUN_ID
        and country.get('npxPitArtifactId') == NPX_ARTIFACT_ID
        and country.get('authoritativeH1CountryRunId') == 34104858455
        and country.get('authoritativeH1CountryArtifactId') == 10012280475
        and country.get('baseCountryEvidenceArtifactId') == 9944538015
        and country.get('structuralCountryEvidenceArtifactId') == 9944797581
        and country.get('periodExtensionMasterYears') == [2005,2006,2007,2008]
    )
    checks['diagnosticLineageFrozen'] = (
        diagnostic.get('catalogSha256') == SOURCE_SHA
        and diagnostic.get('sourceCatalogArtifactId') == SOURCE_ARTIFACT_ID
        and diagnostic.get('sourceCatalogSha256') == SOURCE_SHA
        and diagnostic.get('mappingRunId') == MAPPING_RUN_ID
        and diagnostic.get('mappingArtifactId') == MAPPING_ARTIFACT_ID
        and diagnostic.get('npxPitRunId') == NPX_RUN_ID
        and diagnostic.get('npxPitArtifactId') == NPX_ARTIFACT_ID
    )
    checks['builderCatalogFrozen'] = builder.get('catalogSha256') == SOURCE_SHA
    checks['builderMetadataFrozen'] = (
        builder.get('eligibilityOrder') == 'COMMON_EQUITY -> US -> CORP -> source eligibility'
        and builder.get('sourceEligibility') == 'name exclusions; 10-120 retained holdings; retained total weight >=50; retained top10 weight >=25'
        and builder.get('breadthRule') == 'etfCount>=2 OR maxWeight>=4; score=3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight); Top80'
    )

    map_months=mapping.get('monthSnapshots',[])
    country_months=country.get('monthSnapshots',[])
    diagnostic_months=diagnostic.get('monthSnapshots',[])
    builder_months=builder.get('monthSnapshots',[])
    checks['sixMonthCoverage'] = all(len(rows)==6 for rows in (map_months,country_months,diagnostic_months,builder_months))

    cardinality_ok=True; no_lookahead=True; corp_ok=True; exact_parity=True; rank_ok=True
    monthly=[]
    if checks['sixMonthCoverage']:
        for expected,mapped,resolved,reference,built in zip(EXPECTED,map_months,country_months,diagnostic_months,builder_months):
            month,as_of=expected
            same_period=all(row.get('signalMonth')==month and row.get('asOf')==as_of for row in (mapped,resolved,reference,built))
            source_count=mapped.get('sourceSeriesCount')
            same_counts=(
                isinstance(source_count,int)
                and resolved.get('sourceSeriesCount')==source_count
                and reference.get('sourceSeriesCount')==source_count
                and built.get('sourceSeriesCount')==source_count
                and mapped.get('commonEquityHoldingCount')==resolved.get('commonEquityHoldingCount')
            )
            cardinality_ok = cardinality_ok and same_period and same_counts
            dates=list(evidence_dates(resolved))
            month_no_lookahead=all(d<=as_of for d in dates)
            no_lookahead = no_lookahead and month_no_lookahead
            month_corp_ok=resolved.get('corpPositiveNonCorpNameCount')==0
            corp_ok=corp_ok and month_corp_ok
            month_exact=(
                reference.get('primaryEligibleSourceSeriesCount')==built.get('eligibleSourceSeriesCount')
                and reference.get('primarySymbols')==built.get('symbols')
            )
            exact_parity=exact_parity and month_exact
            symbols=built.get('symbols',[])
            month_rank=(len(symbols)<=80 and [r.get('universeRank') for r in symbols]==list(range(1,len(symbols)+1)))
            rank_ok=rank_ok and month_rank
            monthly.append({
                'signalMonth':month,'asOf':as_of,'sourceSeriesCount':source_count,
                'eligibleSourceSeriesCount':built.get('eligibleSourceSeriesCount'),
                'universeSize':len(symbols),'maxCountryEvidenceDate':max(dates) if dates else None,
                'corpPositiveNonCorpNameCount':resolved.get('corpPositiveNonCorpNameCount'),
                'exactBuilderParity':month_exact,
            })
    else:
        cardinality_ok=no_lookahead=corp_ok=exact_parity=rank_ok=False

    checks['periodCardinalityExact']=cardinality_ok
    checks['countryNoLookahead']=no_lookahead
    checks['corpBridgeMaterialityInvariant']=corp_ok
    checks['frozenBuilderExactParitySixOfSix']=exact_parity
    checks['top80RankInvariant']=rank_ok

    pit=country.get('npxIssuerVariantPitAudit') or {}
    blocked=pit.get('blockedFutureIssuerVariantOccurrencesBySignal') or {}
    checks['npxIssuerVariantPitBounded'] = (
        isinstance(pit.get('incrementalRecordCountInJuneContainer'),int)
        and all(k in {d for _,d in EXPECTED} for k in blocked)
    )

    passed=all(checks.values())
    report={
        'purpose':'H1 2008 downstream period-extension exact-parity validation. Verifies fixed source/holdings/mapping/N-PX/country lineage, strict PIT country no-lookahead, CORP bridge invariance, and exact six-month equality between the frozen historical-Universe builder and the independent frozen primary diagnostic. No strategy outcome is read.',
        'definition':'docs/research/h1-2008-downstream-period-extension-validation-definition.md',
        'sourceCatalogSha256':SOURCE_SHA,
        'checks':checks,'monthly':monthly,'passed':passed,
    }
    OUT.write_text(json.dumps(report,indent=2)+'\n')
    print('H1_2008_DOWNSTREAM_PERIOD_EXTENSION_VALIDATION',json.dumps(report,separators=(',',':')),flush=True)
    if not passed:
        raise SystemExit(2)

if __name__=='__main__': main()
