#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
IN_DIR=DATA/'id-era-strict-h2-2008-shards'
H1_2008=DATA/'sec-id-era-strict-series-source-h1-2008.json'
OUT=DATA/'sec-id-era-strict-series-source-h2-2008.json'
MONTHS=[
    ('2008-07','2008-07-31'), ('2008-08','2008-08-29'),
    ('2008-09','2008-09-30'), ('2008-10','2008-10-31'),
    ('2008-11','2008-11-28'), ('2008-12','2008-12-31'),
]
PRIOR_SOURCE_ARTIFACTS={
    'h1_2008_strict_series_source':10088832684,
}
H1_2008_CATALOG_SHA256='31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc'


def build_snapshots(months,occ,positives):
    snapshots=[]
    for month,asof in months:
        latest={}
        for r in occ:
            ev=positives.get(r['seriesId'])
            if not ev or ev['evidenceDateFiled']>asof or r['dateFiled']>asof:
                continue
            cur=latest.get(r['seriesId'])
            if cur is None or (r['dateFiled'],r['accession'] or '')>(cur['dateFiled'],cur['accession'] or ''):
                latest[r['seriesId']]=r
        src=sorted(latest.values(),key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or ''))
        snapshots.append({
            'signalMonth':month,
            'asOf':asof,
            'sourceSeriesCount':len(src),
            'sourceFilings':[
                {
                    'seriesId':r['seriesId'],
                    'seriesName':r['seriesName'],
                    'cik':r['cik'],
                    'registrant':r['company'],
                    'form':r['form'],
                    'filingDate':r['dateFiled'],
                    'accession':r['accession'],
                    'filename':r['filename'],
                    'evidenceDateFiled':positives[r['seriesId']]['evidenceDateFiled'],
                    'binding':positives[r['seriesId']]['binding'],
                }
                for r in src
            ],
        })
    return snapshots


def main():
    h1_2008=json.loads(H1_2008.read_text())

    paths=sorted(IN_DIR.glob('sec-id-era-strict-series-source-h2-2008-shard-*.json'))
    if len(paths)!=4:
        raise RuntimeError(f'expected 4 shards, got {len(paths)}')
    shards=[json.loads(p.read_text()) for p in paths]
    assigned=[c for s in shards for c in s['assignedCiks']]
    if len(assigned)!=len(set(assigned)):
        raise RuntimeError('duplicate assigned CIK across shards')

    positives={}; conflicts=[]
    for s in shards:
        for r in s['positiveSeries']:
            old=positives.get(r['seriesId'])
            if old and (old['cik'],old['seriesName'])!=(r['cik'],r['seriesName']):
                conflicts.append({'seriesId':r['seriesId'],'left':old,'right':r})
            if old is None or (r['evidenceDateFiled'],r['evidenceFilename'])<(old['evidenceDateFiled'],old['evidenceFilename']):
                positives[r['seriesId']]=r

    occurrences={}
    for s in shards:
        for r in s['sourceOccurrences']:
            occurrences[(r['seriesId'],r['accession'])]=r
    occ=list(occurrences.values())

    # The 30-month 2006-01 through 2008-06 prefix is closed. Replay it
    # verbatim from the authoritative H1-2008 catalog.
    closed=list(h1_2008.get('closedHistoryReplaySnapshots',[]))+list(h1_2008.get('monthSnapshots',[]))
    closed_months=[x.get('signalMonth') for x in closed]
    expected_closed=[f'2006-{m:02d}' for m in range(1,13)]+[f'2007-{m:02d}' for m in range(1,13)]+[f'2008-{m:02d}' for m in range(1,7)]
    if closed_months!=expected_closed:
        raise RuntimeError(f'authoritative closed source lineage is not exactly 2006-01..2008-06: {closed_months}')

    snapshots=build_snapshots(MONTHS,occ,positives)
    binding=Counter(r['binding'] for r in positives.values())
    source_forms=Counter(r['form'] for r in occ)
    out={
        'purpose':(
            'Merged post-2006-02-06 strict Series-ID ETF source catalog through H2 2008 using the frozen H1-2008 '
            'strict Series-source semantics. The full 2006-01 through 2008-06 closed source prefix is replayed verbatim '
            'from the authoritative H1-2008 catalog rather than recomputed from the expanded H2-2008 candidate set. Jul-Dec 2008 uses the latest public complete-portfolio '
            'source per accepted Series subject to both source filing and issuer-own ETF operational evidence being public '
            'by the signal date. No holdings outcomes, ranks, returns, or strategy results are used.'
        ),
        'seriesIdMandatoryDate':'2006-02-06',
        'priorSourceArtifacts':PRIOR_SOURCE_ARTIFACTS,
        'h1_2008CatalogSha256':H1_2008_CATALOG_SHA256,
        'shardCount':len(shards),
        'candidateRegistrantCount':len(set(assigned)),
        'positiveSeriesCount':len(positives),
        'bindingCounts':dict(sorted(binding.items())),
        'sourceOccurrenceCount':len(occ),
        'sourceFormCounts':dict(sorted(source_forms.items())),
        'seriesIdentityConflictCount':len(conflicts),
        'seriesIdentityConflicts':conflicts,
        'positiveSeries':sorted(positives.values(),key=lambda r:r['seriesId']),
        'sourceOccurrences':sorted(occ,key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or '')),
        'closedHistoryReplaySnapshots':closed,
        'monthSnapshots':snapshots,
        'prospectusErrorCount':sum(s['prospectusErrorCount'] for s in shards),
        'sourceErrorCount':sum(s['sourceErrorCount'] for s in shards),
        'sourceNoScheduleCount':sum(s['sourceNoScheduleCount'] for s in shards),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('seriesIdentityConflicts','positiveSeries','sourceOccurrences','closedHistoryReplaySnapshots','monthSnapshots')}),flush=True)
    for s in closed:
        print('CLOSED_REPLAY_MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
    for s in snapshots:
        print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)


if __name__=='__main__':
    main()
