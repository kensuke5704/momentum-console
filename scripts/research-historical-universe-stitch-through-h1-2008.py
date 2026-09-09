#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
PREFIX=DATA/'historical-universe-builder-through-h2-2007.json'
SUFFIX=DATA/'historical-universe-builder-h1-2008.json'
VALIDATION=DATA/'h1-2008-downstream-period-extension-validation.json'
OUT=DATA/'historical-universe-builder-through-h1-2008.json'

BUILDER_BLOB='1357402f34dfea1c1dbdcaac7de5078b680eb5c3'
PREFIX_RUN_ID=34193003030
PREFIX_ARTIFACT_ID=10042873354
SUFFIX_RUN_ID=34354704856
SUFFIX_ARTIFACT_ID=10105210114
SOURCE_SHA='31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc'


def main()->None:
    prefix=json.loads(PREFIX.read_text())
    suffix=json.loads(SUFFIX.read_text())
    validation=json.loads(VALIDATION.read_text())

    assert prefix.get('builderGitBlob')==BUILDER_BLOB
    assert validation.get('passed') is True
    assert validation.get('sourceCatalogSha256')==SOURCE_SHA
    checks=validation.get('checks',{})
    assert checks.get('parserInvariancePassed') is True
    assert checks.get('mappingLineageFrozen') is True
    assert checks.get('countryLineageFrozen') is True
    assert checks.get('countryNoLookahead') is True
    assert checks.get('corpBridgeMaterialityInvariant') is True
    assert checks.get('frozenBuilderExactParitySixOfSix') is True
    assert checks.get('top80RankInvariant') is True
    assert suffix.get('catalogSha256')==SOURCE_SHA

    prefix_months=prefix.get('monthSnapshots',[])
    suffix_months=suffix.get('monthSnapshots',[])
    expected_prefix=[f'2006-{m:02d}' for m in range(1,13)]+[f'2007-{m:02d}' for m in range(1,13)]
    expected_suffix=[f'2008-{m:02d}' for m in range(1,7)]
    assert [r.get('signalMonth') for r in prefix_months]==expected_prefix
    assert [r.get('signalMonth') for r in suffix_months]==expected_suffix
    assert len(prefix_months)==24 and len(suffix_months)==6

    for key in ('eligibilityOrder','sourceEligibility','breadthRule'):
        assert prefix.get(key)==suffix.get(key),(key,prefix.get(key),suffix.get(key))

    combined=prefix_months+suffix_months
    expected=expected_prefix+expected_suffix
    assert [r.get('signalMonth') for r in combined]==expected
    assert len(combined)==30
    assert len({r.get('signalMonth') for r in combined})==30
    assert all(str(r.get('asOf') or '').startswith(r['signalMonth']) for r in combined)
    assert all(len(r.get('symbols',[]))<=80 for r in combined)

    output={
        'purpose':'Frozen validated historical-Universe stitch through H1 2008. Preserves the closed 24-month 2006-01 through 2007-12 prefix exactly and appends only the independently downstream-validated H1-2008 frozen-builder suffix, without recomputing historical reconstruction or strategy performance.',
        'definition':'docs/research/h1-2008-30-month-stitch-validation-definition.md',
        'builderGitBlob':BUILDER_BLOB,
        'segments':[
            {'period':'2006-01..2007-12','runId':PREFIX_RUN_ID,'artifactId':PREFIX_ARTIFACT_ID,'validation':'closed validated 24-month prefix'},
            {'period':'2008-01..2008-06','runId':SUFFIX_RUN_ID,'artifactId':SUFFIX_ARTIFACT_ID,'sourceCatalogSha256':SOURCE_SHA,'validation':'H1 2008 downstream frozen-builder exact parity'},
        ],
        'eligibilityOrder':prefix.get('eligibilityOrder'),
        'sourceEligibility':prefix.get('sourceEligibility'),
        'breadthRule':prefix.get('breadthRule'),
        'monthSnapshots':combined,
    }
    OUT.write_text(json.dumps(output,indent=2)+'\n')

    reread=json.loads(OUT.read_text())
    rows=reread['monthSnapshots']
    assert rows[:24]==prefix_months
    assert rows[24:]==suffix_months
    print('STITCH_THROUGH_H1_2008',json.dumps({
        'passed':True,
        'months':len(rows),
        'first':rows[0]['signalMonth'],
        'last':rows[-1]['signalMonth'],
        'eligibleSourceSeriesCounts':[r.get('eligibleSourceSeriesCount') for r in rows],
        'universeSizes':[len(r.get('symbols',[])) for r in rows],
    },separators=(',',':')),flush=True)


if __name__=='__main__':
    main()
