#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IN_DIR=ROOT/'data/research/id-era-strict-shards'
OUT=ROOT/'data/research/sec-id-era-strict-series-source-h1-2006.json'
MONTHS=[('2006-02','2006-02-28'),('2006-03','2006-03-31'),('2006-04','2006-04-28'),('2006-05','2006-05-31'),('2006-06','2006-06-30')]

def main():
    paths=sorted(IN_DIR.glob('sec-id-era-strict-series-source-h1-2006-shard-*.json'))
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
    snapshots=[]
    for month,asof in MONTHS:
        latest={}
        for r in occ:
            ev=positives.get(r['seriesId'])
            if not ev or ev['evidenceDateFiled']>asof or r['dateFiled']>asof: continue
            cur=latest.get(r['seriesId'])
            if cur is None or (r['dateFiled'],r['accession'] or '')>(cur['dateFiled'],cur['accession'] or ''): latest[r['seriesId']]=r
        src=sorted(latest.values(),key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or ''))
        snapshots.append({'signalMonth':month,'asOf':asof,'sourceSeriesCount':len(src),'sourceFilings':[{'seriesId':r['seriesId'],'seriesName':r['seriesName'],'cik':r['cik'],'registrant':r['company'],'form':r['form'],'filingDate':r['dateFiled'],'accession':r['accession'],'filename':r['filename'],'evidenceDateFiled':positives[r['seriesId']]['evidenceDateFiled'],'binding':positives[r['seriesId']]['binding']} for r in src]})
    binding=Counter(r['binding'] for r in positives.values()); source_forms=Counter(r['form'] for r in occ)
    out={'purpose':'Merged post-2006-02-06 strict Series-ID ETF source catalog. Series-level operational binding only; no trust-global inheritance. Source population includes N-Q/N-CSR/N-CSRS complete-portfolio filings. Monthly snapshots use latest public source per positive Series ID subject to both source filing and ETF operational evidence being public by month end. No holdings outcomes, ranks, returns, or strategy results are used.','seriesIdMandatoryDate':'2006-02-06','shardCount':len(shards),'candidateRegistrantCount':len(set(assigned)),'positiveSeriesCount':len(positives),'bindingCounts':dict(sorted(binding.items())),'sourceOccurrenceCount':len(occ),'sourceFormCounts':dict(sorted(source_forms.items())),'seriesIdentityConflictCount':len(conflicts),'seriesIdentityConflicts':conflicts,'positiveSeries':sorted(positives.values(),key=lambda r:r['seriesId']),'sourceOccurrences':sorted(occ,key=lambda r:(r['seriesId'],r['dateFiled'],r['accession'] or '')),'monthSnapshots':snapshots,'prospectusErrorCount':sum(s['prospectusErrorCount'] for s in shards),'sourceErrorCount':sum(s['sourceErrorCount'] for s in shards),'sourceNoScheduleCount':sum(s['sourceNoScheduleCount'] for s in shards)}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in ('seriesIdentityConflicts','positiveSeries','sourceOccurrences','monthSnapshots')}),flush=True)
    for s in snapshots: print('MONTH',json.dumps({k:s[k] for k in ('signalMonth','asOf','sourceSeriesCount')}),flush=True)
if __name__=='__main__':main()
