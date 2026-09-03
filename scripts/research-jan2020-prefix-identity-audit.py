#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('jan',ROOT/'scripts'/'research-jan2020-source-legacy-fidelity.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
n=mod.nearest
with gzip.open(ROOT/'data/sec-nport/bootstrap.json.gz','rt',encoding='utf-8') as fh:b=json.load(fh)
fs=b.get('snapshots',b) if isinstance(b,dict) else b;first=n.earliest_nport(fs)
MIN_PREFIX=24
for sid in ['S000057700','S000061208']:
    nf=first[sid];name=nf.get('seriesName') or '';cik,acc,form,rd=n.CHOSEN[sid]
    hit=n.locate_doc(n.docs(cik,acc,form),name)
    _,_,_,text,_=hit;seg=n.slice_series(text,name,[name]);grammar,lh=n.parse_rows(seg)
    legacy_names=sorted({x['name'] for x in lh if x.get('name')})
    exact=prefix=amb=none=0;rows=[]
    for h in nf.get('holdings',[]):
        raw=h.get('issuerName') or '';q=n.norm(raw)
        if not q:continue
        if q in legacy_names:
            exact+=1;status='EXACT';matches=[q]
        else:
            matches=[x for x in legacy_names if len(q)>=MIN_PREFIX and x.startswith(q)]
            if len(matches)==1:prefix+=1;status='UNIQUE_PREFIX'
            elif len(matches)>1:amb+=1;status='AMBIGUOUS_PREFIX'
            else:none+=1;status='UNMATCHED'
        rows.append({'issuer':raw,'normalized':q,'symbol':h.get('symbol'),'weight':h.get('weight'),'status':status,'matches':matches[:5]})
    print('SUMMARY',json.dumps({'seriesId':sid,'seriesName':name,'grammar':grammar,'legacyCount':len(lh),'nportCount':len(rows),'exact':exact,'uniquePrefix':prefix,'ambiguousPrefix':amb,'unmatched':none,'retainedAfterPrefix':exact+prefix,'retentionRate':(exact+prefix)/len(rows) if rows else None,'minPrefix':MIN_PREFIX}),flush=True)
    for r in rows:
        if r['status']!='EXACT':print('ROW',sid,json.dumps(r),flush=True)
