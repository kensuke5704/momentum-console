#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('jan',ROOT/'scripts'/'research-jan2020-source-legacy-fidelity.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
n=mod.nearest
sid='S000061208';name='PPTY - U.S. Diversified Real Estate ETF';cik,acc,form,rd=n.CHOSEN[sid]
with gzip.open(ROOT/'data/sec-nport/bootstrap.json.gz','rt',encoding='utf-8') as fh:b=json.load(fh)
fs=b.get('snapshots',b) if isinstance(b,dict) else b;nf=n.earliest_nport(fs)[sid]
hit=n.locate_doc(n.docs(cik,acc,form),name);_,_,url,text,_=hit
seg=n.slice_series(text,name,[name]);grammar,lh=n.parse_rows(seg)
pmap={n.norm(h.get('issuerName') or ''):h for h in nf.get('holdings',[]) if h.get('issuerName')}
legacy_total=sum(float(x.get('value') or 0) for x in lh)
print('SUMMARY',json.dumps({'grammar':grammar,'legacyCount':len(lh),'legacyValueTotal':legacy_total,'nportCount':len(pmap),'url':url}),flush=True)
for x in sorted(lh,key=lambda z:float(z.get('value') or 0),reverse=True)[:40]:
    print('LEGACY_TOP',json.dumps({'raw':x.get('raw'),'name':x.get('name'),'value':x.get('value'),'weight':x.get('weight'),'matched':x.get('name') in pmap,'nport':pmap.get(x.get('name'))}),flush=True)
legacy_names={x.get('name') for x in lh}
for k,h in sorted(pmap.items(),key=lambda kv:float(kv[1].get('weight') or 0),reverse=True)[:40]:
    print('NPORT_TOP',json.dumps({'name':k,'issuer':h.get('issuerName'),'symbol':h.get('symbol'),'weight':h.get('weight'),'matched':k in legacy_names}),flush=True)
