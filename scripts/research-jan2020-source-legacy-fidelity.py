#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DISC=ROOT/'data/research/jan2020-source-legacy-nearest.json'
OUT=ROOT/'data/research/jan2020-source-legacy-fidelity.json'
SPEC=importlib.util.spec_from_file_location('nearest',ROOT/'scripts'/'research-transition-nearest-fidelity-2019.py')
nearest=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(nearest)

d=json.loads(DISC.read_text())
chosen={sid:(str(row['cik']),row['accession'],row['form'],row['reportDate']) for sid,row in d.get('chosen',{}).items()}
nearest.CHOSEN=chosen
nearest.OUT=OUT

# Structural title normalization for filings that render hyphen/en-dash/em-dash differently.
def title_norm(s):
    s=(s or '').lower().replace('–','-').replace('—','-').replace('‑','-')
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())

def structural_start(ls,name):
    target=title_norm(name)
    # Also permit ticker prefix omission/addition by comparing the substantive fund-title tail.
    tails=[target]
    if ' - ' in (name or ''):
        tails.append(title_norm((name or '').split(' - ',1)[1]))
    candidates=[]
    for i,x in enumerate(ls):
        nx=title_norm(x)
        if not any(t and t in nx for t in tails): continue
        local='\n'.join(ls[max(0,i-20):min(len(ls),i+25)])
        if not nearest.SCHED_RE.search(local): continue
        ds=[abs(j-i) for j in range(max(0,i-20),min(len(ls),i+25)) if nearest.SCHED_RE.search(ls[j])]
        candidates.append((min(ds) if ds else 99,i))
    return min(candidates)[1] if candidates else None
nearest.structural_start=structural_start

def slice_series(text,name,all_names):
    ls=text.splitlines();i=structural_start(ls,name)
    if i is None:return ''
    start=max(0,i-20);end=min(len(ls),i+1800)
    other=[title_norm(n) for n in all_names if n!=name and title_norm(n)]
    for j in range(i+1,end):
        nx=title_norm(ls[j])
        if j>i+40 and any(t in nx for t in other) and nearest.SCHED_RE.search('\n'.join(ls[max(0,j-15):min(len(ls),j+20)])):
            end=j;break
        if j>i+40 and re.search(r'^\s*Statements? of Assets',ls[j],re.I):end=j;break
    return '\n'.join(ls[start:end])
nearest.slice_series=slice_series

# Generic legacy grammar: issuer description on one line, then shares and market value
# rendered together on the next non-empty line (e.g. "35,446  $ 4,680,290").
def parse_line_pair(seg):
    ls=[nearest.clean(x) for x in seg.splitlines() if nearest.clean(x)]
    rows=[];in_common=False;i=0
    while i<len(ls):
        line=ls[i]
        if re.search(r'\bCOMMON STOCKS?\b',line,re.I):in_common=True;i+=1;continue
        if in_common and nearest.STOP_RE.search(line):in_common=False;i+=1;continue
        if not in_common:i+=1;continue
        if (nearest.NUM_RE.match(line) or re.search(r'[-—–]\s*\d+(?:\.\d+)?%$',line)
            or line.lower().startswith(('total ','cost ','security ','shares ','value','see notes','schedule of investments'))):
            i+=1;continue
        if i+1<len(ls):
            nums=re.findall(r'\(?\d[\d,]*(?:\.\d+)?\)?',ls[i+1])
            if len(nums)>=2:
                vals=[nearest.num(x) for x in nums]
                if vals[0] is not None and vals[-1] is not None and vals[-1]>0:
                    rows.append({'raw':line,'name':nearest.norm(line),'value':vals[-1]});i+=2;continue
        i+=1
    return nearest.finish(rows)

_old=nearest.parse_rows
def parse_rows(seg):
    candidates=[('line_pair',parse_line_pair(seg)),_old(seg)]
    plausible=[x for x in candidates if 5<=len(x[1])<=250]
    if plausible:return max(plausible,key=lambda x:len(x[1]))
    return max(candidates,key=lambda x:len(x[1]))
nearest.parse_rows=parse_rows
nearest.main()
