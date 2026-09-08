#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
PRIOR=DATA/'sec-id-era-strict-series-source-h1-2007.json'
CURRENT=DATA/'sec-id-era-strict-series-source-h2-2007.json'
OUT=DATA/'sec-id-era-strict-series-source-h2-2007-validation.json'
DEFINITION='docs/research/h2-2007-source-period-extension-validation-definition.md'
EXPECTED=[
    ('2007-07','2007-07-31'),('2007-08','2007-08-31'),('2007-09','2007-09-28'),
    ('2007-10','2007-10-31'),('2007-11','2007-11-30'),('2007-12','2007-12-31'),
]


def main():
    prior=json.loads(PRIOR.read_text())
    cur=json.loads(CURRENT.read_text())
    checks={}

    checks['identityConflictsZero']=cur.get('seriesIdentityConflictCount')==0
    checks['prospectusErrorsZero']=cur.get('prospectusErrorCount')==0
    checks['sourceErrorsZero']=cur.get('sourceErrorCount')==0

    months=cur.get('monthSnapshots',[])
    checks['exactH2Schedule']=[(x.get('signalMonth'),x.get('asOf')) for x in months]==EXPECTED
    checks['sixMonthCoverage']=len(months)==6
    checks['h2NoLookahead']=all(
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

    prior_snaps={x['signalMonth']:x for x in prior.get('monthSnapshots',[])}
    replay=cur.get('closedHistoryReplaySnapshots',[])
    replay_mismatches=[]
    for r in replay:
        p=prior_snaps.get(r.get('signalMonth'))
        if p is None or p.get('asOf')!=r.get('asOf') or p.get('sourceSeriesCount')!=r.get('sourceSeriesCount') or p.get('sourceFilings')!=r.get('sourceFilings'):
            replay_mismatches.append(r.get('signalMonth'))
    expected_replay=['2007-01','2007-02','2007-03','2007-04','2007-05','2007-06']
    checks['exactPriorSnapshotReplay']=[r.get('signalMonth') for r in replay]==expected_replay and not replay_mismatches

    # sourceNoSchedule is audit-only in the frozen shard implementation: sourceOccurrences
    # are emitted only inside the complete-schedule branch. Assert this structurally here.
    occ=cur.get('sourceOccurrences',[])
    checks['sourceOccurrencesHaveSeriesAndAccession']=all(o.get('seriesId') and o.get('accession') for o in occ)

    passed=all(checks.values())
    out={
        'purpose':'Pre-defined H2 2007 strict-Series-source period-extension validation. No Stage21 strategy outcomes are read.',
        'definition':DEFINITION,
        'checks':checks,
        'priorPositiveSeriesCount':len(prior_pos),
        'currentPositiveSeriesCount':len(cur_pos),
        'missingPriorSeries':missing,
        'identityBindingMismatches':identity_mismatches,
        'priorReplayMismatches':replay_mismatches,
        'sourceNoScheduleCount':cur.get('sourceNoScheduleCount'),
        'monthly':[{'signalMonth':x.get('signalMonth'),'asOf':x.get('asOf'),'sourceSeriesCount':x.get('sourceSeriesCount')} for x in months],
        'passed':passed,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('H2_2007_SOURCE_VALIDATION',json.dumps(out,separators=(',',':')),flush=True)
    if not passed: raise SystemExit(1)


if __name__=='__main__':main()
