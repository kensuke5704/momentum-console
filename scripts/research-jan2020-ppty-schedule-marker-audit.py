#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('jan',ROOT/'scripts'/'research-jan2020-source-legacy-fidelity.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
n=mod.nearest
sid='S000061208';cik,acc,form,rd=n.CHOSEN[sid]
name='PPTY - U.S. Diversified Real Estate ETF'
for url in n.docs(cik,acc,form):
    hit=n.locate_doc([url],name)
    if not hit:continue
    _,_,_,text,_=hit;ls=text.splitlines()
    titles=[i for i,x in enumerate(ls) if 'PPTY' in x.upper() and 'DIVERSIFIED REAL ESTATE ETF' in x.upper()]
    markers=[i for i,x in enumerate(ls) if mod.schedule_heading(x)]
    print('DOC',json.dumps({'url':url,'lines':len(ls),'titleHits':titles[:80],'scheduleHeadingHits':markers[:80]}),flush=True)
    for i in sorted(set(markers + titles)):
        print('WINDOW',i,json.dumps(ls[max(0,i-5):min(len(ls),i+12)]),flush=True)
