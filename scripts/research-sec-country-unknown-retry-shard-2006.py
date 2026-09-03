#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data/research/sec-country-evidence-cache-2006.json'
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
IDX=int(os.environ['SHARD_INDEX']); COUNT=int(os.environ['SHARD_COUNT'])
OUT=ROOT/f'data/research/sec-country-unknown-retry-{IDX:02d}-of-{COUNT:02d}-2006.json'
ADR=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)

def classify(row):
    sid=(row.get('securityId') or '').upper(); issuer=row.get('issuer') or ''
    if sid[:1].isalpha(): return {**row,'classification':'NON_US','resolutionSource':'CINS_ALPHA_PREFIX_RETRY'}
    if ADR.search(issuer): return {**row,'classification':'NON_US','resolutionSource':'EXPLICIT_ADR_GDR_RETRY'}
    return cur.resolve({'ticker':row['ticker'],'securityId':row['securityId'],'issuer':issuer,'asOfReportDate':row['asOfReportDate'],'aggregateWeight':row.get('aggregateWeight',0),'occurrenceCount':row.get('occurrenceCount',0)})

def main():
    cache=json.loads(CACHE.read_text())
    pop=sorted((r for r in cache.get('rows',[]) if r.get('classification')=='UNKNOWN'),key=lambda r:(r.get('ticker') or '',r.get('securityId') or ''))
    shard=[r for i,r in enumerate(pop) if i%COUNT==IDX]
    results=[]
    for i,row in enumerate(shard,1):
        r=classify(row);results.append(r)
        print(f'{i}/{len(shard)}',json.dumps({k:r.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','classification','resolutionSource','stateCode']}),flush=True)
        time.sleep(.08)
    out={'year':2006,'purpose':'Deterministic retry of only identities still UNKNOWN in the frozen monotonic PIT country evidence cache. Positive evidence is never overwritten; this run can only add newly recovered PIT evidence. No returns or ranks used.','retryPopulationCount':len(pop),'shardIndex':IDX,'shardCount':COUNT,'shardCountActual':len(shard),'resolvedCount':sum(r.get('classification') in {'US','NON_US'} for r in results),'resolvedWeight':sum(float(r.get('aggregateWeight') or 0) for r in results if r.get('classification') in {'US','NON_US'}),'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
