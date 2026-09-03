#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('jan',ROOT/'scripts'/'research-jan2020-source-legacy-fidelity.py')
mod=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(mod)
n=mod.nearest
for sid in ['S000057700','S000061208']:
    cik,acc,form,rd=n.CHOSEN[sid]
    # Use exact discovered primary form document.
    urls=n.docs(cik,acc,form)
    name='ClearBridge Large Cap Growth ESG ETF' if sid=='S000057700' else 'PPTY - U.S. Diversified Real Estate ETF'
    hit=n.locate_doc(urls,name)
    if not hit:
        print('NO_DOC',sid,urls,flush=True);continue
    _,_,url,text,_=hit
    seg=n.slice_series(text,name,[name])
    print('FORMAT',json.dumps({'sid':sid,'url':url,'segmentChars':len(seg),'segmentLines':len(seg.splitlines())}),flush=True)
    lines=seg.splitlines()
    for i,line in enumerate(lines[:260]):
        if line.strip():print('LINE',sid,i,repr(line),flush=True)
