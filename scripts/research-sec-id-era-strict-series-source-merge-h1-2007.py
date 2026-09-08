#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IN_DIR=ROOT/'data/research/id-era-strict-h1-2007-shards'
OUT=ROOT/'data/research/sec-id-era-strict-series-source-h1-2007.json'
REPLAY_MONTHS=[('2006-07','2006-07-31'),('2006-08','2006-08-31'),('2006-09','2006-09-29'),('2006-10','2006-10-31'),('2006-11','2006-11-30'),('2006-12','2006-12-29')]
MONTHS=[('2007-01','2007-01-31'),('2007-02','2007-02-28'),('2007-03','2007-03-30'),('2007-04','2007-04-30'),('2007-05','2007-05-31'),('2007-06','2007-06-29')]


def build_snapshots(months,occ,positives):
    snapshots=[]
    for month,asof in months:
        latest={}
        for r in occ:
            ev=positives.get(r['seriesId'])
            if not ev or ev['evidenceDateFiled']>asof or r['dateFiled']>asof: continue
            cur=latest.get(r['seriesId'])
            if cur is None or (r['dateFiled'],r['accession'] or '')>(cur['dateFiled'],cur['accession'] or ''): latest[r['seriesId']]=r
        src=sorted(latest.values(),key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or ''))
        snapshots.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(src),'sourceFilings':[{'seriesId':r['seriesId'],'seriesName':r['seriesName'],'cik':r['cik'],'registrant':r['company'],'form':r['form'],'filingDate':r['dateFiled'],'accession':r['accession'],'filename':r['filename'],'evidenceDateFiled':positives[r['seriesId']]['evidenceDateFiled'],'binding':positives[r['seriesId']]['binding']} for r in src]})
    return snapshots


def main():
    paths=sorted(IN_DIR.glob('sec-id-era-strict-series-source-h1-2007-shard-*.json'))
    if len(paths)!=4: raise RuntimeError(f'expected 4 shards, got {len(paths)}')
    shards=[json.loads(p.read_text()) for p in paths]
    assigned=[c for s in shards for c in s['assignedCiks']]
    if len(assigned)!=len(set(assigned)): raise RuntimeError('duplicate assigned CIK across shards')
    positives={}; conflicts=[]
    for s in shards:
        for r in s['positiveSeries']:
            old=positives.get(r['seriesId'])
            if old and (old['cik'],old['seriesName'])!=(r['cik'],r['seriesName']): conflicts.append({'seriesId':r['seriesId'],'left':old,'right':r})
            if old is None or (r['evidenceDateFiled'],r['evidenceFilename'])<(old['evidenceDateFiled'],old['evidenceFilename']): positives[r['seriesId']]=r
    occurrences={}
    for s in shards:
        for r in s['sourceOccurrences']:
            occurrences[(r['seriesId'],r['accession'])]=r
    occ=list(occurrences.values())
    replay=build_snapshots(REPLAY_MONTHS,occ,positives)
    snapshots=build_snapshots(MONTHS,occ,positives)
    binding=Counter(r['binding'] for r in positives.values()); source_forms=Counter(r['form'] for r in occ)
    out={'purpose':'Merged post-2006-02-06 strict Series-ID ETF source catalog through H1 2007 using the frozen 2006 strict Series-source semantics. The catalog includes explicit closed-history replay snapshots for Jul-Dec 2006 and current Jan-Jun 2007 snapshots. Monthly snapshots use the latest public complete-portfolio source per accepted Series subject to both source filing and issuer-own ETF operational evidence being public by the signal date. No holdings outcomes, ranks, returns, or strategy results are used.','seriesIdMandatoryDate':'2006-02-06','shardCount':len(shards),'candidateRegistrantCount':len(set(assigned)),'positiveSeriesCount':len(positives),'bindingCounts':dict(sorted(binding.items())),'sourceOccurrenceCount':len(occ),'sourceFormCounts':dict(sorted(source_forms.items())),'seriesIdentityConflictCount':len(conflicts),'seriesIdentityConflicts':conflicts,'positiveSeries':sorted(positives.values(),key=lambda r:r['seriesId']),'sourceOccurrences':sorted(occ,key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or '')),'closedHistoryReplaySnapshots':replay,'monthSnapshots':snapshots,'prospectusErrorCount':sum(s['prospectusErrorCount'] for s in shards),'sourceErrorCount':sum(s['sourceErrorCount'] for s in shards),'sourceNoScheduleCount':sum(s['sourceNoScheduleCount'] for s in shards)}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('seriesIdentityConflicts','positiveSeries','sourceOccurrences','closedHistoryReplaySnapshots','monthSnapshots')}),flush=True)
    for s in replay: print('REPLAY_MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
    for s in snapshots: print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
if __name__=='__main__':main()
