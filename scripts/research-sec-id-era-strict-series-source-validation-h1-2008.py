#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
H1_2006=DATA/'sec-hybrid-etf-source-catalog-h1-2006.json'
H2_2006=DATA/'sec-id-era-strict-series-source-h2-2006.json'
H2_2007=DATA/'sec-id-era-strict-series-source-h2-2007.json'
CURRENT=DATA/'sec-id-era-strict-series-source-h1-2008.json'
OUT=DATA/'sec-id-era-strict-series-source-h1-2008-validation.json'
DEFINITION='docs/research/h1-2008-source-period-extension-validation-definition.md'
EXPECTED=[
    ('2008-01','2008-01-31'),('2008-02','2008-02-29'),('2008-03','2008-03-31'),
    ('2008-04','2008-04-30'),('2008-05','2008-05-30'),('2008-06','2008-06-30'),
]
EXPECTED_CLOSED_MONTHS=[f'2006-{m:02d}' for m in range(1,13)]+[f'2007-{m:02d}' for m in range(1,13)]
EXPECTED_H1_2006_SHA='e2405277fe03a4208e163a43d724fd7364e139ad229caa70251b151f1d53b801'
EXPECTED_H2_2007_SHA='9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631'
EXPECTED_ARTIFACTS={
    'h1_2006_hybrid_source_and_holdings':10006530879,
    'h2_2006_strict_series_source':10038284691,
    'h2_2007_strict_series_source':10041257985,
}


def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    h1_2006=json.loads(H1_2006.read_text())
    h2_2006=json.loads(H2_2006.read_text())
    h2_2007=json.loads(H2_2007.read_text())
    cur=json.loads(CURRENT.read_text())
    checks={}

    # Frozen authoritative lineage checks happen before evaluating any new H1-2008 source snapshot.
    checks['h1_2006CatalogShaExact']=sha256(H1_2006)==EXPECTED_H1_2006_SHA
    checks['h2_2007CatalogShaExact']=sha256(H2_2007)==EXPECTED_H2_2007_SHA
    checks['priorArtifactsExact']=cur.get('priorSourceArtifacts')==EXPECTED_ARTIFACTS
    checks['identityConflictsZero']=cur.get('seriesIdentityConflictCount')==0
    checks['prospectusErrorsZero']=cur.get('prospectusErrorCount')==0
    checks['sourceErrorsZero']=cur.get('sourceErrorCount')==0

    months=cur.get('monthSnapshots',[])
    checks['exactH1Schedule']=[(x.get('signalMonth'),x.get('asOf')) for x in months]==EXPECTED
    checks['sixMonthCoverage']=len(months)==6
    checks['h1NoLookahead']=all(
        f.get('filingDate','')<=m.get('asOf','') and f.get('evidenceDateFiled','')<=m.get('asOf','')
        for m in months for f in m.get('sourceFilings',[])
    )

    prior_pos={x['seriesId']:x for x in h2_2007.get('positiveSeries',[])}
    cur_pos={x['seriesId']:x for x in cur.get('positiveSeries',[])}
    missing=sorted(set(prior_pos)-set(cur_pos))
    identity_fields=('cik','registrant','seriesId','seriesName','classes','binding')
    identity_mismatches=[]
    for sid,p in prior_pos.items():
        c=cur_pos.get(sid)
        if not c:
            continue
        diffs={k:{'prior':p.get(k),'current':c.get(k)} for k in identity_fields if p.get(k)!=c.get(k)}
        if diffs:
            identity_mismatches.append({'seriesId':sid,'differences':diffs})
    checks['allPriorPositiveSeriesRetained']=not missing
    checks['priorSeriesIdentityBindingExact']=not identity_mismatches

    authoritative_closed=(
        list(h1_2006.get('monthSnapshots',[]))
        + list(h2_2006.get('monthSnapshots',[]))
        + list(h2_2007.get('closedHistoryReplaySnapshots',[]))
        + list(h2_2007.get('monthSnapshots',[]))
    )
    replay=cur.get('closedHistoryReplaySnapshots',[])
    authoritative_months=[x.get('signalMonth') for x in authoritative_closed]
    replay_months=[x.get('signalMonth') for x in replay]
    checks['authoritativeClosedScheduleIs24Months']=authoritative_months==EXPECTED_CLOSED_MONTHS
    checks['closedReplayScheduleIs24Months']=replay_months==EXPECTED_CLOSED_MONTHS
    checks['exactAuthoritativeClosedSnapshotReplay']=replay==authoritative_closed
    checks['exactAuthoritativeClosedSourceFilings']=len(replay)==24 and all(
        replay[i].get('sourceFilings')==authoritative_closed[i].get('sourceFilings')
        for i in range(24)
    )
    checks['closedReplayNoH1Leakage']=all(
        f.get('filingDate','')<=m.get('asOf','') and f.get('evidenceDateFiled','')<=m.get('asOf','')
        for m in replay for f in m.get('sourceFilings',[])
    )

    occ=cur.get('sourceOccurrences',[])
    checks['sourceOccurrencesHaveSeriesAndAccession']=all(o.get('seriesId') and o.get('accession') for o in occ)

    passed=all(checks.values())
    out={
        'purpose':'Pre-defined H1 2008 strict-Series-source period-extension validation. No Stage21 strategy outcomes are read.',
        'definition':DEFINITION,
        'checks':checks,
        'priorSourceArtifacts':EXPECTED_ARTIFACTS,
        'h1_2006CatalogSha256':sha256(H1_2006),
        'h2_2007CatalogSha256':sha256(H2_2007),
        'priorPositiveSeriesCount':len(prior_pos),
        'currentPositiveSeriesCount':len(cur_pos),
        'missingPriorSeries':missing,
        'identityBindingMismatches':identity_mismatches,
        'closedReplayMonthCount':len(replay),
        'closedReplayMonths':replay_months,
        'sourceNoScheduleCount':cur.get('sourceNoScheduleCount'),
        'monthly':[{'signalMonth':x.get('signalMonth'),'asOf':x.get('asOf'),'sourceSeriesCount':x.get('sourceSeriesCount')} for x in months],
        'passed':passed,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('H1_2008_SOURCE_VALIDATION',json.dumps(out,separators=(',',':')),flush=True)
    if not passed:
        raise SystemExit(1)


if __name__=='__main__':
    main()
