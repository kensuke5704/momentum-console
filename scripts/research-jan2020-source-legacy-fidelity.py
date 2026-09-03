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
nearest.CHOSEN={sid:(str(row['cik']),row['accession'],row['form'],row['reportDate']) for sid,row in d.get('chosen',{}).items()}
nearest.OUT=OUT

# Structural title normalization for filings that render hyphen/en-dash/em-dash differently.
def title_norm(s):
    s=(s or '').lower().replace('–','-').replace('—','-').replace('‑','-')
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())

def structural_start(ls,name):
    target=title_norm(name);tails=[target]
    if ' - ' in (name or ''): tails.append(title_norm((name or '').split(' - ',1)[1]))
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

# Issuer identity, not security class identity. Remove only explicit share-class labels and
# trailing state/jurisdiction decorations that SEC/N-PORT often appends to issuer names.
_base_norm=nearest.norm
def issuer_norm(s):
    n=_base_norm(s)
    n=re.sub(r'\bCLASS\s+[A-Z0-9]+(?:\s+SHARES?)?\b',' ',n)
    n=re.sub(r'\bNON\s+VOTING\s+SHARES?\b',' ',n)
    n=re.sub(r'\bCOMMON\s+SHARES?\b',' ',n)
    n=re.sub(r'\s+(?:DE|MD|NY|CA|VA)$','',n)
    return ' '.join(n.split())
nearest.norm=issuer_norm

NUM_TOKEN=r'\(?\$?\d[\d,]*(?:\.\d+)?\)?'
TAIL_TWO_RE=re.compile(rf'^(.*?)\s+({NUM_TOKEN})\s+\$?\s*({NUM_TOKEN})(?:\s*[*†‡a-z()]*)?$',re.I)
PURE_NUMS_RE=re.compile(rf'^\s*({NUM_TOKEN})\s+\$?\s*({NUM_TOKEN})(?:\s*[*†‡a-z()]*)?\s*$',re.I)

def heading(line):
    plain=line.strip().strip('_').strip()
    return bool(re.search(r'[-—–]\s*\d+(?:\.\d+)?%\s*$',plain) or
                re.search(r'[-—–]\s*(?:continued)\s*$',plain,re.I) or
                plain.lower().startswith(('total ','cost ','security ','shares ','value','see notes','schedule of investments','common stocks')))

# Mixed SEC rendering grammar:
# A) issuer and both numeric fields on one line;
# B) issuer on one line and a pure shares/value line immediately after it.
def parse_mixed_line(seg):
    ls=[nearest.clean(x) for x in seg.splitlines() if nearest.clean(x)]
    rows=[];in_common=False;i=0
    while i<len(ls):
        line=ls[i].strip();plain=line.strip('_').strip()
        if re.search(r'\bCOMMON STOCKS?\b',plain,re.I):in_common=True;i+=1;continue
        if in_common and nearest.STOP_RE.search(plain):in_common=False;i+=1;continue
        if not in_common or heading(line):i+=1;continue
        # One-line issuer | shares | market value.
        m=TAIL_TWO_RE.match(plain)
        if m and m.group(1).strip():
            desc=m.group(1).strip();value=nearest.num(m.group(3))
            if value is not None and value>0:
                rows.append({'raw':desc,'name':nearest.norm(desc),'value':value});i+=1;continue
        # Two-line issuer then numeric-only shares/value row.
        if i+1<len(ls):
            m=PURE_NUMS_RE.match(ls[i+1].strip().strip('_').strip())
            if m:
                value=nearest.num(m.group(2))
                if value is not None and value>0:
                    rows.append({'raw':plain,'name':nearest.norm(plain),'value':value});i+=2;continue
        i+=1
    return nearest.finish(rows)

_old=nearest.parse_rows
def parse_rows(seg):
    candidates=[('mixed_line',parse_mixed_line(seg)),_old(seg)]
    plausible=[x for x in candidates if 5<=len(x[1])<=250]
    if plausible:return max(plausible,key=lambda x:len(x[1]))
    return max(candidates,key=lambda x:len(x[1]))
nearest.parse_rows=parse_rows
nearest.main()
