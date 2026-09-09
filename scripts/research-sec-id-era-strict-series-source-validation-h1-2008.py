#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
PRIOR=DATA/'sec-id-era-strict-series-source-h2-2007.json'
CURRENT=DATA/'sec-id-era-strict-series-source-h1-2008.json'
OUT=DATA/'sec-id-era-strict-series-source-h1-2008-validation.json'
DEFINITION='docs/research/h1-2008-source-period-extension-validation-definition.md'
EXPECTED=[
    ('2008-01','2008-01-31'),('2008-02','2008-02-29'),('2008-03','2008-03-31'),
    ('2008-04','2008-04-30'),('2008-05','2008-05-30'),('2008-06','2008-06-30'),
]


def main():
    prior=json.loads(PRIOR.read_text())
    cur=json.loads(CURRENT.read_text())
    checks={}
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

    prior_pos={x['seriesId']:x for x in prior.get('positiveSeries',[])}
    cur_pos={x['seriesId']:x for x in cur.get('positiveSeries',[])}
    missing=sorted(set(prior_pos)-set(cur_pos))
    identity_fields=('cik','registrant','seriesId','seriesName','classes','binding')
    identity_mismatches=[]
    for sid,p in prior_pos.items():
        c=cur_pos.get(sid)
        if not c: continue
        diffs={k:{'prior':p.get(k),'current':c.get(k)} for k in identity_fields if p.get(k)!=c.get(k)}
        if diffs: identity_mismatches.append({'seriesId':sid,'differences':diffs})
    checks['allPriorPositiveSeriesRetained']=not missing
    checks['priorSeriesIdentityBindingExact']=not identity_mismatches

    prior_closed=list(prior.get('closedHistoryReplaySnapshots',[]))+list(prior.get('monthSnapshots',[]))
    replay=cur.get('closedHistoryReplaySnapshots',[])
    checks['exactAuthoritativeClosedSnapshotReplay']=replay==prior_closed
    checks['closedReplayNoH1Leakage']=all(
        f.get('filingDate','')<=m.get('asOf','') and f.get('evidenceDateFiled','')<=m.get('asOf','')
        for m in replay for f in m.get('sourceFilings',[])
    )

    occ=cur.get('sourceOccurrences',[])
    checks['sourceOccurrencesHaveSeriesAndAccession']=all(o.get('seriesId') and o.get('accession') for o in occ)
    checks['priorArtifactBound']=cur.get('priorSourceArtifactId')==10041257985

    passed=all(checks.values())
    out={
        'purpose':'Pre-defined H1 2008 strict-Series-source period-extension validation. No Stage21 strategy outcomes are read.',
        'definition':DEFINITION,
        'checks':checks,
        'priorPositiveSeriesCount':len(prior_pos),
        'currentPositiveSeriesCount':len(cur_pos),
        'missingPriorSeries':missing,
        'identityBindingMismatches':identity_mismatches,
        'closedReplayMonthCount':len(replay),
        'sourceNoScheduleCount':cur.get('sourceNoScheduleCount'),
        'monthly':[{'signalMonth':x.get('signalMonth'),'asOf':x.get('asOf'),'sourceSeriesCount':x.get('sourceSeriesCount')} for x in months],
        'passed':passed,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('H1_2008_SOURCE_VALIDATION',json.dumps(out,separators=(',',':')),flush=True)
    if not passed: raise SystemExit(1)


if __name__=='__main__':main()
