#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, os, re, time
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('cur',ROOT/'scripts'/'research-sec-us-attribution-current-ticker-sample-2006.py')
cur=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(cur)
old=cur.old
MAPPING=ROOT/'data/research/nq-npx-mapping-2006.json'
SHARD_INDEX=int(os.environ['SHARD_INDEX']); SHARD_COUNT=int(os.environ['SHARD_COUNT'])
OUT=ROOT/f'data/research/sec-us-attribution-full-shard-{SHARD_INDEX:02d}-of-{SHARD_COUNT:02d}-2006.json'
ADR_RE=re.compile(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',re.I)

def direct_structural(row):
    sid=(row.get('securityId') or '').strip().upper()
    if sid and sid[0].isalpha():
        return {**row,'classification':'NON_US','resolutionSource':'CINS_ALPHA_PREFIX'}
    if ADR_RE.search(row.get('issuer') or ''):
        return {**row,'classification':'NON_US','resolutionSource':'EXPLICIT_ADR_GDR'}
    return None

def build_population(mapping):
    ids={}
    for d in mapping.get('details',[]):
        if d.get('status')!='MATCHED_UNIQUE' or len(d.get('identities',[]))!=1: continue
        ident=d['identities'][0]; key=(ident['ticker'],ident['securityId'])
        rec=ids.get(key)
        if rec is None:
            rec={'ticker':ident['ticker'],'securityId':ident['securityId'],'issuer':d['description'],'asOfReportDate':d['reportDate'],'aggregateWeight':0.0,'occurrenceCount':0,'seriesIds':[],'issuerVariants':[]}
            ids[key]=rec
        rec['aggregateWeight']+=float(d.get('weight') or 0); rec['occurrenceCount']+=1
        if d.get('seriesId') and d['seriesId'] not in rec['seriesIds']: rec['seriesIds'].append(d['seriesId'])
        if d.get('description') and d['description'] not in rec['issuerVariants']: rec['issuerVariants'].append(d['description'])
        if d['reportDate']<rec['asOfReportDate']:
            rec['asOfReportDate']=d['reportDate']; rec['issuer']=d['description']
    return sorted(ids.values(),key=lambda x:(x['ticker'],x['securityId'],x['issuer']))

def main():
    mapping=json.loads(MAPPING.read_text()); pop=build_population(mapping)
    shard=[r for i,r in enumerate(pop) if i%SHARD_COUNT==SHARD_INDEX]
    results=[]
    for i,row in enumerate(shard,1):
        r=direct_structural(row)
        if r is None: r=cur.resolve(row)
        results.append(r)
        print(f'{i}/{len(shard)}',json.dumps({k:r.get(k) for k in ['ticker','securityId','issuer','aggregateWeight','classification','resolutionSource','stateCode']}),flush=True)
        time.sleep(.08)
    counts={k:sum(1 for r in results if r.get('classification')==k) for k in ['US','NON_US','UNKNOWN']}
    weights={k:sum(float(r.get('aggregateWeight') or 0) for r in results if r.get('classification')==k) for k in ['US','NON_US','UNKNOWN']}
    out={'year':2006,'purpose':'Shard of full deterministic PIT country attribution over all uniquely mapped EC identities. Current ticker metadata may seed CIK only; classification requires CINS/explicit ADR-GDR or historical filing evidence. UNKNOWN is preserved. No returns/ranks used.','shardIndex':SHARD_INDEX,'shardCount':SHARD_COUNT,'populationCount':len(pop),'shardIdentityCount':len(shard),'classificationCounts':counts,'classificationWeights':weights,'results':results}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
