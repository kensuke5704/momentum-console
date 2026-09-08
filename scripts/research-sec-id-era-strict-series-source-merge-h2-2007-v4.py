#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/research'
IN_DIR=DATA/'id-era-strict-h2-2007-shards'
H1_PREF=DATA/'sec-etf-registrant-operational-prefilter-through-h1-2007.json'
OUT=DATA/'sec-id-era-strict-series-source-h2-2007.json'
REPLAY_MONTHS=[('2007-01','2007-01-31'),('2007-02','2007-02-28'),('2007-03','2007-03-30'),('2007-04','2007-04-30'),('2007-05','2007-05-31'),('2007-06','2007-06-29')]
MONTHS=[('2007-07','2007-07-31'),('2007-08','2007-08-31'),('2007-09','2007-09-28'),('2007-10','2007-10-31'),('2007-11','2007-11-30'),('2007-12','2007-12-31')]
H1_PREF_ARTIFACT_ID=10039881783
DIAGNOSTIC_RUN_ID=34188080894
DIAGNOSTIC_ARTIFACT_ID=10041208253


def build_snapshots(months,occ,positives,allowed_ciks=None):
    snapshots=[]
    for month,asof in months:
        latest={}
        for r in occ:
            if allowed_ciks is not None and r['cik'] not in allowed_ciks:
                continue
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
    paths=sorted(IN_DIR.glob('sec-id-era-strict-series-source-h2-2007-shard-*.json'))
    if len(paths)!=4:
        raise RuntimeError(f'expected 4 shards, got {len(paths)}')
    shards=[json.loads(p.read_text()) for p in paths]
    assigned=[c for s in shards for c in s['assignedCiks']]
    if len(assigned)!=len(set(assigned)):
        raise RuntimeError('duplicate assigned CIK across shards')

    h1_pref=json.loads(H1_PREF.read_text())
    closed_candidate_ciks=set(h1_pref['positiveCiks'])
    if len(closed_candidate_ciks)!=h1_pref['positiveCandidateRegistrantCount']:
        raise RuntimeError('H1 candidate-review cardinality mismatch')
    if not closed_candidate_ciks <= set(assigned):
        raise RuntimeError('authoritative H1 candidate CIK missing from cumulative H2 shard assignment')

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

    # Closed-history replay uses only the candidate-review set that was PIT-discovered
    # and frozen in the authoritative H1 2007 reconstruction. CIKs first discovered
    # in H2 may enter only the new Jul-Dec period; final Series evidence rules are unchanged.
    replay=build_snapshots(REPLAY_MONTHS,occ,positives,allowed_ciks=closed_candidate_ciks)
    snapshots=build_snapshots(MONTHS,occ,positives)

    binding=Counter(r['binding'] for r in positives.values())
    source_forms=Counter(r['form'] for r in occ)
    new_candidate_ciks=sorted(set(assigned)-closed_candidate_ciks)
    out={
        'purpose':(
            'Merged post-2006-02-06 strict Series-ID ETF source catalog through H2 2007 using the frozen H1-2007 '
            'strict Series-source semantics plus the explicitly documented closed-history candidate-discovery boundary. '
            'Closed Jan-Jun replay admits only CIKs present in the authoritative H1 candidate-review set; Jul-Dec uses '
            'the cumulative H2 candidate set. Final issuer-own evidence, Series structural binding, complete-portfolio, '
            'and no-lookahead rules are unchanged. No holdings outcomes, ranks, returns, or strategy results are used.'
        ),
        'seriesIdMandatoryDate':'2006-02-06',
        'shardCount':len(shards),
        'candidateRegistrantCount':len(set(assigned)),
        'closedHistoryCandidateReviewArtifactId':H1_PREF_ARTIFACT_ID,
        'closedHistoryCandidateReviewRegistrantCount':len(closed_candidate_ciks),
        'closedHistoryDiscoveryBoundaryApplied':True,
        'newPeriodCandidateRegistrantCount':len(new_candidate_ciks),
        'newPeriodCandidateCiks':new_candidate_ciks,
        'boundaryDiagnosticRunId':DIAGNOSTIC_RUN_ID,
        'boundaryDiagnosticArtifactId':DIAGNOSTIC_ARTIFACT_ID,
        'positiveSeriesCount':len(positives),
        'bindingCounts':dict(sorted(binding.items())),
        'sourceOccurrenceCount':len(occ),
        'sourceFormCounts':dict(sorted(source_forms.items())),
        'seriesIdentityConflictCount':len(conflicts),
        'seriesIdentityConflicts':conflicts,
        'positiveSeries':sorted(positives.values(),key=lambda r:r['seriesId']),
        'sourceOccurrences':sorted(occ,key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or '')),
        'closedHistoryReplaySnapshots':replay,
        'monthSnapshots':snapshots,
        'prospectusErrorCount':sum(s['prospectusErrorCount'] for s in shards),
        'sourceErrorCount':sum(s['sourceErrorCount'] for s in shards),
        'sourceNoScheduleCount':sum(s['sourceNoScheduleCount'] for s in shards),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in (
        'seriesIdentityConflicts','positiveSeries','sourceOccurrences','closedHistoryReplaySnapshots','monthSnapshots','newPeriodCandidateCiks'
    )}),flush=True)
    for s in replay:
        print('REPLAY_MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
    for s in snapshots:
        print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)


if __name__=='__main__':
    main()
