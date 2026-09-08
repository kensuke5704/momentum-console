#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'data/research'
H1=DIR/'sec-id-era-strict-series-source-h1-2006.json'
H2=DIR/'sec-id-era-strict-series-source-h2-2006.json'
OUT=DIR/'sec-id-era-strict-series-source-h2-2006-validation.json'
H1_MONTHS=[('2006-02','2006-02-28'),('2006-03','2006-03-31'),('2006-04','2006-04-28'),('2006-05','2006-05-31'),('2006-06','2006-06-30')]
H2_MONTHS=[('2006-07','2006-07-31'),('2006-08','2006-08-31'),('2006-09','2006-09-29'),('2006-10','2006-10-31'),('2006-11','2006-11-30'),('2006-12','2006-12-29')]
ETF_CLASS=re.compile(r'\b(?:ETF\s+SHARES?|VIPER(?:\s+SHARES?)?|EXCHANGE[- ]TRADED(?:\s+SHARES?)?)\b',re.I)


def snapshot_from_catalog(cat, month, asof):
    positives={r['seriesId']:r for r in cat['positiveSeries']}
    latest={}
    for r in cat['sourceOccurrences']:
        ev=positives.get(r['seriesId'])
        if not ev or ev['evidenceDateFiled']>asof or r['dateFiled']>asof:
            continue
        cur=latest.get(r['seriesId'])
        if cur is None or (r['dateFiled'],r.get('accession') or '')>(cur['dateFiled'],cur.get('accession') or ''):
            latest[r['seriesId']]=r
    src=sorted(latest.values(),key=lambda r:(r['seriesId'],r['dateFiled'],r.get('accession') or ''))
    return {
        'signalMonth':month,
        'asOf':asof,
        'sourceSeriesCount':len(src),
        'sourceFilings':[
            {
                'seriesId':r['seriesId'],'seriesName':r['seriesName'],'cik':r['cik'],'registrant':r['company'],
                'form':r['form'],'filingDate':r['dateFiled'],'accession':r['accession'],'filename':r['filename'],
                'evidenceDateFiled':positives[r['seriesId']]['evidenceDateFiled'],'binding':positives[r['seriesId']]['binding']
            } for r in src
        ],
    }


def identity_key(r):
    return {
        k:r.get(k) for k in (
            'cik','registrant','seriesId','seriesName','classes','seriesMetadataFirstDate',
            'evidenceDateFiled','evidenceForm','evidenceFilename','binding'
        )
    }


def main():
    h1=json.loads(H1.read_text());h2=json.loads(H2.read_text())
    checks=[]
    def check(name, passed, detail=None):
        checks.append({'name':name,'passed':bool(passed),'detail':detail})

    check('h2_series_identity_conflicts_zero',h2.get('seriesIdentityConflictCount')==0,h2.get('seriesIdentityConflictCount'))
    check('h2_prospectus_errors_zero',h2.get('prospectusErrorCount')==0,h2.get('prospectusErrorCount'))
    check('h2_source_errors_zero',h2.get('sourceErrorCount')==0,h2.get('sourceErrorCount'))
    check('h2_month_schedule_exact',[(x['signalMonth'],x['asOf']) for x in h2['monthSnapshots']]==H2_MONTHS,[(x['signalMonth'],x['asOf']) for x in h2['monthSnapshots']])
    counts=[x['sourceSeriesCount'] for x in h2['monthSnapshots']]
    check('h2_source_counts_nondecreasing',counts==sorted(counts),counts)

    h1_by={r['seriesId']:r for r in h1['positiveSeries']};h2_by={r['seriesId']:r for r in h2['positiveSeries']}
    missing=sorted(set(h1_by)-set(h2_by))
    drift=[]
    for sid in sorted(set(h1_by)&set(h2_by)):
        if identity_key(h1_by[sid])!=identity_key(h2_by[sid]):
            drift.append({'seriesId':sid,'h1':identity_key(h1_by[sid]),'h2':identity_key(h2_by[sid])})
    check('h1_positive_series_all_retained',not missing,missing)
    check('h1_positive_series_identity_binding_exact',not drift,drift[:20])

    rebuilt=[snapshot_from_catalog(h2,m,a) for m,a in H1_MONTHS]
    h1_snap=[x for x in h1['monthSnapshots'] if (x['signalMonth'],x['asOf']) in H1_MONTHS]
    retro=[]
    for left,right in zip(h1_snap,rebuilt):
        if left!=right:
            retro.append({
                'signalMonth':left['signalMonth'],
                'h1Count':left['sourceSeriesCount'],'rebuiltFromH2Count':right['sourceSeriesCount'],
                'addedSeriesIds':sorted({x['seriesId'] for x in right['sourceFilings']}-{x['seriesId'] for x in left['sourceFilings']}),
                'missingSeriesIds':sorted({x['seriesId'] for x in left['sourceFilings']}-{x['seriesId'] for x in right['sourceFilings']}),
            })
    check('h1_snapshots_reproduced_exactly_from_h2_catalog',not retro,retro)

    h1_ids=set(h1_by)
    new_vanguard=[]
    bad_vanguard=[]
    for r in h2['positiveSeries']:
        if r['seriesId'] in h1_ids: continue
        text=((r.get('registrant') or '')+' '+(r.get('seriesName') or '')).upper()
        if 'VANGUARD' not in text: continue
        new_vanguard.append(r['seriesId'])
        explicit=any(ETF_CLASS.search(c.get('className') or '') for c in r.get('classes',[]))
        if r.get('binding')!='EXPLICIT_ETF_CLASS_METADATA' or not explicit:
            bad_vanguard.append(identity_key(r))
    check('new_vanguard_series_require_explicit_etf_class_metadata',not bad_vanguard,{'newVanguardSeriesIds':new_vanguard,'bad':bad_vanguard})

    passed=all(x['passed'] for x in checks)
    out={
        'purpose':'Period-extension invariant validation for the strict post-ID H2 2006 source catalog. This validates source/identity causality only and does not inspect holdings, ranks, returns, or strategy outcomes.',
        'passed':passed,
        'h1PositiveSeriesCount':h1.get('positiveSeriesCount'),
        'h2PositiveSeriesCount':h2.get('positiveSeriesCount'),
        'h2SourceOccurrenceCount':h2.get('sourceOccurrenceCount'),
        'h2MonthSourceCounts':counts,
        'checks':checks,
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('VALIDATION',json.dumps(out,indent=2),flush=True)
    if not passed:
        raise SystemExit(2)


if __name__=='__main__':main()
