#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('st',ROOT/'scripts'/'research-transition-nearest-fidelity-structural-2019.py')
st=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(st)
nf=st.nf
nf.OUT=ROOT/'data/research/transition-nearest-fidelity-fixedwidth-2019.json'

START_RE=re.compile(r'^\s*([\d,]+)\s+(.+?)\s*$')
VALUE_RE=re.compile(r'^(.*?)(?:\s+\$?\s*)([\d,]+)\s*$')
HEADING_RE=re.compile(r'\s[-—–]\s*\(?\d+(?:\.\d+)?\)?%$')

def parse_fixed_width_inline(seg):
    rows=[];in_common=False;pending=None
    def finish_pending(text):
        m=VALUE_RE.match(text.strip())
        if not m:return None
        desc=nf.clean(m.group(1));value=nf.num(m.group(2))
        if not desc or value is None or desc.lower().startswith('total '):return None
        return {'raw':desc,'name':nf.norm(desc),'value':value}
    for raw in seg.splitlines():
        line=nf.clean(raw)
        if re.search(r'\bCOMMON STOCKS?\b',line,re.I):
            in_common=True;pending=None;continue
        if in_common and nf.STOP_RE.search(line):
            in_common=False;pending=None;continue
        if not in_common or not line:continue
        if HEADING_RE.search(line) or re.match(r'^[-=]+$',line) or line.upper() in {'SHARES DESCRIPTION VALUE','DESCRIPTION VALUE'}:
            continue
        m=START_RE.match(raw)
        if m:
            # A true row begins with shares. If market value is not on this line,
            # carry only the description fragment to the next physical line.
            body=nf.clean(m.group(2))
            r=finish_pending(body)
            if r:
                rows.append(r);pending=None
            else:
                pending=body
            continue
        if pending:
            combined=(pending+' '+line).strip()
            r=finish_pending(combined)
            if r:
                rows.append(r);pending=None
            elif not HEADING_RE.search(line) and not re.match(r'^[-=]+$',line):
                pending=combined
    return nf.finish(rows)

old=nf.parse_rows
def parse_rows(seg):
    candidates=[('fixed_width_inline',parse_fixed_width_inline(seg)),old(seg)]
    plausible=[x for x in candidates if 5<=len(x[1])<=250]
    if plausible:return max(plausible,key=lambda x:len(x[1]))
    return max(candidates,key=lambda x:len(x[1]))
nf.parse_rows=parse_rows
nf.main()
