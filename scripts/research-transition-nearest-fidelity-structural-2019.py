#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('nf',ROOT/'scripts'/'research-transition-nearest-fidelity-2019.py')
nf=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(nf)
nf.OUT=ROOT/'data/research/transition-nearest-fidelity-structural-2019.json'

EXACT_SCHED=re.compile(r'^\s*(?:PORTFOLIO|SCHEDULE) OF INVESTMENTS(?:\s*\(CONTINUED\))?\s*$',re.I)
COMMON=re.compile(r'\bCOMMON STOCKS?\b',re.I)

def structural_slice(text,name,all_names):
    ls=text.splitlines()
    candidates=[]
    for i,line in enumerate(ls):
        if name.lower() not in line.lower():
            continue
        # Registered series title must be followed immediately by a real schedule heading.
        for j in range(i,min(len(ls),i+14)):
            if not EXACT_SCHED.match(ls[j]):
                continue
            # Real holdings schedule must enter an explicit common-stock section nearby.
            common_at=None
            for k in range(j,min(len(ls),j+260)):
                if COMMON.search(ls[k]):
                    common_at=k;break
                if k>j+40 and re.search(r'^\s*Statements? of Assets',ls[k],re.I):
                    break
            if common_at is not None:
                candidates.append((j-i,j,common_at,i))
    if not candidates:
        return ''
    # Exact structural anchor nearest to title; later line breaks ties to avoid TOC/front-matter duplicates.
    _,sched,common_at,title_i=sorted(candidates,key=lambda x:(x[0],-x[1]))[0]
    start=max(0,title_i-2)
    end=min(len(ls),sched+1800)
    # Stop only at a later exact registered series title that itself starts a real schedule.
    for p in range(sched+1,end):
        for other in all_names:
            if other==name or other.lower() not in ls[p].lower():
                continue
            for q in range(p,min(len(ls),p+14)):
                if EXACT_SCHED.match(ls[q]):
                    end=p;break
            if end==p:break
        if end==p:break
    return '\n'.join(ls[start:end])

nf.slice_series=structural_slice
nf.main()
