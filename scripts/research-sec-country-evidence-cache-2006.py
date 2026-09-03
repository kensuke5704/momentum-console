#!/usr/bin/env python3
from __future__ import annotations
import glob,json
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SAMPLE=ROOT/'data/research/sec-us-attribution-current-ticker-sample-2006.json'; AUDIT=ROOT/'data/research/sec-us-attribution-unresolved-audit-2006.json'; SUFFIX=ROOT/'data/research/sec-us-attribution-suffix-incremental-2006.json'; OUT=ROOT/'data/research/sec-country-evidence-cache-2006.json'

def pos(r):
    c=r.get('classification');return c if c in {'US','NON_US'} else None

def main():
    files=sorted(glob.glob(str(ROOT/'data/research/sec-us-attribution-full-shard-*-2006.json')))
    if len(files)!=12: raise RuntimeError(f'expected 12 shards, found {len(files)}')
    evidence=defaultdict(list); identity_meta={}; ticker_keys=defaultdict(set)
    for f in files:
        for r in json.loads(Path(f).read_text()).get('results',[]):
            k=(r.get('ticker'),r.get('securityId'));identity_meta[k]=r;ticker_keys[k[0]].add(k)
            if pos(r): evidence[k].append({'classification':pos(r),'source':'FULL_SHARD','resolutionSource':r.get('resolutionSource'),'stateCode':r.get('stateCode')})
    # Fixed sample is earlier valid PIT evidence and can only add positive evidence, never overwrite it.
    for r in json.loads(SAMPLE.read_text()).get('results',[]):
        k=(r.get('ticker'),r.get('securityId'))
        if k in identity_meta and pos(r): evidence[k].append({'classification':pos(r),'source':'FIXED_24_SAMPLE','resolutionSource':r.get('resolutionSource'),'stateCode':r.get('stateCode')})
    # The unresolved audit retained ticker but not securityId. Accept only when ticker identifies exactly one full-population identity.
    audit=json.loads(AUDIT.read_text())
    for r in audit.get('rows',[]):
        ks=sorted(ticker_keys.get(r.get('ticker'),set()))
        if len(ks)==1 and pos(r): evidence[ks[0]].append({'classification':pos(r),'source':'UNRESOLVED_AUDIT','resolutionSource':'HISTORICAL_10K_AUDIT','stateCode':r.get('stateCode')})
    # Collision-free suffix additions may introduce identities absent from the baseline 439 population.
    suffix=json.loads(SUFFIX.read_text())
    for r in suffix.get('results',[]):
        k=(r.get('ticker'),r.get('securityId'));identity_meta.setdefault(k,r);ticker_keys[k[0]].add(k)
        if pos(r): evidence[k].append({'classification':pos(r),'source':'SUFFIX_INCREMENTAL','resolutionSource':r.get('resolutionSource'),'stateCode':r.get('stateCode')})
    rows=[]; conflicts=[]
    for k,m in sorted(identity_meta.items()):
        ev=evidence.get(k,[]); classes=sorted({e['classification'] for e in ev})
        if len(classes)==1: c=classes[0]
        elif len(classes)>1: c='CONFLICT'
        else: c='UNKNOWN'
        row={'ticker':k[0],'securityId':k[1],'issuer':m.get('issuer'),'classification':c,'evidence':ev}
        rows.append(row)
        if c=='CONFLICT':conflicts.append(row)
    out={'year':2006,'purpose':'Monotonic cache of positive deterministic PIT issuer-country evidence. UNKNOWN/transport failure never overwrites prior positive evidence; conflicting positive evidence is surfaced as CONFLICT. No strategy return/rank information used.','identityCount':len(rows),'classificationCounts':dict(Counter(r['classification'] for r in rows)),'conflictCount':len(conflicts),'rows':rows,'conflicts':conflicts}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(out,indent=2)+'\n');print('SUMMARY',json.dumps({k:v for k,v in out.items() if k not in {'rows','conflicts'}}),flush=True)
    for r in conflicts:print('CONFLICT',json.dumps(r),flush=True)
if __name__=='__main__':main()
