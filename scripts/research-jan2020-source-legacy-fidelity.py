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

# Structural text normalization only. No issuer overlap is used to locate a portfolio.
def title_norm(s):
    s=(s or '').lower().replace('–','-').replace('—','-').replace('‑','-')
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())

def schedule_heading(line):
    # Accept an actual short schedule/portfolio heading, not prose such as
    # "including the schedule of investments" inside an auditor report.
    p=re.sub(r'\[[^\]]*\]\([^)]*\)',' ',line or '')
    p=re.sub(r'[*_#]+',' ',p).strip()
    return len(p)<=180 and bool(re.match(r'^(?:schedule of investments|portfolio of investments|portfolio holdings)\b',p,re.I))

def structural_start(ls,name):
    target=title_norm(name);aliases=[target]
    # Some reports omit/add the ticker prefix before a dash.
    for sep in (' - ',' – ',' — '):
        if sep in (name or ''):
            aliases.append(title_norm((name or '').split(sep,1)[1]))
    title_hits=[i for i,x in enumerate(ls) if any(a and a in title_norm(x) for a in aliases)]
    sched_hits=[i for i,x in enumerate(ls) if schedule_heading(x)]
    pairs=[]
    for s in sched_hits:
        nearby=[i for i in title_hits if abs(i-s)<=90]
        for i in nearby:pairs.append((abs(i-s),s,i))
    if pairs:
        # Start at the title nearest an explicit schedule heading.
        return min(pairs)[2]
    return None
nearest.structural_start=structural_start

def slice_series(text,name,all_names):
    ls=text.splitlines();i=structural_start(ls,name)
    if i is None:return ''
    # Include the schedule heading when it precedes the fund title.
    sched=[j for j in range(max(0,i-90),min(len(ls),i+30)) if schedule_heading(ls[j])]
    start=max(0,(min(sched,key=lambda j:abs(j-i)) if sched else i)-5)
    end=min(len(ls),start+1900)
    other=[title_norm(n) for n in all_names if n!=name and title_norm(n)]
    for j in range(i+1,end):
        if j>i+30 and re.match(r'^\s*(?:Statement|Statements) of (?:Assets|Operations|Changes)',re.sub(r'[*_#]+','',ls[j]),re.I):
            end=j;break
        nx=title_norm(ls[j])
        if j>i+40 and any(t in nx for t in other):
            local=ls[max(0,j-20):min(len(ls),j+20)]
            if any(schedule_heading(x) for x in local):end=j;break
    return '\n'.join(ls[start:end])
nearest.slice_series=slice_series

# Issuer identity normalization. Remove only security-class labels and common SEC
# jurisdiction suffix decorations; do not fuzzy-match issuer names.
_base_norm=nearest.norm
def issuer_norm(s):
    n=_base_norm(s)
    n=re.sub(r'\bCLASS\s+[A-Z0-9]+(?:\s+SHARES?)?\b',' ',n)
    n=re.sub(r'\bNON\s+VOTING\s+SHARES?\b',' ',n)
    n=re.sub(r'\bCOMMON\s+SHARES?\b',' ',n)
    n=re.sub(r'\s+(?:DE|MD|NY|CA|VA)$','',n)
    return ' '.join(n.split())
nearest.norm=issuer_norm

NUM_RE=re.compile(r'\$?\(?\d[\d,]*(?:\.\d+)?\)?')

def plain_line(line):
    return re.sub(r'[*_#]+','',line or '').strip()

def heading(line):
    p=plain_line(line)
    return bool(
        re.search(r'[-—–]\s*\d+(?:\.\d+)?%\s*$',p) or
        re.search(r'[-—–]\s*(?:continued|cont.?d)\s*$',p,re.I) or
        re.match(r'^(?:total\b|cost\b|security\b|shares\b|value\b|rate\b|see notes\b|schedule of investments\b|portfolio of investments\b)',p,re.I)
    )

def terminal_two(line):
    # SEC/r.jina may concatenate issuer and shares with no separator, e.g.
    # "Amazon.com Inc.5,098 9,049,307*". The final two numeric groups are
    # structurally shares and market value. Taking the final two also avoids
    # company-name digits such as 3M being interpreted as shares.
    p=plain_line(line)
    ms=list(NUM_RE.finditer(p))
    if len(ms)<2:return None
    q,v=ms[-2],ms[-1]
    desc=p[:q.start()].strip(' .\t')
    # Everything after value must be footnote/formatting only.
    tail=p[v.end():].strip()
    if tail and not re.fullmatch(r'[A-Za-z()†‡*\s.,-]*',tail):return None
    value=nearest.num(v.group())
    shares=nearest.num(q.group())
    if not desc or shares is None or value is None or shares<=0 or value<=0:return None
    return desc,value

# Generic mixed legacy grammar:
# A) issuer + shares + market value in one rendered line;
# B) issuer-only line followed by a numeric-only shares/value line.
def parse_mixed_line(seg):
    ls=[nearest.clean(x) for x in seg.splitlines() if nearest.clean(x)]
    rows=[];in_common=False;i=0
    while i<len(ls):
        raw=ls[i];p=plain_line(raw)
        if re.search(r'\bCOMMON STOCKS?\b',p,re.I):in_common=True;i+=1;continue
        if in_common and nearest.STOP_RE.search(p):in_common=False;i+=1;continue
        if not in_common or heading(raw):i+=1;continue
        one=terminal_two(raw)
        if one:
            desc,value=one
            if not desc.lower().startswith('total '):rows.append({'raw':desc,'name':nearest.norm(desc),'value':value})
            i+=1;continue
        if i+1<len(ls):
            nxt=plain_line(ls[i+1]);ms=list(NUM_RE.finditer(nxt))
            nonnum=NUM_RE.sub('',nxt).replace('$','').strip(' _*\t')
            if len(ms)>=2 and not nonnum:
                value=nearest.num(ms[-1].group())
                if value is not None and value>0 and p and not heading(p):
                    rows.append({'raw':p,'name':nearest.norm(p),'value':value});i+=2;continue
        i+=1
    return nearest.finish(rows)

_old=nearest.parse_rows
def parse_rows(seg):
    candidates=[('mixed_terminal',parse_mixed_line(seg)),_old(seg)]
    plausible=[x for x in candidates if 5<=len(x[1])<=250]
    if plausible:return max(plausible,key=lambda x:len(x[1]))
    return max(candidates,key=lambda x:len(x[1]))
nearest.parse_rows=parse_rows
nearest.main()
