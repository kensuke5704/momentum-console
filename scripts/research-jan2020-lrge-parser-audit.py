#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json,difflib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Load the Jan wrapper; its structural monkeypatches are then available as mod.nearest.
SPEC=importlib.util.spec_from_file_location('jan',ROOT/'scripts'/'research-jan2020-source-legacy-fidelity.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
n=mod.nearest
sid='S000057700';cik,acc,form,rd=n.CHOSEN[sid]
with gzip.open(ROOT/'data/sec-nport/bootstrap.json.gz','rt',encoding='utf-8') as fh:b=json.load(fh)
fs=b.get('snapshots',b) if isinstance(b,dict) else b
first=n.earliest_nport(fs);nf=first[sid];name=nf.get('seriesName') or ''
du=n.docs(cik,acc,form);hit=n.locate_doc(du,name)
score,_,url,text,_=hit
seg=n.slice_series(text,name,[name]);grammar,lh=n.parse_rows(seg)
ph=[{'raw':h.get('issuerName'),'name':n.norm(h.get('issuerName') or ''),'symbol':h.get('symbol'),'weight':h.get('weight')} for h in nf.get('holdings',[]) if h.get('issuerName')]
pnames=[x['name'] for x in ph]
print('AUDIT_SUMMARY',json.dumps({'seriesId':sid,'seriesName':name,'grammar':grammar,'legacyCount':len(lh),'nportCount':len(ph),'document':url,'segmentChars':len(seg)}),flush=True)
for i,x in enumerate(lh[:60]):
    close=difflib.get_close_matches(x['name'],pnames,n=3,cutoff=.3)
    print('LEGACY',json.dumps({'i':i,'raw':x.get('raw'),'name':x.get('name'),'value':x.get('value'),'closest':close}),flush=True)
for i,x in enumerate(ph[:60]):print('NPORT',json.dumps({'i':i,**x}),flush=True)
