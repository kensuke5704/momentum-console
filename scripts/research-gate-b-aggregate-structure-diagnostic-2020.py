#!/usr/bin/env python3
from __future__ import annotations
import gzip,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'scripts/research-gate-b-aggregate-shadow-2020.py'
spec=importlib.util.spec_from_file_location('agg',p);agg=importlib.util.module_from_spec(spec);spec.loader.exec_module(agg)
man=json.loads((ROOT/'data/research/gate-b-production-source-manifest-2020.json').read_text())
with gzip.open(ROOT/'data/sec-nport/bootstrap.json.gz','rt',encoding='utf-8') as fh:b=json.load(fh)
filings=b.get('snapshots',b) if isinstance(b,dict) else b
hist=agg.production_month(json.loads((ROOT/'data/universe-history.json').read_text()));asof=hist['asOf'];master=agg.build_master(filings,asof)
rows=[]
for s0 in man['sources']:
 s=dict(s0);s['filingDate']=agg.filing_date(s);text,tr=agg.fetch(s['sourceDocumentUrl']);src,m=agg.source_from_legacy(s,text,master,asof);m['transport']=tr;rows.append(m);print('STRUCTURE',json.dumps(m),flush=True)
out={'asOf':asof,'rows':rows,'purpose':'Structural-only diagnostic before aggregate Universe scoring. No Production overlap/rank metrics are computed.'}
q=ROOT/'data/research/gate-b-aggregate-structure-diagnostic-2020.json';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+'\n')
