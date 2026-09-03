#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('fw',ROOT/'scripts'/'research-transition-nearest-fidelity-fixedwidth-2019.py')
fw=importlib.util.module_from_spec(S);S.loader.exec_module(fw)
nf=fw.nf
TARGETS=['S000010977','S000017177','S000017178','S000033237','S000050385']
with gzip.open(nf.BOOT,'rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b;first=nf.earliest_nport(filings)
names={sid:(first[sid].get('seriesName') or first[sid].get('fundName') or '') for sid in TARGETS}
for sid in TARGETS:
 cik,acc,form,rd=nf.CHOSEN[sid];name=names[sid];hit=nf.locate_doc(nf.docs(cik,acc,form),name)
 same=[names[x] for x in TARGETS if nf.CHOSEN[x][:3]==(cik,acc,form)]
 seg=fw.st.structural_slice(hit[3],name,same);rows=fw.parse_fixed_width_inline(seg)
 print('SERIES',json.dumps({'seriesId':sid,'seriesName':name,'rowCount':len(rows),'segmentLines':len(seg.splitlines())}),flush=True)
 for i,r in enumerate(rows[:20],1):print('ROW',json.dumps({'seriesId':sid,'i':i,'raw':r.get('raw'),'name':r.get('name'),'value':r.get('value')}),flush=True)
