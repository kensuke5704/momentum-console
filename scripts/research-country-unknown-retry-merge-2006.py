#!/usr/bin/env python3
from __future__ import annotations
import json, glob
from pathlib import Path
from collections import Counter, defaultdict
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/research/country-full-coverage-2006.json'
MAP=ROOT/'data/research/nq-npx-mapping-2006.json'
OUT=ROOT/'data/research/country-full-coverage-unknown-retry-2006.json'

def key(r): return (r.get('ticker'),r.get('securityId'))

def main():
    base=json.loads(BASE.read_text()); mapping=json.loads(MAP.read_text())
    retries=[]
    for p in sorted(glob.glob(str(ROOT/'data/research/sec-us-attribution-unknown-retry-*-2006.json'))):
        retries += json.loads(Path(p).read_text()).get('results',[])
    retry_by={key(r):r for r in retries if r.get('classification') in {'US','NON_US'}}
    # Reconstruct original identity classifications from retry inputs when present, else retry rows include original fields.
    # The merge artifact's identity rows are stored under identityRows if available; otherwise derive from retry originals plus unresolved base aggregate is not enough.
    identity_rows=[]
    for p in sorted(glob.glob(str(ROOT/'data/research/sec-us-attribution-full-shard-*-2006.json'))):
        identity_rows += json.loads(Path(p).read_text()).get('results',[])
    merged=[]
    for r in identity_rows:
        rr=dict(r)
        if rr.get('classification')=='UNKNOWN' and key(rr) in retry_by:
            nr=retry_by[key(rr)]
            for f in ['classification','resolutionSource','stateCode','filingUrl','resolvedCik']:
                if nr.get(f) is not None: rr[f]=nr.get(f)
            rr['retryResolved']=True
        merged.append(rr)
    byid={key(r):r for r in merged}
    counts=Counter(); weights=defaultdict(float)
    mapped_counts=Counter(); mapped_weights=defaultdict(float)
    all_counts=Counter(); all_weights=defaultdict(float)
    for r in merged:
        c=r.get('classification','UNKNOWN'); counts[c]+=1; weights[c]+=float(r.get('aggregateWeight') or 0)
    for d in mapping.get('details',[]):
        w=float(d.get('weight') or 0)
        if d.get('status')=='MATCHED_UNIQUE' and len(d.get('identities',[]))==1:
            ident=d['identities'][0]; c=byid.get((ident.get('ticker'),ident.get('securityId')),{}).get('classification','UNKNOWN')
        elif d.get('status')!='PARSER_ARTIFACT' and __import__('re').search(r'\b(?:ADR|GDR|AMERICAN DEPOSITARY|GLOBAL DEPOSITARY)\b',d.get('description') or '',__import__('re').I): c='NON_US'
        else: c='UNKNOWN'
        if d.get('status')=='MATCHED_UNIQUE': mapped_counts[c]+=1; mapped_weights[c]+=w
        all_counts[c]+=1; all_weights[c]+=w
    mapped_total=sum(mapped_counts.values()); mapped_w=sum(mapped_weights.values()); all_total=sum(all_counts.values()); all_w=sum(all_weights.values())
    resolved_retry=sum(1 for r in merged if r.get('retryResolved'))
    out={
      'year':2006,'purpose':'Merge UNKNOWN-only retry results into frozen full PIT country attribution. Existing US/NON_US classifications are unchanged; UNKNOWN remains conservative.',
      'retryResolvedIdentityCount':resolved_retry,
      'identityClassificationCounts':dict(counts),'identityClassificationWeights':dict(weights),
      'mappedHoldingClassificationCounts':dict(mapped_counts),'mappedHoldingClassificationWeights':dict(mapped_weights),
      'mappedHoldingResolvedCountRate':(mapped_counts['US']+mapped_counts['NON_US'])/mapped_total if mapped_total else 0,
      'mappedHoldingResolvedWeightRate':(mapped_weights['US']+mapped_weights['NON_US'])/mapped_w if mapped_w else 0,
      'allEcHoldingClassificationCounts':dict(all_counts),'allEcHoldingClassificationWeights':dict(all_weights),
      'allEcResolvedCountRate':(all_counts['US']+all_counts['NON_US'])/all_total if all_total else 0,
      'allEcResolvedWeightRate':(all_weights['US']+all_weights['NON_US'])/all_w if all_w else 0,
      'identityRows':merged
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print('SUMMARY',json.dumps({k:v for k,v in out.items() if k!='identityRows'}),flush=True)
if __name__=='__main__': main()
